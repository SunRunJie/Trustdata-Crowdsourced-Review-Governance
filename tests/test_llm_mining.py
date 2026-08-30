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
    parse_task_yaml,
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
        assert np.isclose(result["entity_reference_score"].iloc[0], 3.5)
        assert np.isclose(result["cross_source_gap"].iloc[0], 0.0)

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
        # Follow-up response (no follow-ups)
        follow_up_response = "[]"
        # Extraction response
        page_content = (
            '<div class="review">'
            '<span class="rating">8.5</span>'
            '<span class="user">user123</span>'
            '<p>Amazing movie with great visual effects and a mind-bending plot.</p>'
            '<span class="date">2024-03-15</span>'
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
            "citation_snippet": "Amazing movie with great visual effects and a mind-bending plot.",
        }])

        # Set up LLM chat mock to return different responses
        call_count = [0]
        def mock_chat(system, user):
            call_count[0] += 1
            if call_count[0] == 1:
                return strategy_response
            elif call_count[0] == 2:
                return follow_up_response
            else:
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
        assert df["verification_level"].iloc[0] == "llm_mined_web_citation"
        assert "entity_reference_score" in df.columns
        assert "cross_source_gap" in df.columns
