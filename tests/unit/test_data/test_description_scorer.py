"""Tests for the LLM description quality scorer."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import httpx

from pricepoint.data.housing.description_scorer import (
    build_system_prompt,
    build_user_prompt,
    call_ollama,
    compute_description_hash,
    extract_json_from_text,
    parse_llm_response,
    score_all_descriptions,
    score_descriptions_batch,
)

BASIC_RAW = {
    "quality_score": 50,
    "quality_reasoning": "test",
    "positive_factors": [],
    "negative_factors": [],
}


def _make_raw(score=50, reasoning="test", pos=None, neg=None):
    return {
        "quality_score": score,
        "quality_reasoning": reasoning,
        "positive_factors": pos if pos is not None else [],
        "negative_factors": neg if neg is not None else [],
    }


# ---------------------------------------------------------------------------
# TestComputeDescriptionHash
# ---------------------------------------------------------------------------


class TestComputeDescriptionHash:
    def test_deterministic(self):
        """Same input produces same hash."""
        h1 = compute_description_hash("beautiful home")
        h2 = compute_description_hash("beautiful home")
        assert h1 == h2
        assert len(h1) == 64

    def test_different_inputs(self):
        """Different inputs produce different hashes."""
        h1 = compute_description_hash("beautiful home")
        h2 = compute_description_hash("ugly home")
        assert h1 != h2

    def test_empty_string(self):
        """Empty string still produces a valid hash."""
        h = compute_description_hash("")
        assert len(h) == 64


# ---------------------------------------------------------------------------
# TestBuildPrompts
# ---------------------------------------------------------------------------


class TestBuildPrompts:
    def test_system_prompt_contains_scoring_guidelines(self):
        prompt = build_system_prompt()
        assert "SCORING GUIDELINES" in prompt
        assert "0-100" in prompt
        assert "quality_score" in prompt

    def test_user_prompt_embeds_description(self):
        prompt = build_user_prompt("A lovely 3-bed ranch")
        assert "A lovely 3-bed ranch" in prompt

    def test_user_prompt_has_delimiters(self):
        prompt = build_user_prompt("test description")
        assert "---" in prompt
        assert prompt.count("---") == 2


# ---------------------------------------------------------------------------
# TestExtractJsonFromText
# ---------------------------------------------------------------------------


class TestExtractJsonFromText:
    def test_direct_json(self):
        text = '{"quality_score": 75, "quality_reasoning": "good"}'
        result = extract_json_from_text(text)
        assert result == {"quality_score": 75, "quality_reasoning": "good"}

    def test_code_fence(self):
        text = '```json\n{"quality_score": 60}\n```'
        result = extract_json_from_text(text)
        assert result == {"quality_score": 60}

    def test_text_wrapped(self):
        text = 'Here is my analysis:\n{"quality_score": 45, "quality_reasoning": "average"}\nDone.'
        result = extract_json_from_text(text)
        assert result["quality_score"] == 45

    def test_invalid_json(self):
        text = "this is not json at all"
        result = extract_json_from_text(text)
        assert result is None

    def test_empty_string(self):
        result = extract_json_from_text("")
        assert result is None


# ---------------------------------------------------------------------------
# TestParseLlmResponse
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    def test_valid_response(self):
        raw = {
            "quality_score": 72,
            "quality_reasoning": "Good condition with updates.",
            "positive_factors": ["new roof", "hardwood floors"],
            "negative_factors": ["dated bathrooms"],
        }
        result = parse_llm_response(raw)
        assert result["quality_score"] == 72
        assert result["quality_reasoning"] == "Good condition with updates."
        assert result["positive_factors"] == ["new roof", "hardwood floors"]
        assert result["negative_factors"] == ["dated bathrooms"]

    def test_score_clamped_high(self):
        result = parse_llm_response(_make_raw(score=150))
        assert result["quality_score"] == 100

    def test_score_clamped_low(self):
        result = parse_llm_response(_make_raw(score=-10))
        assert result["quality_score"] == 0

    def test_all_null_insufficient_description(self):
        raw = {
            "quality_score": None,
            "quality_reasoning": None,
            "positive_factors": None,
            "negative_factors": None,
        }
        result = parse_llm_response(raw)
        assert result["quality_score"] is None
        assert result["quality_reasoning"] is None
        assert result["positive_factors"] is None
        assert result["negative_factors"] is None

    def test_non_int_score_defaults_null(self):
        result = parse_llm_response(_make_raw(score="high"))
        assert result["quality_score"] is None

    def test_invalid_reasoning(self):
        result = parse_llm_response(_make_raw(reasoning=123))
        assert result["quality_reasoning"] is None

    def test_valid_factors(self):
        raw = _make_raw(
            score=65,
            reasoning="decent",
            pos=["granite counters", "new HVAC"],
            neg=["small lot"],
        )
        result = parse_llm_response(raw)
        assert len(result["positive_factors"]) == 2
        assert len(result["negative_factors"]) == 1

    def test_invalid_factors_default_empty(self):
        raw = {
            "quality_score": 50,
            "quality_reasoning": "test",
            "positive_factors": "not a list",
            "negative_factors": 42,
        }
        result = parse_llm_response(raw)
        assert result["positive_factors"] == []
        assert result["negative_factors"] == []

    def test_float_score_converted_to_int(self):
        result = parse_llm_response(_make_raw(score=72.8))
        assert result["quality_score"] == 72
        assert isinstance(result["quality_score"], int)


# ---------------------------------------------------------------------------
# TestCallOllama (async)
# ---------------------------------------------------------------------------


def _make_async_return(value):
    """Create a coroutine that returns a value."""

    async def _coro(*args, **kwargs):
        return value

    return _coro


def _make_async_raise(exc):
    """Create a coroutine that raises an exception."""

    async def _coro(*args, **kwargs):
        raise exc

    return _coro


class TestCallOllama:
    def test_success(self):
        response_data = {
            "response": json.dumps(
                {
                    "quality_score": 65,
                    "quality_reasoning": "Average home.",
                    "positive_factors": ["garage"],
                    "negative_factors": [],
                }
            )
        }
        mock_request = httpx.Request("POST", "http://test/api/generate")
        mock_response = httpx.Response(200, json=response_data, request=mock_request)
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_return(mock_response)

        result = asyncio.run(call_ollama("A nice home", client=mock_client))
        assert result is not None
        assert result["quality_score"] == 65

    def test_http_error(self):
        mock_response = httpx.Response(500)
        exc = httpx.HTTPStatusError(
            "error",
            request=httpx.Request("POST", "http://x"),
            response=mock_response,
        )
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_raise(exc)

        result = asyncio.run(call_ollama("test", client=mock_client))
        assert result is None

    def test_timeout(self):
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_raise(httpx.TimeoutException("timeout"))

        result = asyncio.run(call_ollama("test", client=mock_client))
        assert result is None

    def test_bad_json_response(self):
        response_data = {"response": "not json at all, just text"}
        mock_request = httpx.Request("POST", "http://test/api/generate")
        mock_response = httpx.Response(200, json=response_data, request=mock_request)
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_return(mock_response)

        result = asyncio.run(call_ollama("test", client=mock_client))
        assert result is None


# ---------------------------------------------------------------------------
# TestScoreDescriptionsBatch (async)
# ---------------------------------------------------------------------------


class TestScoreDescriptionsBatch:
    def test_processes_all(self):
        async def mock_ollama(desc, **kwargs):
            return _make_raw(score=60, reasoning="OK")

        listings = [
            {"id": 1, "description": "Nice home with garage"},
            {"id": 2, "description": "Cozy starter home"},
        ]
        results = asyncio.run(
            score_descriptions_batch(
                listings,
                "test-model",
                "abc123",
                ollama_fn=mock_ollama,
                max_concurrent=2,
            )
        )
        assert len(results) == 2
        assert all(r["quality_score"] == 60 for r in results)

    def test_skips_unchanged_hash(self):
        async def mock_ollama(desc, **kwargs):
            return _make_raw(score=70)

        listings = [{"id": 1, "description": "Same description"}]
        desc_hash = compute_description_hash("Same description")
        existing = {(1, "model", "v1"): desc_hash}

        results = asyncio.run(
            score_descriptions_batch(
                listings,
                "model",
                "v1",
                existing_hashes=existing,
                ollama_fn=mock_ollama,
            )
        )
        assert len(results) == 0

    def test_handles_failures_gracefully(self):
        async def mock_ollama(desc, **kwargs):
            return None

        listings = [{"id": 1, "description": "A home"}]
        results = asyncio.run(
            score_descriptions_batch(listings, "model", "v1", ollama_fn=mock_ollama)
        )
        assert len(results) == 1
        assert results[0]["raw_response"] == {"error": "ollama_call_failed"}

    def test_callback_injection(self):
        call_count = 0

        async def mock_ollama(desc, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_raw(score=55, reasoning="ok")

        listings = [{"id": 1, "description": "test"}]
        asyncio.run(score_descriptions_batch(listings, "m", "v", ollama_fn=mock_ollama))
        assert call_count == 1


# ---------------------------------------------------------------------------
# TestScoreAllDescriptions
# ---------------------------------------------------------------------------

_SCORER = "pricepoint.data.housing.description_scorer"


class TestScoreAllDescriptions:
    @patch(f"{_SCORER}.SessionLocal")
    @patch(f"{_SCORER}._get_model_version")
    def test_full_pipeline_mock(self, mock_version, mock_session_cls):
        mock_version.return_value = "abc123456789"

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock existing hashes query (empty)
        mock_session.execute.return_value.all.return_value = []

        async def mock_ollama(desc, **kwargs):
            return _make_raw()

        result = score_all_descriptions(batch_size=10, ollama_fn=mock_ollama)
        assert "scored" in result
        assert "skipped" in result
        assert "errors" in result

    @patch(f"{_SCORER}.SessionLocal")
    @patch(f"{_SCORER}._get_model_version")
    def test_empty_database(self, mock_version, mock_session_cls):
        mock_version.return_value = "abc123456789"

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # First call: existing hashes, second call: listings
        mock_session.execute.return_value.all.side_effect = [[], []]

        result = score_all_descriptions(batch_size=10)
        assert result["scored"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @patch(f"{_SCORER}.SessionLocal")
    @patch(f"{_SCORER}._get_model_version")
    def test_skips_same_hash(self, mock_version, mock_session_cls):
        mock_version.return_value = "abc123456789"

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        desc = "Beautiful home with hardwood floors"
        desc_hash = compute_description_hash(desc)

        # Mock existing hashes with matching hash
        existing_row = MagicMock()
        existing_row.listing_id = 1
        existing_row.model_name = "qwen2.5:32b"
        existing_row.model_version = "abc123456789"
        existing_row.description_hash = desc_hash

        # Mock listing
        listing_row = MagicMock()
        listing_row.id = 1
        listing_row.description = desc

        mock_session.execute.return_value.all.side_effect = [
            [existing_row],
            [listing_row],
        ]

        result = score_all_descriptions(batch_size=10)
        assert result["skipped"] == 1
        assert result["scored"] == 0
