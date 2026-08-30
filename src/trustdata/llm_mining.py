"""LLM-driven universal web mining for cross-source trust verification.

LLM drives *where to find data* and *how to parse it*; httpx handles the
actual web fetching, ensuring all data comes from real web pages rather than
model parameters.  Mined data is normalised into the TrustData canonical
schema and can be fed directly into ``assess_data.py``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .normalization import normalize_name, stable_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy httpx import
# ---------------------------------------------------------------------------

def _lazy_import_httpx():
    """Import httpx on demand so the rest of trustdata works without it."""
    try:
        import httpx  # noqa: F811
        return httpx
    except ImportError:
        raise ImportError(
            "The 'httpx' package is required for LLM mining features. "
            "Install it with: pip install 'trustdata[mining]' or pip install httpx"
        )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMProvider:
    """Configuration for an LLM API provider."""

    api_type: str                   # "openai" | "anthropic"
    model: str                      # model identifier
    api_key_env: str                # environment variable name (never store keys)
    base_url: str | None = None     # OpenAI-compatible endpoint override
    max_tokens: int = 4096
    temperature: float = 0.1


@dataclass(frozen=True)
class MiningTask:
    """A structured mining task description."""

    task_id: str
    domain: str                     # "movies" / "music" / "restaurants" / ...
    entity_type: str                # "movie" / "music_album" / "restaurant" / ...
    entities: list[dict[str, str]]
    platforms: list[str]
    search_hints: list[str] = field(default_factory=list)
    max_pages_per_entity: int = 5
    request_delay: float = 2.0
    language: str = "zh"


@dataclass
class FetchedPage:
    """A web page fetched by httpx."""

    url: str
    status_code: int
    content: str
    fetched_at: str
    content_hash: str               # SHA256[:20]
    byte_length: int


@dataclass
class CrawlStep:
    """A single step in the crawl plan."""

    step_id: int
    action: str                     # "fetch" | "paginate" | "follow_link"
    url: str
    purpose: str
    completed: bool = False
    fetched_page: FetchedPage | None = None


@dataclass
class ExtractedRecord:
    """A single record extracted from a web page."""

    entity_name: str
    platform: str
    rating: float | None
    rating_scale: str               # "0-5", "0-10", "0-100", etc.
    contributor_id: str | None
    review_text: str | None
    created_at: str | None
    source_url: str
    content_hash: str
    citation_snippet: str
    confidence: float               # 0.0-1.0


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _html_to_text_snippet(html: str, max_chars: int = 8000) -> str:
    """Strip HTML tags and collapse whitespace to produce a plain-text snippet."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _truncate_for_context(text: str, max_chars: int = 60000) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _extract_json_block(text: str) -> str:
    """Extract the first JSON array or object from LLM output.

    Handles markdown fenced blocks (```json ... ```) as well as raw JSON.
    """
    fenced = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if fenced:
        return fenced.group(1).strip()
    # Try to find raw JSON array or object
    for pattern in [r"(\[[\s\S]*\])", r"(\{[\s\S]*\})"]:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return text.strip()


