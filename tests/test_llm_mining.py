"""Tests for the LLM mining module.

All tests use mocks — no real network calls or LLM API keys required.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from trustdata.llm_mining import (
    CrawlStep,
    ExtractedRecord,
    FetchedPage,
    LLMClient,
    LLMProvider,
    MiningPipeline,
    MiningTask,
    _citation_score,
    _extract_json_block,
    _html_to_text_snippet,
    _normalize_rating,
    enrich_cross_source_fields,
    parse_task_natural_language,
    parse_task_yaml,
    run_mining,
)


# ---------------------------------------------------------------------------
# TestCitationScore
# ---------------------------------------------------------------------------

class TestCitationScore:
    def test_exact_match(self):
        assert _citation_score("hello world", "say hello world today") == 1.0

    def test_normalized_match(self):
        score = _citation_score("Hello  World", "say hello world today")
        assert score == 0.9

    def test_empty_snippet(self):
        assert _citation_score("", "some content") == 0.0

    def test_empty_content(self):
        assert _citation_score("snippet", "") == 0.0

    def test_hallucinated(self):
        score = _citation_score(
            "this text does not exist anywhere",
            "completely unrelated page content about cats and dogs",
        )
        assert score < 0.5

    def test_partial_overlap(self):
        score = _citation_score(
            "rating 4.5 stars excellent",
            "the rating is 4.5 stars for this excellent movie review",
        )
        assert 0.0 < score <= 1.0


# ---------------------------------------------------------------------------
# TestNormalizeRating
# ---------------------------------------------------------------------------

class TestNormalizeRating:
    def test_0_to_5_passthrough(self):
        assert _normalize_rating(4.0, "0-5") == 4.0

    def test_0_to_10(self):
        assert _normalize_rating(8.0, "0-10") == 4.0

    def test_0_to_100(self):
        assert _normalize_rating(80.0, "0-100") == 4.0

    def test_none_input(self):
        assert _normalize_rating(None, "0-5") is None

    def test_clamp_high(self):
        result = _normalize_rating(110.0, "0-100")
        assert result == 5.0

    def test_clamp_low(self):
        result = _normalize_rating(-5.0, "0-10")
        assert result == 0.0

    def test_invalid_scale_passthrough(self):
        result = _normalize_rating(3.5, "stars")
        assert result == 3.5


# ---------------------------------------------------------------------------
# TestExtractJsonBlock
# ---------------------------------------------------------------------------

class TestExtractJsonBlock:
    def test_markdown_fenced(self):
        text = '```json\n[{"a": 1}]\n```'
        result = json.loads(_extract_json_block(text))
        assert result == [{"a": 1}]

    def test_raw_array(self):
        text = 'Here is the result: [{"a": 1}, {"b": 2}] end.'
        result = json.loads(_extract_json_block(text))
        assert len(result) == 2

    def test_raw_object(self):
        text = 'Output: {"key": "value"}'
        result = json.loads(_extract_json_block(text))
        assert result["key"] == "value"

    def test_fenced_no_lang(self):
        text = '```\n{"x": 42}\n```'
        result = json.loads(_extract_json_block(text))
        assert result["x"] == 42

    def test_multiple_json_objects_returns_first_complete_object(self):
        text = '{"domain": "music"}\n{"entity_type": "album"}'
        assert json.loads(_extract_json_block(text)) == {"domain": "music"}

    def test_multiple_json_arrays_returns_first_complete_array(self):
        text = '[{"action": "fetch"}]\n[{"action": "paginate"}]'
        assert json.loads(_extract_json_block(text)) == [{"action": "fetch"}]

    def test_braces_inside_json_string_do_not_break_extraction(self):
        text = 'Result: {"note": "keep {this} literal", "items": []} trailing text'
        assert json.loads(_extract_json_block(text))["note"] == "keep {this} literal"


class TestNaturalLanguageTaskParsing:
    def test_multiple_json_objects_use_the_first_task_object(self):
        llm = MagicMock()
        llm.chat.return_value = (
            '{"domain":"music","entity_type":"album",'
            '"entities":[{"name":"OK Computer"}],"platforms":["aoty","rym"]}'
            '\n{"note":"duplicate response"}'
        )

        task = parse_task_natural_language("Find OK Computer ratings", llm)

        assert task.domain == "music"
        assert task.entities == [{"name": "OK Computer"}]
        assert task.platforms == ["aoty", "rym"]

    def test_non_object_task_response_has_actionable_error(self):
        llm = MagicMock()
        llm.chat.return_value = '[{"name":"OK Computer"}]'

        with pytest.raises(ValueError, match="natural-language task parsing; expected a JSON dict"):
            parse_task_natural_language("Find ratings", llm)


# ---------------------------------------------------------------------------
# TestHtmlToTextSnippet
# ---------------------------------------------------------------------------

class TestHtmlToTextSnippet:
    def test_strip_tags(self):
        html = "<p>Hello <b>world</b></p>"
        text = _html_to_text_snippet(html)
        assert "Hello" in text
        assert "world" in text
        assert "<" not in text

    def test_remove_scripts(self):
        html = "<script>var x=1;</script><p>Content</p>"
        text = _html_to_text_snippet(html)
        assert "var x" not in text
        assert "Content" in text

    def test_remove_styles(self):
        html = "<style>.foo{color:red}</style><p>Visible</p>"
        text = _html_to_text_snippet(html)
        assert "color" not in text
        assert "Visible" in text

    def test_truncation(self):
        html = "<p>" + "A" * 10000 + "</p>"
        text = _html_to_text_snippet(html, max_chars=100)
        assert len(text) <= 100


# ---------------------------------------------------------------------------
# TestParseTaskYaml
# ---------------------------------------------------------------------------

class TestParseTaskYaml:
    def test_valid_yaml(self, tmp_path):
        task_file = tmp_path / "task.yaml"
        task_file.write_text(textwrap.dedent("""\
            task:
              domain: "movies"
              entity_type: "movie"
              entities:
                - name: "Inception"
                  year: "2010"
              platforms: ["imdb", "douban"]
              search_hints:
                - "https://www.imdb.com/title/tt1375666/reviews/"
              max_pages_per_entity: 3
              language: "en"
        """), encoding="utf-8")
        task = parse_task_yaml(task_file)
        assert task.domain == "movies"
        assert task.entity_type == "movie"
        assert len(task.entities) == 1
        assert task.entities[0]["name"] == "Inception"
        assert task.platforms == ["imdb", "douban"]
        assert task.max_pages_per_entity == 3
        assert task.language == "en"
        assert task.task_id.startswith("mining_task_")

    def test_string_entities(self, tmp_path):
        task_file = tmp_path / "task.yaml"
        task_file.write_text(textwrap.dedent("""\
            task:
              domain: "music"
              entity_type: "album"
              entities:
                - "OK Computer"
                - "Kid A"
              platforms: ["aoty"]
        """), encoding="utf-8")
        task = parse_task_yaml(task_file)
        assert len(task.entities) == 2
        assert task.entities[0] == {"name": "OK Computer"}
        assert task.entities[1] == {"name": "Kid A"}


# ---------------------------------------------------------------------------
# TestEnrichCrossSource
# ---------------------------------------------------------------------------

class TestEnrichCrossSource:
    def test_multi_platform(self):
        df = pd.DataFrame({
            "record_id": ["r1", "r2", "r3", "r4"],
            "entity_id": ["e1", "e1", "e1", "e2"],
            "rating": [4.0, 3.0, 5.0, 2.0],
            "source": ["llm_mined:imdb", "llm_mined:douban", "llm_mined:rt", "llm_mined:imdb"],
        })
        result = enrich_cross_source_fields(df)
        assert "entity_reference_score" in result.columns
        assert "cross_source_gap" in result.columns
        # e1 has 3 sources with means 4.0, 3.0, 5.0 → ref = 4.0, gap = 2.0
        e1_rows = result[result["entity_id"] == "e1"]
        assert np.isclose(e1_rows["entity_reference_score"].iloc[0], 4.0)
        assert np.isclose(e1_rows["cross_source_gap"].iloc[0], 2.0)

    def test_single_platform(self):
        df = pd.DataFrame({
            "record_id": ["r1"],
            "entity_id": ["e1"],
            "rating": [3.5],
            "source": ["llm_mined:imdb"],
        })
        result = enrich_cross_source_fields(df)
        assert pd.isna(result["entity_reference_score"].iloc[0])
        assert pd.isna(result["cross_source_gap"].iloc[0])

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = enrich_cross_source_fields(df)
        assert result.empty


# ---------------------------------------------------------------------------
# TestMiningPipeline — full pipeline with mocks
# ---------------------------------------------------------------------------

class TestMiningPipeline:
    def _make_provider(self) -> LLMProvider:
        return LLMProvider(
            api_type="openai",
            model="test-model",
            api_key_env="TEST_LLM_KEY",
        )

    def _make_task(self) -> MiningTask:
        return MiningTask(
            task_id="test_task_001",
            domain="movies",
            entity_type="movie",
            entities=[{"name": "Inception", "year": "2010"}],
            platforms=["imdb"],
            max_pages_per_entity=2,
            request_delay=0.0,
            language="en",
        )

    @patch.dict("os.environ", {"TEST_LLM_KEY": "fake-key"})
    @patch("trustdata.llm_mining._lazy_import_httpx")
    def test_full_pipeline_with_mocks(self, mock_lazy_httpx):
        """End-to-end pipeline with mocked LLM and HTTP."""
        # Build a mock LLM client
        provider = self._make_provider()

        mock_httpx = MagicMock()
        mock_lazy_httpx.return_value = mock_httpx

        llm = LLMClient.__new__(LLMClient)
        llm._provider = provider
        llm._api_key = "fake-key"
        llm._httpx = mock_httpx

        task = self._make_task()

        # Strategy response
        strategy_response = json.dumps([
            {"action": "fetch", "url": "https://www.imdb.com/title/tt1375666/reviews/", "purpose": "IMDB reviews for Inception"}
        ])
        # Extraction response
        citation = "Inception rating 4.25/5 by user123 on 2024-03-15: Amazing movie with great visual effects and a mind-bending plot."
        page_content = (
            '<div class="review">'
            f'<p>{citation}</p>'
            '</div>'
        )
        extraction_response = json.dumps([{
            "entity_name": "Inception",
            "platform": "imdb",
            "rating": 4.25,
            "rating_scale": "0-5",
            "contributor_id": "user123",
            "review_text": "Amazing movie with great visual effects and a mind-bending plot.",
            "created_at": "2024-03-15T00:00:00Z",
            "citation_snippet": citation,
        }])

        # Set up LLM chat mock to return different responses
        call_count = [0]
        def mock_chat(system, user):
            call_count[0] += 1
            if call_count[0] == 1:
                return strategy_response
            return extraction_response

        llm.chat = mock_chat

        # Mock httpx.get for fetching
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = page_content
        mock_httpx.get.return_value = mock_response

        pipeline = MiningPipeline(
            llm, task,
            max_pages=10,
            delay=0.0,
            min_citation_score=0.3,
            resolver=lambda _: ["8.8.8.8"],
        )

        # Phase 1
        steps = pipeline.generate_strategy()
        assert len(steps) == 1
        assert "imdb.com" in steps[0].url

        # Phase 2
        pages = pipeline.execute_crawl_plan()
        assert len(pages) == 1
        assert pages[0].status_code == 200

        # Phase 3
        records = pipeline.extract_records()
        assert len(records) == 1
        assert records[0].entity_name == "Inception"

        # Phase 4
        verified = pipeline.verify_records()
        assert len(verified) >= 1
        assert verified[0].confidence > 0

        # Phase 5
        df = pipeline.to_canonical_dataframe()
        assert not df.empty
        assert "record_id" in df.columns
        assert "entity_id" in df.columns
        assert "rating" in df.columns
        assert "verification_level" in df.columns
        assert df["verification_level"].iloc[0] == "llm_mined_web_citation_field_bound"
        assert df["citation_evidence_status"].iloc[0] == "field_bound"
        assert "entity_reference_score" in df.columns
        assert "cross_source_gap" in df.columns
        assert pipeline.source_unavailable_report() is None

    @patch("trustdata.llm_mining._lazy_import_httpx")
    def test_all_403_404_attempts_produce_a_manual_source_report(self, mock_lazy_httpx):
        task = self._make_task()
        pipeline = MiningPipeline(MagicMock(), task, max_pages=10, delay=0.0, resolver=lambda _: ["8.8.8.8"])
        pipeline._crawl_plan = [
            CrawlStep(1, "fetch", "https://www.imdb.com/blocked", "blocked source"),
            CrawlStep(2, "fetch", "https://www.imdb.com/missing", "missing source"),
        ]
        blocked = MagicMock(status_code=403, text="Access denied")
        missing = MagicMock(status_code=404, text="Not found")
        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = [blocked, missing]
        mock_lazy_httpx.return_value = mock_httpx

        assert pipeline.execute_crawl_plan() == []
        report = pipeline.source_unavailable_report()

        assert report is not None
        assert report["status"] == "source_unavailable"
        assert report["status_counts"] == {"403": 1, "404": 1}
        assert report["attempted_urls"] == [
            {"url": "https://www.imdb.com/blocked", "status_code": 403},
            {"url": "https://www.imdb.com/missing", "status_code": 404},
        ]

    @patch("trustdata.llm_mining.MiningPipeline")
    @patch("trustdata.llm_mining.LLMClient")
    def test_empty_run_writes_source_unavailable_report(self, mock_client, mock_pipeline, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "llm:\n"
            "  api_type: openai\n"
            "  model: test-model\n"
            "  api_key_env: TEST_LLM_KEY\n"
            "crawl:\n"
            "  platform_domains:\n"
            "    aoty: [albumoftheyear.org]\n"
            "    rym: [rateyourmusic.com]\n",
            encoding="utf-8",
        )
        task_path = tmp_path / "task.yaml"
        task_path.write_text(
            "task:\n"
            "  domain: music\n"
            "  entity_type: album\n"
            "  entities: [OK Computer]\n"
            "  platforms: [aoty, rym]\n",
            encoding="utf-8",
        )
        output_path = tmp_path / "okcomputer.csv"
        unavailable_report = {
            "status": "source_unavailable",
            "attempted_urls": [{"url": "https://example.test/blocked", "status_code": 403}],
        }
        pipeline = mock_pipeline.return_value
        pipeline.to_canonical_dataframe.return_value = pd.DataFrame()
        pipeline.source_unavailable_report.return_value = unavailable_report

        result = run_mining(config_path, task_path, output_path)

        assert result.empty
        assert output_path.exists()
        report_path = tmp_path / "okcomputer.source_unavailable.json"
        assert json.loads(report_path.read_text(encoding="utf-8")) == unavailable_report


class TestSafeCrawling:
    def _pipeline(self, *, resolver=lambda _: ["8.8.8.8"]):
        task = MiningTask(
            task_id="safe-crawl", domain="movies", entity_type="movie",
            entities=[{"name": "Inception"}], platforms=["imdb"], request_delay=0.0,
        )
        return MiningPipeline(MagicMock(), task, delay=0.0, resolver=resolver)

    @patch("trustdata.llm_mining._lazy_import_httpx")
    def test_unsafe_urls_are_blocked_before_http(self, mock_lazy_httpx):
        httpx = MagicMock()
        mock_lazy_httpx.return_value = httpx
        pipeline = self._pipeline(resolver=lambda _: ["127.0.0.1"])

        assert pipeline._fetch_url("https://www.imdb.com/title/1") is None
        assert pipeline._fetch_url("http://www.imdb.com/title/1") is None
        assert pipeline._fetch_url("https://127.0.0.1/internal") is None
        assert pipeline._fetch_url("https://attacker.example/anything") is None
        for blocked_address in ("10.0.0.7", "169.254.3.9", "::1"):
            assert self._pipeline(resolver=lambda _, address=blocked_address: [address])._fetch_url(
                "https://www.imdb.com/title/1"
            ) is None
        assert httpx.get.call_count == 0
        assert pipeline._blocked_urls

    def test_unknown_task_platform_requires_explicit_allowlist_entry(self):
        task = MiningTask(
            task_id="unknown", domain="movies", entity_type="movie",
            entities=[{"name": "Inception"}], platforms=["unlisted"],
        )
        with pytest.raises(ValueError, match="explicitly configured"):
            MiningPipeline(MagicMock(), task, resolver=lambda _: ["8.8.8.8"])

    @patch("trustdata.llm_mining._lazy_import_httpx")
    def test_redirect_target_is_validated_before_second_request(self, mock_lazy_httpx):
        redirect = MagicMock(status_code=302, text="")
        redirect.headers = {"location": "https://127.0.0.1/admin"}
        httpx = MagicMock()
        httpx.get.return_value = redirect
        mock_lazy_httpx.return_value = httpx
        pipeline = self._pipeline()

        assert pipeline._fetch_url("https://www.imdb.com/title/1") is None
        assert httpx.get.call_count == 1

    @patch("trustdata.llm_mining._lazy_import_httpx")
    def test_relative_safe_redirect_is_followed_manually(self, mock_lazy_httpx):
        redirect = MagicMock(status_code=302, text="")
        redirect.headers = {"location": "/title/1/reviews?page=2"}
        page = MagicMock(status_code=200, text="ok")
        httpx = MagicMock()
        httpx.get.side_effect = [redirect, page]
        mock_lazy_httpx.return_value = httpx
        pipeline = self._pipeline()

        fetched = pipeline._fetch_url("https://www.imdb.com/title/1/reviews")
        assert fetched is not None
        assert fetched.url == "https://www.imdb.com/title/1/reviews?page=2"
        assert httpx.get.call_count == 2
        assert all(call.kwargs["follow_redirects"] is False for call in httpx.get.call_args_list)

    def test_follow_ups_must_be_html_candidates_and_relative_links_are_resolved(self):
        pipeline = self._pipeline()
        pipeline._llm.chat.return_value = json.dumps([
            {"action": "paginate", "url": "https://www.imdb.com/title/1/reviews?page=2", "purpose": "next"},
            {"action": "follow_link", "url": "https://attacker.example/", "purpose": "bad"},
        ])
        page = FetchedPage(
            url="https://www.imdb.com/title/1/reviews", status_code=200,
            content='<a href="?page=2">Next</a><a href="https://attacker.example/">bad</a>',
            fetched_at="now", content_hash="h", byte_length=1,
        )
        steps = pipeline._detect_follow_ups(page, CrawlStep(1, "fetch", page.url, "reviews"))

        assert [step.url for step in steps] == ["https://www.imdb.com/title/1/reviews?page=2"]
        assert any(item["url"] == "https://attacker.example/" for item in pipeline._blocked_urls)


class TestFieldBoundEvidenceAndIdentity:
    def _pipeline(self) -> MiningPipeline:
        task = MiningTask(
            task_id="evidence", domain="movies", entity_type="movie",
            entities=[{"name": "Inception"}], platforms=["imdb"], request_delay=0.0,
        )
        return MiningPipeline(MagicMock(), task, delay=0.0, resolver=lambda _: ["8.8.8.8"])

    @staticmethod
    def _record(*, rating=4.0, snippet="Inception rating 4/5 by u1 on 2024-03-15: Great film.", url="https://www.imdb.com/title/1/reviews"):
        return ExtractedRecord(
            entity_name="Inception", platform="imdb", rating=rating, rating_scale="0-5",
            contributor_id="u1", review_text="Great film.", created_at="2024-03-15T00:00:00Z",
            source_url=url, content_hash="a" * 64, citation_snippet=snippet, confidence=0.0,
        )

    def test_fabricated_rating_is_rejected_even_when_citation_exists(self):
        pipeline = self._pipeline()
        record = self._record(rating=5.0)
        pipeline._fetched_pages = [FetchedPage(record.source_url, 200, record.citation_snippet, "now", record.content_hash, 1)]
        pipeline._records = [record]

        assert pipeline.verify_records() == []
        assert record.confidence < 1.0
        assert record.evidence_status == "field_mismatch"

    def test_full_evidence_is_bound_and_ids_use_complete_evidence(self):
        pipeline = self._pipeline()
        first = self._record(snippet="Inception rating 4/5 by u1 on 2024-03-15: Great film. First continuation.")
        second = self._record(snippet="Inception rating 4/5 by u1 on 2024-03-15: Great film. Second continuation.")
        page_content = f"{first.citation_snippet} {second.citation_snippet}"
        pipeline._fetched_pages = [FetchedPage(first.source_url, 200, page_content, "now", first.content_hash, 1)]
        pipeline._records = [first, second]

        assert len(pipeline.verify_records()) == 2
        frame = pipeline.to_canonical_dataframe()
        assert frame["citation_confidence"].eq(1.0).all()
        assert frame["record_id"].nunique() == 2
        assert frame["evidence_fingerprint"].nunique() == 2

    def test_exact_duplicate_evidence_is_deduplicated(self):
        pipeline = self._pipeline()
        first = self._record()
        duplicate = self._record()
        pipeline._fetched_pages = [FetchedPage(first.source_url, 200, first.citation_snippet, "now", first.content_hash, 1)]
        pipeline._records = [first, duplicate]

        pipeline.verify_records()
        frame = pipeline.to_canonical_dataframe()
        assert len(frame) == 1
        assert pipeline._deduplicated_records == 1
