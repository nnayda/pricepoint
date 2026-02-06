"""Tests for geocode schemas."""

import pytest
from pydantic import ValidationError

from pricepoint.api.schemas.geocode import GeocodeResponse, GeocodeResult


class TestGeocodeResult:
    def test_valid_result(self) -> None:
        result = GeocodeResult(
            display_name="123 Main St, Raleigh, NC",
            lat=35.7796,
            lon=-78.6382,
            place_id=12345,
            osm_type="way",
            osm_id=67890,
            boundingbox=[35.77, 35.78, -78.64, -78.63],
        )
        assert result.display_name == "123 Main St, Raleigh, NC"
        assert result.lat == 35.7796
        assert result.lon == -78.6382
        assert result.place_id == 12345
        assert result.osm_type == "way"
        assert result.osm_id == 67890
        assert result.boundingbox == [35.77, 35.78, -78.64, -78.63]

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            GeocodeResult(
                display_name="123 Main St",
                lat=35.7796,
                # lon missing
                place_id=12345,
                osm_type="way",
                osm_id=67890,
                boundingbox=[35.77, 35.78, -78.64, -78.63],
            )  # type: ignore[call-arg]

    def test_invalid_lat_type(self) -> None:
        with pytest.raises(ValidationError):
            GeocodeResult(
                display_name="123 Main St",
                lat="not_a_float",
                lon=-78.6382,
                place_id=12345,
                osm_type="way",
                osm_id=67890,
                boundingbox=[35.77, 35.78, -78.64, -78.63],
            )  # type: ignore[arg-type]

    def test_empty_boundingbox(self) -> None:
        result = GeocodeResult(
            display_name="123 Main St",
            lat=35.7796,
            lon=-78.6382,
            place_id=12345,
            osm_type="node",
            osm_id=67890,
            boundingbox=[],
        )
        assert result.boundingbox == []


class TestGeocodeResponse:
    def test_valid_response(self) -> None:
        response = GeocodeResponse(
            results=[
                GeocodeResult(
                    display_name="123 Main St, Raleigh, NC",
                    lat=35.7796,
                    lon=-78.6382,
                    place_id=12345,
                    osm_type="way",
                    osm_id=67890,
                    boundingbox=[35.77, 35.78, -78.64, -78.63],
                )
            ],
            cached=False,
        )
        assert len(response.results) == 1
        assert response.cached is False

    def test_empty_results(self) -> None:
        response = GeocodeResponse(results=[], cached=True)
        assert response.results == []
        assert response.cached is True

    def test_multiple_results(self) -> None:
        results = [
            GeocodeResult(
                display_name=f"Address {i}",
                lat=35.0 + i,
                lon=-78.0 + i,
                place_id=i,
                osm_type="way",
                osm_id=i * 10,
                boundingbox=[34.0, 36.0, -79.0, -77.0],
            )
            for i in range(3)
        ]
        response = GeocodeResponse(results=results, cached=False)
        assert len(response.results) == 3

    def test_missing_cached_field(self) -> None:
        with pytest.raises(ValidationError):
            GeocodeResponse(
                results=[],
            )  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        response = GeocodeResponse(
            results=[
                GeocodeResult(
                    display_name="123 Main St",
                    lat=35.7796,
                    lon=-78.6382,
                    place_id=12345,
                    osm_type="relation",
                    osm_id=67890,
                    boundingbox=[35.77, 35.78, -78.64, -78.63],
                )
            ],
            cached=True,
        )
        data = response.model_dump()
        restored = GeocodeResponse.model_validate(data)
        assert restored == response
