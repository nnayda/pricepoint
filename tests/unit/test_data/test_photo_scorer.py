"""Tests for the LLM photo quality scorer."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import httpx

from pricepoint.data.housing.photo_scorer import (
    build_system_prompt,
    build_user_prompt,
    call_ollama_vision,
    compute_photos_hash,
    download_photos_as_base64,
    merge_photo_results,
    parse_llm_response,
    score_all_photos,
    score_photos_batch,
)

BASIC_RAW = {
    "visual_quality_score": 50,
    "visual_reasoning": "Average condition",
    "detected_features": {"kitchen_features": [], "flooring": ["carpet"]},
    "renovation_level": "original_maintained",
}


def _make_raw(
    score=50, reasoning="Average condition", features=None, renovation="original_maintained"
):
    return {
        "visual_quality_score": score,
        "visual_reasoning": reasoning,
        "detected_features": features if features is not None else {},
        "renovation_level": renovation,
    }


# ---------------------------------------------------------------------------
# TestComputePhotosHash
# ---------------------------------------------------------------------------


class TestComputePhotosHash:
    def test_deterministic(self):
        """Same input produces same hash."""
        h1 = compute_photos_hash(["photos/a.jpg", "photos/b.jpg"])
        h2 = compute_photos_hash(["photos/a.jpg", "photos/b.jpg"])
        assert h1 == h2
        assert len(h1) == 64

    def test_order_independent(self):
        """Different order produces same hash (sorted internally)."""
        h1 = compute_photos_hash(["photos/b.jpg", "photos/a.jpg"])
        h2 = compute_photos_hash(["photos/a.jpg", "photos/b.jpg"])
        assert h1 == h2

    def test_different_keys_differ(self):
        """Different keys produce different hashes."""
        h1 = compute_photos_hash(["photos/a.jpg"])
        h2 = compute_photos_hash(["photos/b.jpg"])
        assert h1 != h2

    def test_empty_list(self):
        """Empty list still produces a valid hash."""
        h = compute_photos_hash([])
        assert len(h) == 64


# ---------------------------------------------------------------------------
# TestBuildPrompts
# ---------------------------------------------------------------------------


class TestBuildPrompts:
    def test_system_prompt_contains_scoring_guidelines(self):
        prompt = build_system_prompt()
        assert "SCORING GUIDELINES" in prompt
        assert "0-100" in prompt
        assert "visual_quality_score" in prompt

    def test_system_prompt_contains_visual_priority(self):
        prompt = build_system_prompt()
        assert "VISUAL PRIORITY LIST" in prompt
        assert "Kitchen" in prompt

    def test_system_prompt_contains_detected_features(self):
        prompt = build_system_prompt()
        assert "detected_features" in prompt
        assert "renovation_level" in prompt

    def test_user_prompt_correct(self):
        prompt = build_user_prompt()
        assert "Analyze these property listing photos" in prompt


# ---------------------------------------------------------------------------
# TestParseLlmResponse
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    def test_valid_response(self):
        raw = {
            "visual_quality_score": 72,
            "visual_reasoning": "Good condition with updates.",
            "detected_features": {"kitchen_features": ["granite counters"]},
            "renovation_level": "partially_updated",
        }
        result = parse_llm_response(raw)
        assert result["visual_quality_score"] == 72
        assert result["visual_reasoning"] == "Good condition with updates."
        assert result["detected_features"] == {"kitchen_features": ["granite counters"]}
        assert result["renovation_level"] == "partially_updated"

    def test_score_clamped_high(self):
        result = parse_llm_response(_make_raw(score=150))
        assert result["visual_quality_score"] == 100

    def test_score_clamped_low(self):
        result = parse_llm_response(_make_raw(score=-10))
        assert result["visual_quality_score"] == 0

    def test_all_null_insufficient_photos(self):
        raw = {
            "visual_quality_score": None,
            "visual_reasoning": None,
            "detected_features": None,
            "renovation_level": None,
        }
        result = parse_llm_response(raw)
        assert result["visual_quality_score"] is None
        assert result["visual_reasoning"] is None
        assert result["detected_features"] is None
        assert result["renovation_level"] is None

    def test_non_int_score_defaults_null(self):
        result = parse_llm_response(_make_raw(score="high"))
        assert result["visual_quality_score"] is None

    def test_invalid_reasoning(self):
        result = parse_llm_response(_make_raw(reasoning=123))
        assert result["visual_reasoning"] is None

    def test_float_score_converted_to_int(self):
        result = parse_llm_response(_make_raw(score=72.8))
        assert result["visual_quality_score"] == 72
        assert isinstance(result["visual_quality_score"], int)

    def test_invalid_features_default_empty_dict(self):
        raw = _make_raw()
        raw["detected_features"] = "not a dict"
        result = parse_llm_response(raw)
        assert result["detected_features"] == {}

    def test_invalid_renovation_default_none(self):
        raw = _make_raw()
        raw["renovation_level"] = 42
        result = parse_llm_response(raw)
        assert result["renovation_level"] is None


# ---------------------------------------------------------------------------
# TestDownloadPhotosAsBase64
# ---------------------------------------------------------------------------


class TestDownloadPhotosAsBase64:
    @patch("pricepoint.data.housing.photo_scorer.get_settings")
    def test_downloads_photos(self, mock_settings):
        mock_settings.return_value.s3_bucket = "test-bucket"

        mock_body = MagicMock()
        mock_body.read.return_value = b"fake image data"
        mock_client = MagicMock()
        mock_client.get_object.return_value = {"Body": mock_body}

        result = download_photos_as_base64(
            ["photos/a.jpg", "photos/b.jpg"],
            s3_client=mock_client,
        )
        assert len(result) == 2
        assert mock_client.get_object.call_count == 2

    @patch("pricepoint.data.housing.photo_scorer.get_settings")
    def test_handles_missing_photo(self, mock_settings):
        mock_settings.return_value.s3_bucket = "test-bucket"

        mock_client = MagicMock()
        mock_client.get_object.side_effect = Exception("NoSuchKey")

        result = download_photos_as_base64(
            ["photos/missing.jpg"],
            s3_client=mock_client,
        )
        assert len(result) == 0

    @patch("pricepoint.data.housing.photo_scorer.get_settings")
    def test_empty_keys(self, mock_settings):
        result = download_photos_as_base64([], s3_client=MagicMock())
        assert result == []


# ---------------------------------------------------------------------------
# TestCallOllamaVision (async)
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


class TestCallOllamaVision:
    def test_success(self):
        response_data = {
            "response": json.dumps(
                {
                    "visual_quality_score": 65,
                    "visual_reasoning": "Average home.",
                    "detected_features": {},
                    "renovation_level": "original_maintained",
                }
            )
        }
        mock_request = httpx.Request("POST", "http://test/api/generate")
        mock_response = httpx.Response(200, json=response_data, request=mock_request)
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_return(mock_response)

        result = asyncio.run(call_ollama_vision("base64img1", client=mock_client))
        assert result is not None
        assert result["visual_quality_score"] == 65

    def test_single_image_in_payload(self):
        """Verify single image is wrapped in a list in the payload."""
        response_data = {"response": json.dumps(_make_raw())}
        mock_request = httpx.Request("POST", "http://test/api/generate")
        mock_response = httpx.Response(200, json=response_data, request=mock_request)

        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = mock_post

        asyncio.run(call_ollama_vision("img1", client=mock_client))
        assert "images" in captured_payload
        assert captured_payload["images"] == ["img1"]

    def test_http_error(self):
        mock_response = httpx.Response(500)
        exc = httpx.HTTPStatusError(
            "error",
            request=httpx.Request("POST", "http://x"),
            response=mock_response,
        )
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_raise(exc)

        result = asyncio.run(call_ollama_vision("img", client=mock_client))
        assert result is None

    def test_timeout(self):
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.post = _make_async_raise(httpx.TimeoutException("timeout"))

        result = asyncio.run(call_ollama_vision("img", client=mock_client))
        assert result is None


# ---------------------------------------------------------------------------
# TestScorePhotosBatch (async)
# ---------------------------------------------------------------------------


class TestMergePhotoResults:
    def test_median_score_odd(self):
        results = [
            _make_raw(score=40, reasoning="Low"),
            _make_raw(score=60, reasoning="Mid"),
            _make_raw(score=80, reasoning="High"),
        ]
        merged = merge_photo_results([parse_llm_response(r) for r in results])
        assert merged["visual_quality_score"] == 60

    def test_median_score_even(self):
        results = [
            _make_raw(score=40, reasoning="Low"),
            _make_raw(score=60, reasoning="High"),
        ]
        merged = merge_photo_results([parse_llm_response(r) for r in results])
        assert merged["visual_quality_score"] == 50

    def test_features_merged(self):
        results = [
            _make_raw(features={"kitchen_features": ["granite"], "flooring": ["hardwood"]}),
            _make_raw(
                features={"kitchen_features": ["island", "granite"], "exterior_features": ["pool"]}
            ),
        ]
        merged = merge_photo_results([parse_llm_response(r) for r in results])
        assert set(merged["detected_features"]["kitchen_features"]) == {"granite", "island"}
        assert merged["detected_features"]["flooring"] == ["hardwood"]
        assert merged["detected_features"]["exterior_features"] == ["pool"]

    def test_most_common_renovation(self):
        results = [
            _make_raw(renovation="fully_renovated"),
            _make_raw(renovation="original_maintained"),
            _make_raw(renovation="fully_renovated"),
        ]
        merged = merge_photo_results([parse_llm_response(r) for r in results])
        assert merged["renovation_level"] == "fully_renovated"

    def test_all_none_scores(self):
        results = [_make_raw(score=None, reasoning=None, renovation=None)]
        # score=None with other fields present → parse_llm_response sets score=None
        merged = merge_photo_results([parse_llm_response(r) for r in results])
        assert merged["visual_quality_score"] is None


class TestScorePhotosBatch:
    def test_processes_all(self):
        async def mock_ollama(image, **kwargs):
            return _make_raw(score=60, reasoning="OK")

        def mock_s3(keys, **kwargs):
            return ["base64data"] * len(keys)

        listings = [
            {"id": 1, "property_photos": ["photos/a.jpg"]},
            {"id": 2, "property_photos": ["photos/b.jpg"]},
        ]
        results = asyncio.run(
            score_photos_batch(
                listings,
                "test-model",
                "abc123",
                ollama_fn=mock_ollama,
                s3_fn=mock_s3,
            )
        )
        assert len(results) == 2
        assert all(r["visual_quality_score"] == 60 for r in results)

    def test_multiple_photos_per_listing(self):
        """Each photo is scored individually and results are merged."""
        call_count = 0

        async def mock_ollama(image, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_raw(score=50 + call_count * 10, reasoning=f"Photo {call_count}")

        def mock_s3(keys, **kwargs):
            return ["base64data"] * len(keys)

        listings = [{"id": 1, "property_photos": ["photos/a.jpg", "photos/b.jpg"]}]
        results = asyncio.run(
            score_photos_batch(
                listings,
                "model",
                "v1",
                ollama_fn=mock_ollama,
                s3_fn=mock_s3,
            )
        )
        assert len(results) == 1
        assert call_count == 2
        # raw_response is a list of per-photo responses
        assert isinstance(results[0]["raw_response"], list)
        assert len(results[0]["raw_response"]) == 2

    def test_skips_unchanged_hash(self):
        async def mock_ollama(image, **kwargs):
            return _make_raw(score=70)

        def mock_s3(keys, **kwargs):
            return ["base64data"]

        listings = [{"id": 1, "property_photos": ["photos/a.jpg"]}]
        photos_hash = compute_photos_hash(["photos/a.jpg"])
        existing = {(1, "model", "v1"): photos_hash}

        results = asyncio.run(
            score_photos_batch(
                listings,
                "model",
                "v1",
                existing_hashes=existing,
                ollama_fn=mock_ollama,
                s3_fn=mock_s3,
            )
        )
        assert len(results) == 0

    def test_handles_failures_gracefully(self):
        async def mock_ollama(image, **kwargs):
            return None

        def mock_s3(keys, **kwargs):
            return ["base64data"]

        listings = [{"id": 1, "property_photos": ["photos/a.jpg"]}]
        results = asyncio.run(
            score_photos_batch(
                listings,
                "model",
                "v1",
                ollama_fn=mock_ollama,
                s3_fn=mock_s3,
            )
        )
        assert len(results) == 1
        assert results[0]["raw_response"] == {"error": "ollama_call_failed"}

    def test_skips_empty_photos(self):
        async def mock_ollama(image, **kwargs):
            return _make_raw()

        def mock_s3(keys, **kwargs):
            return ["base64data"]

        listings = [
            {"id": 1, "property_photos": []},
            {"id": 2, "property_photos": None},
        ]
        results = asyncio.run(
            score_photos_batch(
                listings,
                "model",
                "v1",
                ollama_fn=mock_ollama,
                s3_fn=mock_s3,
            )
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# TestScoreAllPhotos
# ---------------------------------------------------------------------------

_SCORER = "pricepoint.data.housing.photo_scorer"


class TestScoreAllPhotos:
    @patch(f"{_SCORER}.SessionLocal")
    @patch(f"{_SCORER}._get_model_version")
    def test_full_pipeline_mock(self, mock_version, mock_session_cls):
        mock_version.return_value = "abc123456789"

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock existing hashes query (empty)
        mock_session.execute.return_value.all.return_value = []

        async def mock_ollama(images, **kwargs):
            return _make_raw()

        def mock_s3(keys, **kwargs):
            return ["base64data"]

        result = score_all_photos(batch_size=10, ollama_fn=mock_ollama, s3_fn=mock_s3)
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

        result = score_all_photos(batch_size=10)
        assert result["scored"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @patch(f"{_SCORER}.SessionLocal")
    @patch(f"{_SCORER}._get_model_version")
    def test_skips_same_hash(self, mock_version, mock_session_cls):
        mock_version.return_value = "abc123456789"

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        photo_keys = ["photos/slug/photo_0.jpg", "photos/slug/photo_1.jpg"]
        photos_hash = compute_photos_hash(photo_keys)

        # Mock existing hashes with matching hash
        existing_row = MagicMock()
        existing_row.listing_id = 1
        existing_row.model_name = "llama3.2-vision:11b"
        existing_row.model_version = "abc123456789"
        existing_row.photos_hash = photos_hash

        # Mock listing
        listing_row = MagicMock()
        listing_row.id = 1
        listing_row.property_photos = photo_keys

        mock_session.execute.return_value.all.side_effect = [
            [existing_row],
            [listing_row],
        ]

        result = score_all_photos(batch_size=10)
        assert result["skipped"] == 1
        assert result["scored"] == 0
