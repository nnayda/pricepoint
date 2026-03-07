"""Tests for Redfin listing HTML collector."""

import os
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from pricepoint.data.housing.known_fields import _to_snake_case, normalize_field_name
from pricepoint.data.housing.redfin_listings import (
    _archive_to_s3,
    _determine_agent_role,
    _extract_photos,
    _get_price_label,
    _is_hidden_entry,
    _parse_address,
    _parse_address_from_filename,
    _parse_agent_info,
    _parse_climate_risks,
    _parse_description,
    _parse_float,
    _parse_html_file,
    _parse_int,
    _parse_key_details,
    _parse_key_stats,
    _parse_listing_status,
    _parse_price,
    _parse_property_details,
    _parse_redfin_estimate,
    _parse_sale_history,
    _parse_schools,
    _parse_source_url,
    _parse_tax_history,
    _slugify_address,
    _upsert_listing,
    process_listings,
)

FIXTURES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "redfin")
)
SOLD_FIXTURE = os.path.join(FIXTURES_DIR, "sold_listing.html")
FOR_SALE_FIXTURE = os.path.join(FIXTURES_DIR, "for_sale_listing.html")


@pytest.fixture
def sold_soup():
    """BeautifulSoup of sold listing fixture."""
    with open(SOLD_FIXTURE, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "lxml")


@pytest.fixture
def for_sale_soup():
    """BeautifulSoup of for-sale listing fixture."""
    with open(FOR_SALE_FIXTURE, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "lxml")


# ---------------------------------------------------------------------------
# A. Helper function tests
# ---------------------------------------------------------------------------


class TestParsePrice:
    def test_valid_price(self):
        assert _parse_price("$721,000") == "$721,000"

    def test_price_with_extra_text(self):
        assert _parse_price("$721,000$247/sq ft") == "$721,000"

    def test_none_input(self):
        assert _parse_price(None) is None

    def test_empty_string(self):
        assert _parse_price("") is None

    def test_no_price_in_text(self):
        assert _parse_price("no price here") is None

    def test_dash(self):
        assert _parse_price("—") is None


class TestParseInt:
    def test_valid_int(self):
        assert _parse_int("4") == 4

    def test_int_with_commas(self):
        assert _parse_int("2,916") == 2916

    def test_none_input(self):
        assert _parse_int(None) is None

    def test_empty_string(self):
        assert _parse_int("") is None

    def test_invalid_string(self):
        assert _parse_int("abc") is None

    def test_float_string(self):
        # Should fail since "3.5" is not a valid int
        assert _parse_int("3.5") is None

    def test_whitespace(self):
        assert _parse_int("  42  ") == 42


class TestParseFloat:
    def test_valid_float(self):
        assert _parse_float("3.5") == 3.5

    def test_integer_string(self):
        assert _parse_float("4") == 4.0

    def test_with_commas(self):
        assert _parse_float("2,916") == 2916.0

    def test_none_input(self):
        assert _parse_float(None) is None

    def test_empty_string(self):
        assert _parse_float("") is None

    def test_invalid_string(self):
        assert _parse_float("abc") is None


class TestSlugifyAddress:
    def test_normal_address(self):
        result = _slugify_address("100 Fern Berry Ct, Apex, NC 27502")
        assert result == "100-fern-berry-ct-apex-nc-27502"

    def test_strips_special_chars(self):
        assert _slugify_address("123 Main St #4") == "123-main-st-4"

    def test_lowercase(self):
        assert _slugify_address("ABC DEF") == "abc-def"


# ---------------------------------------------------------------------------
# B. Parser function tests (using fixture HTML)
# ---------------------------------------------------------------------------


class TestParseAddressFromFilename:
    def test_standard_format(self):
        result = _parse_address_from_filename(
            "100 Fern Berry Ct, Apex, NC 27502 ｜ Redfin (1_26_2026 9：22：10 AM).html"
        )
        assert result["address"] == "100 Fern Berry Ct, Apex, NC 27502"
        assert result["city"] == "Apex"
        assert result["state"] == "NC"
        assert result["zip_code"] == "27502"

    def test_mls_format(self):
        fn = (
            "1010 Castalia Dr, Cary, NC 27513"
            " ｜ MLS# 10144851 ｜ Redfin (2_9_2026 2：48：40 PM).html"
        )
        result = _parse_address_from_filename(fn)
        assert result["address"] == "1010 Castalia Dr, Cary, NC 27513"
        assert result["city"] == "Cary"
        assert result["state"] == "NC"
        assert result["zip_code"] == "27513"

    def test_invalid_filename(self):
        result = _parse_address_from_filename("not_a_redfin_file.html")
        assert result["address"] is None

    def test_ascii_pipe(self):
        result = _parse_address_from_filename(
            "123 Main St, Town, ST 12345 | Redfin (1_1_2026).html"
        )
        assert result["address"] == "123 Main St, Town, ST 12345"