def _normalize_rating(value: float | None, scale: str) -> float | None:
    """Normalise a rating value to the 0-5 canonical scale."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    scale = scale.strip().lower()
    match = re.match(r"(\d+)\s*[-–]\s*(\d+)", scale)
    if not match:
        return max(0.0, min(5.0, value))

    lo, hi = float(match.group(1)), float(match.group(2))
    if hi <= lo:
        return max(0.0, min(5.0, value))
    normalised = (value - lo) / (hi - lo) * 5.0
    return max(0.0, min(5.0, round(normalised, 2)))


def _citation_score(snippet: str, page_content: str) -> float:
    """Score how well *snippet* is evidenced in *page_content*.

    Returns 1.0 for exact substring match, 0.9 for whitespace/case-
    normalised match, and a word-overlap ratio otherwise.
    """
    if not snippet or not page_content:
        return 0.0

    # Exact substring
    if snippet in page_content:
        return 1.0

    # Normalised match
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    norm_snippet = _norm(snippet)
    norm_content = _norm(page_content)
    if norm_snippet and norm_snippet in norm_content:
        return 0.9

    # Word overlap
    snippet_words = set(norm_snippet.split())
    content_words = set(norm_content.split())
    if not snippet_words:
        return 0.0
    overlap = len(snippet_words & content_words) / len(snippet_words)
    return round(min(overlap * 0.7, 0.7), 2)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Unified client supporting OpenAI-compatible and Anthropic Messages APIs."""

    def __init__(self, provider: LLMProvider) -> None:
        import os
        self._provider = provider
        self._api_key = os.environ.get(provider.api_key_env, "")
        if not self._api_key:
            raise ValueError(
                f"Environment variable {provider.api_key_env!r} is not set. "
                f"Set it to your {provider.api_type} API key."
            )
        self._httpx = _lazy_import_httpx()

    def chat(self, system: str, user: str) -> str:
        """Send a chat completion request and return the assistant message."""
        if self._provider.api_type == "anthropic":
            return self._chat_anthropic(system, user)
        return self._chat_openai(system, user)

    def _chat_openai(self, system: str, user: str) -> str:
        base = self._provider.base_url or "https://api.openai.com/v1"
        url = f"{base.rstrip('/')}/chat/completions"
        payload = {
            "model": self._provider.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self._provider.max_tokens,
            "temperature": self._provider.temperature,
        }
        response = self._httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _chat_anthropic(self, system: str, user: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self._provider.model,
            "max_tokens": self._provider.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        response = self._httpx.post(
            url,
            json=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


# ---------------------------------------------------------------------------
# Task parsing
# ---------------------------------------------------------------------------

def parse_task_yaml(path: Path) -> MiningTask:
    """Parse a YAML task file into a ``MiningTask``."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    task = raw.get("task", raw)
    entities = task["entities"]
    # Support both dict-list and string-list forms
    if entities and isinstance(entities[0], str):
        entities = [{"name": e} for e in entities]
    task_id = stable_id(
        task.get("domain", ""),
        json.dumps(entities, ensure_ascii=False, sort_keys=True),
        prefix="mining_task",
    )
    return MiningTask(
        task_id=task_id,
        domain=task.get("domain", "general"),
        entity_type=task.get("entity_type", "item"),
        entities=entities,
        platforms=task.get("platforms", []),
        search_hints=task.get("search_hints", []),
        max_pages_per_entity=int(task.get("max_pages_per_entity", 5)),
        request_delay=float(task.get("request_delay", 2.0)),
        language=task.get("language", "zh"),
    )


def parse_task_natural_language(description: str, llm: LLMClient) -> MiningTask:
    """Use LLM to parse a natural-language task description into ``MiningTask``."""
    system = (
        "You are a structured-data extraction assistant. "
        "Parse the user's mining task description into a JSON object with these fields:\n"
        '  domain (str), entity_type (str), entities (list of {name, ...}), '
        '  platforms (list of str), search_hints (list of str), '
        '  max_pages_per_entity (int, default 5), language (str, default "zh").\n'
        "Return ONLY a JSON object, no explanation."
    )
    raw = llm.chat(system, description)
    parsed = json.loads(_extract_json_block(raw))
    entities = parsed.get("entities", [])
    if entities and isinstance(entities[0], str):
        entities = [{"name": e} for e in entities]
    task_id = stable_id(
        parsed.get("domain", ""),
        json.dumps(entities, ensure_ascii=False, sort_keys=True),
        prefix="mining_task",
    )
    return MiningTask(
        task_id=task_id,
        domain=parsed.get("domain", "general"),
        entity_type=parsed.get("entity_type", "item"),
        entities=entities,
        platforms=parsed.get("platforms", []),
        search_hints=parsed.get("search_hints", []),
        max_pages_per_entity=int(parsed.get("max_pages_per_entity", 5)),
        request_delay=float(parsed.get("request_delay", 2.0)),
        language=parsed.get("language", "zh"),
    )


# ---------------------------------------------------------------------------
# Mining Pipeline
# ---------------------------------------------------------------------------

_STRATEGY_SYSTEM_PROMPT = """\
You are a data-mining strategy planner for a data trustworthiness assessment system.
Given a target domain, entities, and platforms, generate a list of URLs to crawl.
Use your knowledge of platform URL structures (e.g. IMDB /title/ttXXXX/reviews/).
Only generate URLs — do NOT generate review data itself.
Output a JSON array: [{"action": "fetch", "url": "...", "purpose": "..."}]
Return ONLY the JSON array, no explanation."""

_EXTRACTION_SYSTEM_PROMPT = """\
You are a structured-data extractor for a data trustworthiness assessment system.
From the provided web page content, extract user review/rating records.

CRITICAL RULES:
1. ONLY extract data that actually exists on the page. NEVER fabricate or hallucinate.
2. Each record MUST include a "citation_snippet" — an EXACT substring from the page
   that proves the data exists.
3. Normalise ratings to a 0-5 scale and state the original scale in "rating_scale".
4. Set missing fields to null.
5. Return a JSON array of objects with these fields:
   entity_name, platform, rating, rating_scale, contributor_id, review_text,
   created_at, citation_snippet
Return ONLY the JSON array, no explanation."""

_FOLLOW_UP_SYSTEM_PROMPT = """\
You are a web navigation assistant. Given the text content of a web page,
identify pagination links or detail page links that would contain more
user reviews or ratings for the same entity.
Return a JSON array of at most 3 objects:
[{"action": "paginate"|"follow_link", "url": "...", "purpose": "..."}]
If there are no useful follow-up links, return an empty array [].
Return ONLY the JSON array, no explanation."""


class MiningPipeline:
    """Orchestrates the 5-phase LLM-driven mining pipeline."""

    def __init__(
        self,
        llm: LLMClient,
        task: MiningTask,
        *,
        max_pages: int = 50,
        delay: float = 2.0,
        user_agent: str = "TrustData-Miner/0.1 (academic-research)",
        request_timeout: float = 30.0,
        min_citation_score: float = 0.5,
    ) -> None:
        self._llm = llm
        self._task = task
        self._max_pages = max_pages
        self._delay = delay
        self._user_agent = user_agent
        self._request_timeout = request_timeout
        self._min_citation_score = min_citation_score

        self._crawl_plan: list[CrawlStep] = []
        self._fetched_pages: list[FetchedPage] = []
        self._records: list[ExtractedRecord] = []
        self._verified_records: list[ExtractedRecord] = []
        self._step_counter = 0

    # -- Phase 1: Strategy generation -----------------------------------------

    def generate_strategy(self) -> list[CrawlStep]:
        """Ask LLM to generate initial crawl plan (target URL list)."""
        entities_desc = json.dumps(self._task.entities, ensure_ascii=False)
        user_msg = (
            f"Domain: {self._task.domain}\n"
            f"Entity type: {self._task.entity_type}\n"
            f"Entities: {entities_desc}\n"
            f"Platforms: {', '.join(self._task.platforms)}\n"
            f"Language: {self._task.language}\n"
        )
        if self._task.search_hints:
            user_msg += f"URL hints: {', '.join(self._task.search_hints)}\n"
        user_msg += (
            f"\nGenerate up to {self._task.max_pages_per_entity} URLs per entity per platform."
        )

        raw = self._llm.chat(_STRATEGY_SYSTEM_PROMPT, user_msg)
        steps_data = json.loads(_extract_json_block(raw))
        self._crawl_plan = []
        for item in steps_data:
            self._step_counter += 1
            self._crawl_plan.append(CrawlStep(
                step_id=self._step_counter,
                action=item.get("action", "fetch"),
                url=item["url"],
                purpose=item.get("purpose", ""),
            ))
        logger.info("Phase 1: generated %d crawl steps", len(self._crawl_plan))
        return self._crawl_plan

    # -- Phase 2: Web fetching ------------------------------------------------

    def _fetch_url(self, url: str) -> FetchedPage | None:
        """Fetch a single URL with httpx."""
        httpx = _lazy_import_httpx()
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": self._user_agent},
                timeout=self._request_timeout,
                follow_redirects=True,
            )
            content = response.text
            content_bytes = content.encode("utf-8", errors="replace")
            return FetchedPage(
                url=url,
                status_code=response.status_code,
                content=content,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_hash=hashlib.sha256(content_bytes).hexdigest()[:20],
                byte_length=len(content_bytes),
            )
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return None

    def _detect_follow_ups(self, page: FetchedPage, step: CrawlStep) -> list[CrawlStep]:
        """Ask LLM to identify pagination/detail links in a fetched page."""
        snippet = _html_to_text_snippet(page.content, max_chars=8000)
        user_msg = (
            f"Page URL: {page.url}\n"
            f"Original purpose: {step.purpose}\n"
            f"Page content (text):\n{snippet}"
        )
        try:
            raw = self._llm.chat(_FOLLOW_UP_SYSTEM_PROMPT, user_msg)
            items = json.loads(_extract_json_block(raw))
        except Exception:
            return []

        visited = {s.url for s in self._crawl_plan}
        new_steps: list[CrawlStep] = []
        for item in items[:3]:
            url = item.get("url", "")
            if url and url not in visited:
                self._step_counter += 1
                new_steps.append(CrawlStep(
                    step_id=self._step_counter,
                    action=item.get("action", "follow_link"),
                    url=url,
                    purpose=item.get("purpose", ""),
                ))
                visited.add(url)
        return new_steps

    def execute_crawl_plan(self) -> list[FetchedPage]:
        """Execute crawl plan step by step, dynamically appending follow-ups."""
        pages_fetched = 0
        step_index = 0
        while step_index < len(self._crawl_plan) and pages_fetched < self._max_pages:
            step = self._crawl_plan[step_index]
            if step.completed:
                step_index += 1
                continue
            logger.info("Phase 2: fetching step %d — %s", step.step_id, step.url)
            page = self._fetch_url(step.url)
            step.completed = True
            if page and page.status_code == 200:
                step.fetched_page = page
                self._fetched_pages.append(page)
                pages_fetched += 1
                follow_ups = self._detect_follow_ups(page, step)
                self._crawl_plan.extend(follow_ups)
            step_index += 1
            if step_index < len(self._crawl_plan):
                time.sleep(self._delay)
        logger.info("Phase 2: fetched %d pages", pages_fetched)
        return self._fetched_pages

    # -- Phase 3: Intelligent extraction --------------------------------------

    def extract_records(self) -> list[ExtractedRecord]:
        """Send each fetched page to LLM for structured data extraction."""
        self._records = []
        for page in self._fetched_pages:
            text_content = _html_to_text_snippet(page.content, max_chars=60000)
            truncated = _truncate_for_context(text_content)
            user_msg = (
                f"Source URL: {page.url}\n"
                f"Domain: {self._task.domain}\n"
                f"Target entities: {json.dumps(self._task.entities, ensure_ascii=False)}\n"
                f"\nPage content:\n{truncated}"
            )
            try:
                raw = self._llm.chat(_EXTRACTION_SYSTEM_PROMPT, user_msg)
                items = json.loads(_extract_json_block(raw))
            except Exception as exc:
                logger.warning("Extraction failed for %s: %s", page.url, exc)
                continue

            for item in items:
                self._records.append(ExtractedRecord(
                    entity_name=item.get("entity_name", ""),
                    platform=item.get("platform", ""),
                    rating=item.get("rating"),
                    rating_scale=item.get("rating_scale", "0-5"),
                    contributor_id=item.get("contributor_id"),
                    review_text=item.get("review_text"),
                    created_at=item.get("created_at"),
                    source_url=page.url,
                    content_hash=page.content_hash,
                    citation_snippet=item.get("citation_snippet", ""),
                    confidence=1.0,  # will be updated in verification
                ))
        logger.info("Phase 3: extracted %d records", len(self._records))
        return self._records

    # -- Phase 4: Anti-hallucination verification -----------------------------

    def verify_records(self) -> list[ExtractedRecord]:
        """Verify each record's citation_snippet against its source page."""
        page_map: dict[str, str] = {}
        for page in self._fetched_pages:
            text = _html_to_text_snippet(page.content, max_chars=200000)
            page_map[page.content_hash] = text

        self._verified_records = []
        discarded = 0
        for record in self._records:
            page_text = page_map.get(record.content_hash, "")
            score = _citation_score(record.citation_snippet, page_text)
            record.confidence = score
            if score >= self._min_citation_score:
                self._verified_records.append(record)
            else:
                discarded += 1
                logger.debug(
                    "Discarded record (score=%.2f): %s — %s",
                    score, record.entity_name, record.citation_snippet[:50],
                )
        logger.info(
            "Phase 4: verified %d records, discarded %d",
            len(self._verified_records), discarded,
        )
        return self._verified_records

    # -- Phase 5: Canonical output --------------------------------------------

    def to_canonical_dataframe(self) -> pd.DataFrame:
        """Convert verified records to a TrustData canonical schema DataFrame."""
        if not self._verified_records:
            return pd.DataFrame()

        rows: list[dict[str, Any]] = []
        for rec in self._verified_records:
            normalised_rating = _normalize_rating(rec.rating, rec.rating_scale)
            entity_id = stable_id(
                normalize_name(rec.entity_name),
                self._task.domain,
                prefix="entity",
            )
            record_id = stable_id(
                rec.platform,
                entity_id,
                rec.contributor_id or "",
                rec.citation_snippet[:40],
                prefix="mined_record",
            )
            contributor_id = (
                stable_id(rec.contributor_id, rec.platform, prefix="contributor")
                if rec.contributor_id
                else None
            )
            rows.append({
                "record_id": record_id,
                "entity_id": entity_id,
                "entity_type": self._task.entity_type,
                "entity_name": rec.entity_name,
                "contributor_id": contributor_id,
                "rating": normalised_rating,
                "review_text": rec.review_text,
                "created_at": rec.created_at,
                "source": f"llm_mined:{rec.platform}",
                "verification_level": "llm_mined_web_citation",
                "ai_disclosure": "unknown",
                "is_synthetic": False,
                "source_url": rec.source_url,
                "content_hash": rec.content_hash,
                "citation_snippet": rec.citation_snippet,
                "citation_confidence": rec.confidence,
            })

        df = pd.DataFrame(rows)
        df = enrich_cross_source_fields(df)
        return df


# ---------------------------------------------------------------------------
# Cross-source enrichment
# ---------------------------------------------------------------------------

def enrich_cross_source_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ``entity_reference_score`` and ``cross_source_gap`` per entity.

    Groups records by ``entity_id``, computes the mean rating across distinct
    sources as the reference score, and the max absolute pairwise source
    difference as the cross-source gap.
    """
    if df.empty or "entity_id" not in df.columns or "rating" not in df.columns:
        return df

    result = df.copy()
    rating = pd.to_numeric(result["rating"], errors="coerce")

    # Per-source mean rating for each entity
    source_col = result.get("source", pd.Series("unknown", index=result.index))
    group = pd.DataFrame({
        "entity_id": result["entity_id"],
        "source": source_col,
        "rating": rating,
    })
    source_means = (
        group.dropna(subset=["rating"])
        .groupby(["entity_id", "source"])["rating"]
        .mean()
        .reset_index()
    )

    # Entity reference score: mean of source-level means
    entity_ref = source_means.groupby("entity_id")["rating"].mean()
    entity_ref.name = "entity_reference_score"

    # Cross-source gap: max pairwise difference between source means
    def _max_gap(ratings: pd.Series) -> float:
        vals = ratings.values
        if len(vals) < 2:
            return 0.0
        return float(np.max(vals) - np.min(vals))

    entity_gap = source_means.groupby("entity_id")["rating"].apply(_max_gap)
    entity_gap.name = "cross_source_gap"

    ref_df = pd.DataFrame({"entity_reference_score": entity_ref, "cross_source_gap": entity_gap})
    result = result.merge(ref_df, left_on="entity_id", right_index=True, how="left")
    return result


# ---------------------------------------------------------------------------
# Top-level convenience function
# ---------------------------------------------------------------------------

def run_mining(
    config_path: Path,
    task_source: Path | str,
    output_path: Path,
    *,
    verbose: bool = False,
) -> pd.DataFrame:
    """One-shot mining pipeline: config -> task -> strategy -> crawl -> extract -> verify -> output."""
    from .io import write_table

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Load config
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    llm_cfg = config["llm"]
    crawl_cfg = config.get("crawl", {})
    verify_cfg = config.get("verification", {})

    provider = LLMProvider(
        api_type=llm_cfg["api_type"],
        model=llm_cfg["model"],
        api_key_env=llm_cfg["api_key_env"],
        base_url=llm_cfg.get("base_url"),
        max_tokens=int(llm_cfg.get("max_tokens", 4096)),
        temperature=float(llm_cfg.get("temperature", 0.1)),
    )
    llm = LLMClient(provider)

    # Parse task
    task_path = Path(task_source) if not isinstance(task_source, str) else None
    if task_path and task_path.suffix in (".yaml", ".yml") and task_path.exists():
        task = parse_task_yaml(task_path)
    elif isinstance(task_source, Path) and task_source.suffix in (".yaml", ".yml"):
        task = parse_task_yaml(task_source)
    else:
        task = parse_task_natural_language(str(task_source), llm)

    # Run pipeline
    pipeline = MiningPipeline(
        llm,
        task,
        max_pages=int(crawl_cfg.get("max_pages_total", 50)),
        delay=float(crawl_cfg.get("request_delay", 2.0)),
        user_agent=crawl_cfg.get("user_agent", "TrustData-Miner/0.1 (academic-research)"),
        request_timeout=float(crawl_cfg.get("request_timeout", 30.0)),
        min_citation_score=float(verify_cfg.get("min_citation_score", 0.5)),
    )

    pipeline.generate_strategy()
    pipeline.execute_crawl_plan()
    pipeline.extract_records()
    pipeline.verify_records()
    df = pipeline.to_canonical_dataframe()

    if df.empty:
        logger.warning("No records survived verification. Output will be empty.")
        write_table(pd.DataFrame(), output_path)
        return df

    # Write output
    write_table(df, output_path)
    logger.info("Wrote %d records to %s", len(df), output_path)

    # Write summary
    summary = {
        "task_id": task.task_id,
        "domain": task.domain,
        "entity_type": task.entity_type,
        "entities": task.entities,
        "platforms": task.platforms,
        "pages_fetched": len(pipeline._fetched_pages),
        "records_extracted": len(pipeline._records),
        "records_verified": len(pipeline._verified_records),
        "output_path": str(output_path),
    }
    summary_path = output_path.with_name(f"{output_path.stem}.mining_summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    logger.info("Summary: %s", summary_path)

    return df