class TestParseAddress:
    def test_filename_preferred(self, sold_soup):
        result = _parse_address(
            sold_soup,
            "100 Fern Berry Ct, Apex, NC 27502 ｜ Redfin (1_26_2026 9：22：10 AM).html",
        )
        assert result["address"] == "100 Fern Berry Ct, Apex, NC 27502"

    def test_h1_fallback(self, sold_soup):
        result = _parse_address(sold_soup, "unknown_file.html")
        assert result["address"] == "100 Fern Berry Ct, Apex, NC 27502"
        assert result["city"] == "Apex"
        assert result["state"] == "NC"
        assert result["zip_code"] == "27502"


class TestParseListingStatus:
    def test_sold_with_price(self, sold_soup):
        result = _parse_listing_status(sold_soup)
        assert result["listing_status"] == "SOLD"
        assert result["sold_date"] == "JUN 2024"
        assert result["sold_price"] == "$721,000"

    def test_for_sale(self, for_sale_soup):
        result = _parse_listing_status(for_sale_soup)
        assert result["listing_status"] == "FOR SALE"
        assert result["sold_date"] is None
        assert result["sold_price"] is None

    def test_no_banner(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        result = _parse_listing_status(soup)
        assert result["listing_status"] is None


class TestParseKeyStats:
    def test_sold_listing(self, sold_soup):
        result = _parse_key_stats(sold_soup)
        assert result["listing_price"] == "$725,574"
        assert result["beds"] == 4
        assert result["baths"] == 3.5
        assert result["sqft"] == 2916

    def test_for_sale_listing(self, for_sale_soup):
        result = _parse_key_stats(for_sale_soup)
        assert result["listing_price"] == "$500,000"
        assert result["beds"] == 3
        assert result["baths"] == 2.5
        assert result["sqft"] == 2311

    def test_empty_html(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        result = _parse_key_stats(soup)
        assert result["listing_price"] is None
        assert result["beds"] is None
        assert result["baths"] is None
        assert result["sqft"] is None


class TestParseKeyDetails:
    def test_sold_listing(self, sold_soup):
        result = _parse_key_details(sold_soup)
        assert result["year_built"] == 2001
        assert result["lot_size"] == "0.25 acres"
        assert result["price_per_sqft"] == "$249"

    def test_for_sale_listing(self, for_sale_soup):
        result = _parse_key_details(for_sale_soup)
        assert result["year_built"] == 1998
        assert result["lot_size"] == "0.42 acres"
        assert result["price_per_sqft"] == "$216"

    def test_no_key_details(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        result = _parse_key_details(soup)
        assert result["year_built"] is None


class TestParseDescription:
    def test_sold_listing(self, sold_soup):
        desc = _parse_description(sold_soup)
        assert desc is not None
        assert "Victorian-style home" in desc

    def test_for_sale_listing(self, for_sale_soup):
        desc = _parse_description(for_sale_soup)
        assert desc is not None
        assert "Charming home" in desc

    def test_no_description(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_description(soup) is None


class TestParseAgentInfo:
    def test_sold_listing(self, sold_soup):
        result = _parse_agent_info(sold_soup)
        assert result["listing_agent"] == "Karen Coe"
        assert result["listing_brokerage"] == "Keller Williams Legacy"
        assert result["buying_agent"] == "Diana Chan Warren"
        assert result["buying_brokerage"] == "Cary-Raleigh Realty, Inc."

    def test_for_sale_listing(self, for_sale_soup):
        result = _parse_agent_info(for_sale_soup)
        assert result["listing_agent"] == "John Smith"
        assert result["listing_brokerage"] == "RE/MAX United"
        assert result["buying_agent"] is None

    def test_no_agent_section(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        result = _parse_agent_info(soup)
        assert result["listing_agent"] is None

    def test_semantic_heading_without_prefix(self):
        """Agent name directly in heading (Redfin-listed, no 'Listed by' prefix)."""
        html = """
        <div class="agent-info-section">
          <div class="redfin-agent">
            <div class="agent-info-item">
              <span class="agent-basic-details--heading">Jane Doe</span>
              <span class="agent-basic-details--broker">• Redfin Corp</span>
            </div>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        result = _parse_agent_info(soup)
        assert result["listing_agent"] == "Jane Doe"
        assert result["listing_brokerage"] == "Redfin Corp"

    def test_legacy_pipe_delimited_fallback(self):
        """Pipe-delimited text (no semantic elements) still works."""
        html = """
        <div class="agent-info-section">
          <div class="agent-info-item">Listed by | Alice Jones | • | Best Realty</div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        result = _parse_agent_info(soup)
        assert result["listing_agent"] == "Alice Jones"
        assert result["listing_brokerage"] == "Best Realty"


class TestGetPriceLabel:
    def test_sold_fixture_label(self, sold_soup):
        label = _get_price_label(sold_soup)
        assert label == "Sold Price"

    def test_for_sale_fixture_label(self, for_sale_soup):
        label = _get_price_label(for_sale_soup)
        assert label == "Est. mortgage"

    def test_no_price_section(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _get_price_label(soup) is None


class TestDetermineAgentRole:
    def test_listed_by_prefix(self):
        html = '<div class="agent-info-item"><span>Listed by Agent</span></div>'
        soup = BeautifulSoup(html, "lxml")
        item = soup.find(class_="agent-info-item")
        assert _determine_agent_role("Listed by Agent", item) == "listing"

    def test_bought_with_prefix(self):
        html = '<div class="agent-info-item"><span>Bought with Agent</span></div>'
        soup = BeautifulSoup(html, "lxml")
        item = soup.find(class_="agent-info-item")
        assert _determine_agent_role("Bought with Agent", item) == "buying"

    def test_ancestor_redfin_agent(self):
        html = """
        <div class="agent-info-section">
          <div class="redfin-agent">
            <div class="agent-info-item"><span>Agent Name</span></div>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        item = soup.find(class_="agent-info-item")
        assert _determine_agent_role("Agent Name", item) == "listing"

    def test_ancestor_buyer_agent(self):
        html = """
        <div class="agent-info-section">
          <div class="buyer-agent-item">
            <div class="agent-info-item"><span>Buyer Agent</span></div>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        item = soup.find(class_="agent-info-item")
        assert _determine_agent_role("Buyer Agent", item) == "buying"

    def test_unknown_role(self):
        html = (
            '<div class="agent-info-section">'
            '<div class="agent-info-item"><span>Unknown</span></div>'
            "</div>"
        )
        soup = BeautifulSoup(html, "lxml")
        item = soup.find(class_="agent-info-item")
        assert _determine_agent_role("Unknown", item) is None


class TestSoldPricePostProcessing:
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_sold_listing_moves_price_to_sold_price(self, mock_settings, mock_extract_photos):
        """Sold listing with 'Sold Price' label → sold_price set, listing_price None."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)

        data, _ = _parse_html_file(
            SOLD_FIXTURE,
            "100 Fern Berry Ct, Apex, NC 27502 ｜ Redfin (1_26_2026).html",
        )

        # The sold fixture has "Sold Price" as statsLabel and "SOLD ... FOR $721,000"
        # in the banner. The banner already sets sold_price=$721,000 so the
        # statsValue should NOT overwrite it. listing_price must be None.
        assert data["sold_price"] == "$721,000"
        assert data["listing_price"] is None

    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_sold_no_banner_price_uses_stats_value(self, mock_settings, mock_extract_photos):
        """Sold listing where banner has no price but statsLabel says 'Sold Price'."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)
        html = """<!DOCTYPE html><html><body>
        <div class="ListingStatusBannerSection">SOLD ON AUG 12, 2025</div>
        <div class="stat-block price-section">
          <div class="statsValue"><span>$1,440,000</span></div>
          <span class="statsLabel">Sold Price</span>
        </div>
        </body></html>"""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            data, _ = _parse_html_file(f.name, "test.html")
            os.unlink(f.name)

        assert data["sold_price"] == "$1,440,000"
        assert data["listing_price"] is None

    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_sold_estimate_label_clears_listing_price(self, mock_settings, mock_extract_photos):
        """Sold listing where statsValue is Redfin estimate → listing_price None."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)
        html = """<!DOCTYPE html><html><body>
        <div class="ListingStatusBannerSection">SOLD APR 2022 FOR $675,000</div>
        <div class="stat-block price-section">
          <div class="statsValue"><span>$732,378</span></div>
          <span class="statsLabel">Redfin Estimate</span>
        </div>
        </body></html>"""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            data, _ = _parse_html_file(f.name, "test.html")
            os.unlink(f.name)

        assert data["sold_price"] == "$675,000"
        assert data["listing_price"] is None

    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_for_sale_listing_keeps_listing_price(self, mock_settings, mock_extract_photos):
        """For-sale listings should keep listing_price unchanged."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)

        data, _ = _parse_html_file(
            FOR_SALE_FIXTURE,
            "1010 Castalia Dr, Cary, NC 27513 ｜ Redfin (2_9_2026).html",
        )

        assert data["listing_price"] == "$500,000"
        assert data["sold_price"] is None


class TestParseRedfinEstimate:
    def test_sold_listing(self, sold_soup):
        estimate = _parse_redfin_estimate(sold_soup)
        assert estimate == "$725,574"

    def test_for_sale_listing(self, for_sale_soup):
        estimate = _parse_redfin_estimate(for_sale_soup)
        assert estimate == "$510,000"

    def test_no_estimate(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_redfin_estimate(soup) is None


class TestParseSaleHistory:
    def test_sold_listing(self, sold_soup):
        history = _parse_sale_history(sold_soup)
        assert len(history) == 3
        assert history[0]["date"] == "Jun 14, 2024"
        assert history[0]["event"] == "Sold"
        assert history[0]["price"] == "$721,000"
        assert history[2]["event"] == "Listed"
        assert history[2]["price"] == "$699,999"

    def test_for_sale_listing(self, for_sale_soup):
        history = _parse_sale_history(for_sale_soup)
        assert len(history) == 1
        assert history[0]["event"] == "Listed"
        assert history[0]["price"] == "$500,000"

    def test_no_history(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_sale_history(soup) == []


class TestParseTaxHistory:
    def test_sold_listing(self, sold_soup):
        history = _parse_tax_history(sold_soup)
        assert len(history) == 2
        assert history[0]["year"] == "2025"
        assert history[0]["tax"] == "$5,586(+2.3%)"
        assert history[0]["land"] == "$189,000"
        assert history[0]["assessed_value"] == "$637,513"

    def test_for_sale_listing(self, for_sale_soup):
        history = _parse_tax_history(for_sale_soup)
        assert len(history) == 1
        assert history[0]["year"] == "2025"

    def test_no_history(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_tax_history(soup) == []


class TestParsePropertyDetails:
    def test_sold_listing(self, sold_soup):
        details = _parse_property_details(sold_soup)
        assert details is not None
        assert details["bathrooms_full"] == "3"
        assert details["bathrooms_half"] == "1"
        assert details["attached_garage"] == "Yes"
        assert details["garage_spaces"] == "2"
        assert details["heating"] == "Forced Air"
        assert details["cooling"] == "Central Air"
        assert details["flooring"] == "Hardwood, Tile"
        assert details["appliances"] == "Dishwasher, Microwave"
        assert details["roof"] == "Asphalt Shingle"
        assert details["fencing"] == "Wood"
        assert details["hoa_dues"] == "$150/month"

    def test_boolean_feature(self, sold_soup):
        details = _parse_property_details(sold_soup)
        assert details is not None
        assert details["has_basement"] is True

    def test_hidden_field_excluded(self, sold_soup):
        details = _parse_property_details(sold_soup)
        assert details is not None
        # Items in the <ul> containing "hidden custom fields" are excluded
        assert "somehiddenthing" not in details

    def test_comma_single_item_excluded(self, sold_soup):
        details = _parse_property_details(sold_soup)
        assert details is not None
        # "Dishwasher, Microwave, Oven" (comma-containing single item) is excluded
        keys = list(details.keys())
        assert not any("dishwasher" in k and "oven" in k for k in keys)

    def test_for_sale_listing(self, for_sale_soup):
        details = _parse_property_details(for_sale_soup)
        assert details is not None
        assert details["granite_countertops"] == "Yes"
        assert details["appliances"] == "Dishwasher, Microwave"
        assert details["pool_features"] == "In-Ground"
        assert details["crawl_space"] is True

    def test_no_details(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_property_details(soup) is None

    def test_empty_container(self):
        soup = BeautifulSoup(
            '<html><body><div id="propertyDetails-preview"></div></body></html>',
            "lxml",
        )
        assert _parse_property_details(soup) is None


class TestIsHiddenEntry:
    def test_normal_item(self):
        html = '<ul><li class="entryItem">Heating: Gas</li></ul>'
        soup = BeautifulSoup(html, "lxml")
        item = soup.find("li", class_="entryItem")
        assert _is_hidden_entry(item) is False

    def test_hidden_custom_fields_sibling(self):
        html = """<ul>
            <li>hidden custom fields</li>
            <li class="entryItem">SomeHiddenThing</li>
        </ul>"""
        soup = BeautifulSoup(html, "lxml")
        item = soup.find("li", class_="entryItem")
        assert _is_hidden_entry(item) is True

    def test_no_parent(self):
        """Edge case: item with no parent returns False."""
        from bs4 import Tag

        item = Tag(name="li")
        item.string = "Orphan"
        assert _is_hidden_entry(item) is False


class TestNormalizeFieldName:
    def test_known_field(self):
        assert normalize_field_name("Bathrooms Full") == "bathrooms_full"

    def test_known_field_with_hash(self):
        assert normalize_field_name("# of Full Baths") == "num_of_full_baths"

    def test_trailing_space(self):
        assert normalize_field_name("Lot Size ") == "lot_size"

    def test_unknown_field_fallback(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            result = normalize_field_name("Brand New Field XYZ")
        assert result == "brand_new_field_xyz"
        assert "Unknown property detail field" in caplog.text

    def test_to_snake_case_hash(self):
        assert _to_snake_case("# of Full Baths") == "num_of_full_baths"

    def test_to_snake_case_special_chars(self):
        assert _to_snake_case("Garage/Parking Sq. Ft") == "garage_parking_sq_ft"

    def test_to_snake_case_trailing_space(self):
        assert _to_snake_case("Lot Size ") == "lot_size"


class TestParseSchools:
    def test_sold_listing(self, sold_soup):
        schools = _parse_schools(sold_soup)
        assert len(schools) == 2
        assert schools[0]["rating"] == "7"
        assert schools[0]["name"] == "Scotts Ridge Elementary"
        assert "PreK-5" in schools[0]["description"]
        assert schools[1]["rating"] == "10"
        assert schools[1]["name"] == "Apex Middle"

    def test_for_sale_listing(self, for_sale_soup):
        schools = _parse_schools(for_sale_soup)
        assert len(schools) == 1
        assert schools[0]["rating"] == "8"
        assert schools[0]["name"] == "Cary Elementary"

    def test_no_schools(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert _parse_schools(soup) == []


class TestParseClimateRisks:
    def test_sold_listing(self, sold_soup):
        result = _parse_climate_risks(sold_soup)
        assert result["climate_flood_factor"] == "Major"
        assert result["climate_fire_factor"] == "Minimal"

    def test_for_sale_listing(self, for_sale_soup):
        result = _parse_climate_risks(for_sale_soup)
        assert result["climate_flood_factor"] == "Minor"
        assert result["climate_fire_factor"] == "Moderate"

    def test_no_climate(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        result = _parse_climate_risks(soup)
        assert result["climate_flood_factor"] is None
        assert result["climate_fire_factor"] is None


# ---------------------------------------------------------------------------
# C. Photo extraction tests
# ---------------------------------------------------------------------------


class TestExtractPhotos:
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_extracts_base64_photos(self, mock_settings, sold_soup):
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()

        paths, failed = _extract_photos(sold_soup, "test-slug", s3_client=mock_s3)

        # Fixture has 2 base64 images (png + jpeg), 1 non-base64 img
        assert len(paths) == 2
        assert failed == 0
        assert "redfin/photos/test-slug/photo_0.png" in paths[0]
        assert mock_s3.put_object.call_count == 2

    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_empty_container(self, mock_settings):
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="test-bucket",
        )
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        paths, failed = _extract_photos(soup, "test-slug", s3_client=MagicMock())
        assert paths == []
        assert failed == 0

    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_s3_upload_failure_reports_count(self, mock_settings, sold_soup):
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 error")

        paths, failed = _extract_photos(sold_soup, "test-slug", s3_client=mock_s3)

        # Should return empty list since all uploads failed, with failure count
        assert paths == []
        assert failed == 2


# ---------------------------------------------------------------------------
# D. Upsert logic tests
# ---------------------------------------------------------------------------


class TestUpsertListing:
    def test_insert_new_record(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None

        data = {
            "address": "100 Fern Berry Ct, Apex, NC 27502",
            "listing_price": "$725,574",
            "beds": 4,
        }
        _upsert_listing(session, data)

        session.add.assert_called_once()

    def test_update_existing_record(self):
        existing = MagicMock()
        existing.address = "100 Fern Berry Ct, Apex, NC 27502"
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = existing

        data = {
            "address": "100 Fern Berry Ct, Apex, NC 27502",
            "listing_price": "$730,000",
            "beds": 4,
        }
        _upsert_listing(session, data)

        session.add.assert_not_called()

    def test_skip_no_address(self):
        session = MagicMock()
        data = {"listing_price": "$500,000"}
        _upsert_listing(session, data)
        session.query.assert_not_called()
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# E. End-to-end process_listings tests
# ---------------------------------------------------------------------------


class TestProcessListings:
    @patch("pricepoint.data.housing.redfin_listings._archive_to_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_single_file_mode(
        self, mock_settings, mock_session_cls, mock_extract_photos, mock_archive
    ):
        mock_settings.return_value = MagicMock(
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
            s3_bucket="bucket",
            redfin_s3_photos_prefix="redfin/photos",
        )
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_cls.return_value = mock_session
        mock_extract_photos.return_value = ([], 0)

        result = process_listings(file_path=SOLD_FIXTURE)

        assert result["processed"] == 1
        assert result["errors"] == 0
        mock_session.commit.assert_called_once()
        mock_archive.assert_called_once()

    @patch("pricepoint.data.housing.redfin_listings._archive_to_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_photo_failures_skip_archive(
        self, mock_settings, mock_session_cls, mock_extract_photos, mock_archive
    ):
        """When photo uploads fail, file should NOT be archived/deleted."""
        mock_settings.return_value = MagicMock(
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
            s3_bucket="bucket",
            redfin_s3_photos_prefix="redfin/photos",
        )
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_cls.return_value = mock_session
        mock_extract_photos.return_value = (["redfin/photos/slug/photo_0.png"], 2)

        result = process_listings(file_path=SOLD_FIXTURE)

        assert result["processed"] == 1
        assert result["errors"] == 0
        mock_session.commit.assert_called_once()
        mock_archive.assert_not_called()

    @patch("pricepoint.data.housing.redfin_listings._archive_to_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_directory_mode(
        self, mock_settings, mock_session_cls, mock_extract_photos, mock_archive
    ):
        mock_settings.return_value = MagicMock(
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
            s3_bucket="bucket",
            redfin_s3_photos_prefix="redfin/photos",
        )
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_cls.return_value = mock_session
        mock_extract_photos.return_value = ([], 0)

        result = process_listings(directory=FIXTURES_DIR)

        assert result["processed"] == 2
        assert result["errors"] == 0

    @patch("pricepoint.data.housing.redfin_listings._archive_to_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_no_files_found(
        self, mock_settings, mock_session_cls, mock_extract_photos, mock_archive
    ):
        mock_settings.return_value = MagicMock(
            redfin_html_dir="/nonexistent/dir",
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
        )

        result = process_listings(directory="/nonexistent/dir")

        assert result["processed"] == 0
        assert result["errors"] == 0

    @patch("pricepoint.data.housing.redfin_listings._archive_to_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_continue_on_error(
        self, mock_settings, mock_session_cls, mock_extract_photos, mock_archive
    ):
        mock_settings.return_value = MagicMock(
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
            s3_bucket="bucket",
            redfin_s3_photos_prefix="redfin/photos",
        )
        mock_session = MagicMock()
        # First call succeeds, second call fails
        mock_session.commit.side_effect = [None, Exception("DB error")]
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_cls.return_value = mock_session
        mock_extract_photos.return_value = ([], 0)

        result = process_listings(directory=FIXTURES_DIR)

        assert result["processed"] == 1
        assert result["errors"] == 1
        mock_session.rollback.assert_called_once()

    @patch("pricepoint.data.housing.redfin_listings._download_from_s3")
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.SessionLocal")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    def test_reprocess_s3_mode(
        self,
        mock_get_s3,
        mock_settings,
        mock_session_cls,
        mock_extract_photos,
        mock_download,
    ):
        import shutil
        import tempfile

        mock_settings.return_value = MagicMock(
            s3_endpoint_url="http://localhost:9000",
            s3_access_key="key",
            s3_secret_key="secret",
            s3_bucket="bucket",
            redfin_s3_archive_prefix="redfin/archive",
            redfin_s3_photos_prefix="redfin/photos",
        )
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_cls.return_value = mock_session
        mock_extract_photos.return_value = ([], 0)

        # Copy fixture to a temp file so process_listings can safely delete it
        # (reprocess mode marks files as is_temp=True and removes them after processing)
        fd, tmp_path = tempfile.mkstemp(suffix=".html")
        os.close(fd)
        shutil.copy2(SOLD_FIXTURE, tmp_path)

        # Mock S3 client paginator
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "redfin/archive/sold_listing.html"},
                ]
            }
        ]
        mock_download.return_value = tmp_path

        result = process_listings(reprocess_s3_prefix="redfin/archive")

        assert result["processed"] == 1
        assert result["errors"] == 0


# ---------------------------------------------------------------------------
# F. Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_corrupt_html(self, mock_settings, mock_extract_photos):
        """Parsing corrupt HTML should not raise (BS4 is lenient)."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write("<html><body>not a valid redfin page</body></html>")
            f.flush()
            data, photo_failures = _parse_html_file(f.name, "corrupt.html")
            os.unlink(f.name)

        # Should return data dict with None values
        assert data["address"] is None
        assert photo_failures == 0
        assert data["listing_status"] is None

    def test_missing_sections_return_none(self):
        """All parser functions should handle missing sections gracefully."""
        soup = BeautifulSoup("<html><body></body></html>", "lxml")

        assert _parse_listing_status(soup)["listing_status"] is None
        assert _parse_key_stats(soup)["listing_price"] is None
        assert _parse_key_details(soup)["year_built"] is None
        assert _parse_description(soup) is None
        assert _parse_agent_info(soup)["listing_agent"] is None
        assert _parse_redfin_estimate(soup) is None
        assert _parse_sale_history(soup) == []
        assert _parse_tax_history(soup) == []
        assert _parse_property_details(soup) is None
        assert _parse_schools(soup) == []
        assert _parse_climate_risks(soup)["climate_flood_factor"] is None

    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_invalid_base64_skipped(self, mock_settings):
        """Invalid base64 data should be skipped without error."""
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        html = """
        <html><body>
        <div class="InlinePhotoPreviewRedesign">
          <img src="data:image/png;base64,NOT_VALID_BASE64!!!" alt="bad">
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        mock_s3 = MagicMock()

        paths, failed = _extract_photos(soup, "test", s3_client=mock_s3)

        assert paths == []
        assert failed == 1
        mock_s3.put_object.assert_not_called()


# ---------------------------------------------------------------------------
# G. Archive to S3 tests
# ---------------------------------------------------------------------------


class TestArchiveToS3:
    @patch("pricepoint.data.housing.redfin_listings.os.path.exists", return_value=True)
    @patch("pricepoint.data.housing.redfin_listings.os.remove")
    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_archive_uploads_verifies_and_deletes(
        self, mock_settings, mock_get_s3, mock_remove, _mock_exists
    ):
        mock_settings.return_value = MagicMock(
            redfin_s3_archive_prefix="redfin/archive",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3

        result = _archive_to_s3("/tmp/test.html", "test.html")

        assert result is True
        mock_s3.upload_file.assert_called_once_with(
            "/tmp/test.html", "test-bucket", "redfin/archive/test.html"
        )
        mock_s3.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="redfin/archive/test.html"
        )
        mock_remove.assert_called_once_with("/tmp/test.html")

    @patch("pricepoint.data.housing.redfin_listings.os.path.exists", return_value=True)
    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_archive_keeps_file_on_s3_error(self, mock_settings, mock_get_s3, _mock_exists):
        mock_settings.return_value = MagicMock(
            redfin_s3_archive_prefix="redfin/archive",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = Exception("S3 error")
        mock_get_s3.return_value = mock_s3

        result = _archive_to_s3("/tmp/test.html", "test.html")

        assert result is False

    @patch("pricepoint.data.housing.redfin_listings.os.path.exists", return_value=True)
    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_archive_keeps_file_on_verify_failure(self, mock_settings, mock_get_s3, _mock_exists):
        """If head_object fails after upload, do not delete local file."""
        mock_settings.return_value = MagicMock(
            redfin_s3_archive_prefix="redfin/archive",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_s3.head_object.side_effect = Exception("Verify failed")
        mock_get_s3.return_value = mock_s3

        result = _archive_to_s3("/tmp/test.html", "test.html")

        assert result is False

    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_missing_file_confirmed_in_s3(self, mock_settings, mock_get_s3):
        """File gone locally but confirmed in S3 — returns True."""
        mock_settings.return_value = MagicMock(
            redfin_s3_archive_prefix="redfin/archive",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3

        result = _archive_to_s3("/tmp/nonexistent.html", "nonexistent.html")

        assert result is True
        mock_s3.head_object.assert_called_once()

    @patch("pricepoint.data.housing.redfin_listings._get_s3_client")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_missing_file_not_in_s3_returns_false(self, mock_settings, mock_get_s3):
        """File gone locally and not in S3 — data loss, returns False."""
        mock_settings.return_value = MagicMock(
            redfin_s3_archive_prefix="redfin/archive",
            s3_bucket="test-bucket",
        )
        mock_s3 = MagicMock()
        mock_s3.head_object.side_effect = Exception("Not found")
        mock_get_s3.return_value = mock_s3

        result = _archive_to_s3("/tmp/nonexistent.html", "nonexistent.html")

        assert result is False


# ---------------------------------------------------------------------------
# H. Full parse integration test
# ---------------------------------------------------------------------------


class TestParseHtmlFile:
    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_parse_sold_fixture(self, mock_settings, mock_extract_photos):
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = (["redfin/photos/test/photo_0.png"], 0)

        data, photo_failures = _parse_html_file(
            SOLD_FIXTURE,
            "100 Fern Berry Ct, Apex, NC 27502 ｜ Redfin (1_26_2026).html",
        )

        assert photo_failures == 0
        assert data["address"] == "100 Fern Berry Ct, Apex, NC 27502"
        assert data["city"] == "Apex"
        assert data["state"] == "NC"
        assert data["zip_code"] == "27502"
        assert data["listing_status"] == "SOLD"
        assert data["sold_price"] == "$721,000"
        assert data["listing_price"] is None
        assert data["beds"] == 4
        assert data["baths"] == 3.5
        assert data["sqft"] == 2916
        assert data["year_built"] == 2001
        assert data["lot_size"] == "0.25 acres"
        assert data["redfin_estimate"] == "$725,574"
        assert len(data["sale_history"]) == 3
        assert len(data["tax_history"]) == 2
        assert data["property_details"] is not None
        assert len(data["schools"]) == 2
        assert data["climate_flood_factor"] == "Major"
        assert data["climate_fire_factor"] == "Minimal"
        assert data["description"] is not None

    @patch("pricepoint.data.housing.redfin_listings._extract_photos")
    @patch("pricepoint.data.housing.redfin_listings.get_settings")
    def test_parse_for_sale_fixture(self, mock_settings, mock_extract_photos):
        mock_settings.return_value = MagicMock(
            redfin_s3_photos_prefix="redfin/photos",
            s3_bucket="bucket",
        )
        mock_extract_photos.return_value = ([], 0)

        data, photo_failures = _parse_html_file(
            FOR_SALE_FIXTURE,
            "1010 Castalia Dr, Cary, NC 27513 ｜ MLS# 10144851 ｜ Redfin (2_9_2026).html",
        )

        assert photo_failures == 0
        assert data["address"] == "1010 Castalia Dr, Cary, NC 27513"
        assert data["listing_status"] == "FOR SALE"
        assert data["listing_price"] == "$500,000"
        assert data["beds"] == 3
        assert data["baths"] == 2.5
        assert data["sqft"] == 2311
        assert data["year_built"] == 1998
        assert data["listing_agent"] == "John Smith"
        assert data["redfin_estimate"] == "$510,000"


# ---------------------------------------------------------------------------
# _parse_source_url tests
# ---------------------------------------------------------------------------


class TestParseSourceUrl:
    """Tests for _parse_source_url."""

    def test_canonical_link(self):
        html = '<html><head><link rel="canonical" href="https://www.redfin.com/NC/Apex/100/home/123"></head><body></body></html>'
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) == "https://www.redfin.com/NC/Apex/100/home/123"

    def test_og_url_fallback(self):
        html = '<html><head><meta property="og:url" content="https://www.redfin.com/NC/Cary/200/home/456"></head><body></body></html>'
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) == "https://www.redfin.com/NC/Cary/200/home/456"

    def test_canonical_preferred_over_og(self):
        html = (
            "<html><head>"
            '<link rel="canonical" href="https://www.redfin.com/canonical">'
            '<meta property="og:url" content="https://www.redfin.com/og">'
            "</head><body></body></html>"
        )
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) == "https://www.redfin.com/canonical"

    def test_singlefile_comment_saved_from(self):
        url = "https://www.redfin.com/NC/Apex/100/home/789"
        html = f"<!-- saved from url=(0070){url} --><html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) == url

    def test_singlefile_comment_url_colon(self):
        url = "https://www.redfin.com/NC/Cary/300/home/101"
        comment = f"<!-- Page saved with SingleFile url: {url} -->"
        html = f"{comment}<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) == url

    def test_no_url_returns_none(self):
        html = "<html><head><title>No URL</title></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _parse_source_url(soup) is None

    def test_sold_fixture_has_url(self, sold_soup):
        url = _parse_source_url(sold_soup)
        assert url == "https://www.redfin.com/NC/Apex/100-Fern-Berry-Ct-27502/home/123456"
