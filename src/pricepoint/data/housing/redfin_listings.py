"""Collect Redfin listing data from SingleFile HTML snapshots.

Parses self-contained HTML files saved via browser "Save As" / SingleFile extension.
Extracts structured listing data, uploads photos to S3, archives processed HTML,
and upserts results into staging_redfin_listings table.

Two filename formats are supported:
  - {Address} ｜ Redfin ({date}).html
  - {Address} ｜ MLS# {id} ｜ Redfin ({date}).html
"""

from __future__ import annotations

import base64
import glob
import logging
import os
import re
import tempfile
from datetime import date
from typing import Any

import boto3
from bs4 import BeautifulSoup, Tag

from pricepoint.config.settings import get_settings
from pricepoint.data.housing.known_fields import normalize_field_name
from pricepoint.db import SessionLocal
from pricepoint.db.models import StagingRedfinListing

logger = logging.getLogger(__name__)

# Regex for extracting address from filename (both formats)
# Handles fullwidth ｜ (U+FF5C) and fullwidth ： (U+FF1A) used by SingleFile
_FILENAME_RE = re.compile(r"^(.+?)\s*[｜|]\s*(?:MLS#\s*\S+\s*[｜|]\s*)?Redfin\s*\(([^)]*)\)\.html$")


def _parse_extraction_date(raw: str | None) -> date | None:
    """Parse extraction date from filename parenthetical, e.g. ``1_26_2026 9：22：10 AM``.

    Only the ``M_D_YYYY`` portion is used; the optional time suffix is ignored.
    Returns ``None`` on any parse failure.
    """
    if not raw:
        return None
    # Take only the date part (before the first space, if any)
    date_part = raw.strip().split()[0]
    parts = date_part.split("_")
    if len(parts) != 3:
        return None
    try:
        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None


def _parse_filename_date(filename: str) -> date | None:
    """Extract the extraction date from a Redfin HTML filename."""
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    return _parse_extraction_date(m.group(2))


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_price(text: str | None) -> str | None:
    """Extract price string, preserving $ and commas."""
    if not text:
        return None
    text = text.strip()
    # Match price pattern like $721,000 or $699,999
    m = re.search(r"\$[\d,]+", text)
    return m.group(0) if m else None


def _parse_int(text: str | None) -> int | None:
    """Parse integer from text, stripping commas."""
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        return int(text)
    except (ValueError, TypeError):
        return None


def _parse_float(text: str | None) -> float | None:
    """Parse float from text, stripping commas."""
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _slugify_address(address: str) -> str:
    """Convert address to URL-safe slug for S3 paths."""
    slug = address.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _get_s3_client():
    """Create boto3 S3 client from application settings."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


# ---------------------------------------------------------------------------
# Parser functions — each takes a BeautifulSoup and returns extracted data
# ---------------------------------------------------------------------------


def _parse_address_from_filename(filename: str) -> dict[str, str | None]:
    """Extract address components from the HTML filename.

    More reliable than DOM parsing since Redfin filenames always contain
    the full address.
    """
    m = _FILENAME_RE.match(filename)
    if not m:
        return {"address": None, "city": None, "state": None, "zip_code": None}

    full_address = m.group(1).strip()
    result: dict[str, str | None] = {
        "address": full_address,
        "city": None,
        "state": None,
        "zip_code": None,
    }

    # Try to parse "123 Main St, City, ST 12345"
    parts = [p.strip() for p in full_address.split(",")]
    if len(parts) >= 3:
        result["city"] = parts[-2].strip()
        # Last part: "NC 27502"
        state_zip = parts[-1].strip().split()
        if len(state_zip) >= 2:
            result["state"] = state_zip[0]
            result["zip_code"] = state_zip[1]
        elif len(state_zip) == 1:
            result["state"] = state_zip[0]
    elif len(parts) == 2:
        state_zip = parts[-1].strip().split()
        if len(state_zip) >= 2:
            result["state"] = state_zip[0]
            result["zip_code"] = state_zip[1]

    return result


def _parse_address(soup: BeautifulSoup, filename: str) -> dict[str, str | None]:
    """Parse address from filename with h1 fallback."""
    result = _parse_address_from_filename(filename)
    if result["address"]:
        return result

    # Fallback: parse from DOM h1
    h1 = soup.find("h1", class_="full-address")
    if h1:
        full_address = h1.get_text(strip=True)
        result["address"] = full_address
        parts = [p.strip() for p in full_address.split(",")]
        if len(parts) >= 3:
            result["city"] = parts[-2].strip()
            state_zip = parts[-1].strip().split()
            if len(state_zip) >= 2:
                result["state"] = state_zip[0]
                result["zip_code"] = state_zip[1]

    return result


def _parse_listing_status(soup: BeautifulSoup) -> dict[str, str | None]:
    """Parse listing status from the status banner section.

    Returns listing_status, sold_date, sold_price.
    """
    result: dict[str, str | None] = {
        "listing_status": None,
        "sold_date": None,
        "sold_price": None,
    }
    banner = soup.find("div", class_="ListingStatusBannerSection")
    if not banner:
        return result

    text = banner.get_text(" ", strip=True)

    # Check for sold pattern: "OFF MARKET— SOLD JUN 2024 FOR $721,000"
    # or "SOLD NOV 10, 2025"
    sold_match = re.search(
        r"SOLD\s+(.+?)(?:\s+FOR\s+(\$[\d,]+))?$",
        text,
        re.IGNORECASE,
    )
    if sold_match:
        result["listing_status"] = "SOLD"
        result["sold_date"] = sold_match.group(1).strip()
        result["sold_price"] = sold_match.group(2)
        return result

    if re.search(r"OFF\s*MARKET", text, re.IGNORECASE):
        result["listing_status"] = "OFF MARKET"
    elif re.search(r"FOR\s+SALE", text, re.IGNORECASE):
        result["listing_status"] = "FOR SALE"
    elif re.search(r"PENDING", text, re.IGNORECASE):
        result["listing_status"] = "PENDING"
    else:
        # Store raw text as status
        result["listing_status"] = text[:100] if text else None

    return result


def _parse_key_stats(soup: BeautifulSoup) -> dict[str, str | int | float | None]:
    """Parse price, beds, baths, sqft from stat-block sections."""
    result: dict[str, str | int | float | None] = {
        "listing_price": None,
        "beds": None,
        "baths": None,
        "sqft": None,
    }

    def _match_stat(name: str):
        return lambda c: c and name in c and "stat-block" in c

    # Price
    price_block = soup.find("div", class_=_match_stat("price-section"))
    if price_block:
        val = price_block.find(class_="statsValue")
        if val:
            result["listing_price"] = _parse_price(val.get_text(strip=True))

    # Beds — has statsValue div with number
    beds_block = soup.find("div", class_=_match_stat("beds-section"))
    if beds_block:
        val = beds_block.find(class_="statsValue")
        if val:
            result["beds"] = _parse_int(val.get_text(strip=True))
        else:
            # Sometimes beds value is in the label text
            label = beds_block.find(class_="statsLabel")
            if label:
                m = re.search(r"(\d+)", label.get_text(strip=True))
                if m:
                    result["beds"] = int(m.group(1))

    # Baths — value is inside statsLabel (e.g. "3.5 ba")
    baths_block = soup.find("div", class_=_match_stat("baths-section"))
    if baths_block:
        # Try statsValue first
        val = baths_block.find(class_="statsValue")
        if val:
            result["baths"] = _parse_float(val.get_text(strip=True))
        else:
            # Baths value is in the label: "3.5 ba"
            label = baths_block.find(class_="statsLabel")
            if label:
                m = re.search(r"([\d.]+)", label.get_text(strip=True))
                if m:
                    result["baths"] = _parse_float(m.group(1))

    # Sqft
    sqft_block = soup.find("div", class_=_match_stat("sqft-section"))
    if sqft_block:
        val = sqft_block.find(class_="statsValue")
        if val:
            result["sqft"] = _parse_int(val.get_text(strip=True))

    return result


def _parse_key_details(soup: BeautifulSoup) -> dict[str, str | int | None]:
    """Parse year built, lot size, price per sqft from KeyDetailsV2."""
    result: dict[str, str | int | None] = {
        "year_built": None,
        "lot_size": None,
        "price_per_sqft": None,
    }
    kd = soup.find("div", class_="KeyDetailsV2")
    if not kd:
        return result

    rows = kd.find_all(class_="keyDetails-row")
    for row in rows:
        value_span = row.find(class_="valueText")
        type_span = row.find(class_="valueType")
        if not value_span or not type_span:
            continue

        value_text = value_span.get_text(strip=True)
        type_text = type_span.get_text(strip=True).lower()

        if "year built" in type_text:
            result["year_built"] = _parse_int(value_text)
        elif "lot size" in type_text:
            result["lot_size"] = value_text
        elif "price" in type_text and "sq" in type_text:
            result["price_per_sqft"] = value_text

    return result


def _parse_description(soup: BeautifulSoup) -> str | None:
    """Parse listing description from about-this-home section."""
    about = soup.find(id="about-this-home-scroll")
    if about:
        remarks = about.find(class_="remarks")
        if remarks:
            return remarks.get_text(strip=True) or None
        # Fallback: get text excluding heading
        text = about.get_text(strip=True)
        # Remove "About this home" prefix
        text = re.sub(r"^About this home\s*", "", text, flags=re.IGNORECASE)
        return text or None
    return None


def _determine_agent_role(heading_text: str, item: Tag) -> str | None:
    """Determine whether an agent-info-item represents a listing or buying agent."""
    ht = heading_text.lower()
    if "listed by" in ht or "list" in ht:
        return "listing"
    if "bought" in ht or "buy" in ht:
        return "buying"
    # Check ancestor classes for context
    for parent in item.parents:
        cls: list[str] = parent.get("class") or []  # type: ignore[assignment]
        if "listing-agent-item" in cls or "redfin-agent" in cls:
            return "listing"
        if "buyer-agent-item" in cls:
            return "buying"
        if "agent-info-section" in cls:
            break
    return None


def _parse_agent_info(soup: BeautifulSoup) -> dict[str, str | None]:
    """Parse listing and buying agent information.

    Supports two HTML structures:
    1. Semantic elements (real Redfin pages): ``agent-basic-details--heading``
       and ``agent-basic-details--broker`` classes inside each
       ``agent-info-item``.
    2. Pipe/bullet-delimited plain text (legacy test fixtures):
       ``"Listed by | Agent | • | Brokerage"``.
    """
    result: dict[str, str | None] = {
        "listing_agent": None,
        "listing_brokerage": None,
        "buying_agent": None,
        "buying_brokerage": None,
    }
    section = soup.find(class_="agent-info-section")
    if not section:
        return result

    for item in section.find_all(class_="agent-info-item"):
        heading = item.find(class_="agent-basic-details--heading")
        broker_el = item.find(class_="agent-basic-details--broker")

        if heading:
            # --- Semantic element approach (real Redfin HTML) ---
            heading_text = heading.get_text(strip=True)
            agent_name = (
                re.sub(
                    r"^(Listed by|Bought with)\s*",
                    "",
                    heading_text,
                    flags=re.IGNORECASE,
                ).strip()
                or None
            )
            brokerage = (
                re.sub(r"^[•·]\s*", "", broker_el.get_text(strip=True)).strip()
                if broker_el
                else None
            ) or None

            role = _determine_agent_role(heading_text, item)
            if role == "listing":
                result["listing_agent"] = agent_name
                result["listing_brokerage"] = brokerage
            elif role == "buying":
                result["buying_agent"] = agent_name
                result["buying_brokerage"] = brokerage
        else:
            # --- Fallback: pipe / bullet text split (legacy fixtures) ---
            text = item.get_text(" ", strip=True)
            parts = [p.strip() for p in re.split(r"[|•]", text) if p.strip()]

            if len(parts) >= 2:
                role_text = parts[0].lower()
                agent = parts[1] if len(parts) >= 2 else None
                brokerage = parts[2] if len(parts) >= 3 else None

                if "list" in role_text:
                    result["listing_agent"] = agent
                    result["listing_brokerage"] = brokerage
                elif "bought" in role_text or "buy" in role_text:
                    result["buying_agent"] = agent
                    result["buying_brokerage"] = brokerage

    return result


def _get_price_label(soup: BeautifulSoup) -> str | None:
    """Read the statsLabel text from the price-section stat block."""

    def _match_stat(name: str):
        return lambda c: c and name in c and "stat-block" in c

    price_block = soup.find("div", class_=_match_stat("price-section"))
    if price_block:
        label = price_block.find(class_="statsLabel")
        if label:
            return label.get_text(strip=True) or None
    return None


def _parse_redfin_estimate(soup: BeautifulSoup) -> str | None:
    """Parse Redfin estimate value."""
    est = soup.find(class_="RedfinEstimateSectionRemodel")
    if not est:
        return None

    # The estimate price is in a div with class "price smallerFont"
    price_div = est.find(class_="price")
    if price_div:
        return _parse_price(price_div.get_text(strip=True))

    return None


def _parse_sale_history(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    """Parse sale history from BasicTable rows."""
    result: list[dict[str, str | None]] = []
    panel = soup.find(class_="sale-history-panel")
    if not panel:
        return result

    rows = panel.find_all(class_="BasicTable__row")
    for row in rows:
        date_col = row.find(class_="date")
        event_col = row.find(class_="event")
        price_col = row.find(class_="price")

        if not date_col:
            continue

        entry: dict[str, str | None] = {
            "date": date_col.get_text(strip=True) or None,
            "event": event_col.get_text(strip=True) if event_col else None,
            "price": None,
        }

        if price_col:
            # Price col may contain main price + subtext (e.g. "$721,000$247/sq ft")
            # Get just the first price
            price_text = _parse_price(price_col.get_text(strip=True))
            entry["price"] = price_text

        result.append(entry)

    return result


def _parse_tax_history(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    """Parse tax history from TaxHistoryTable."""
    result: list[dict[str, str | None]] = []
    table = soup.find("table", class_="TaxHistoryTable")
    if not table:
        return result

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if not cells or len(cells) < 5:
            continue

        entry: dict[str, str | None] = {
            "year": cells[0].get_text(strip=True) or None,
            "tax": cells[1].get_text(strip=True) or None,
            "land": cells[2].get_text(strip=True) or None,
            "additions": cells[3].get_text(strip=True) or None,
            "assessed_value": cells[4].get_text(strip=True) or None,
        }
        result.append(entry)

    return result


def _is_hidden_entry(item: Tag) -> bool:
    """Check if an entryItem belongs to a hidden custom fields section.

    Redfin marks MLS custom/hidden fields by placing a ``<li>`` with the exact
    text ``"hidden custom fields"`` as a sibling inside the same ``<ul>``.
    """
    parent = item.parent
    if not parent:
        return False
    return any(
        child.get_text(strip=True) == "hidden custom fields" for child in parent.find_all("li")
    )


def _parse_property_details(soup: BeautifulSoup) -> dict[str, str | bool] | None:
    """Parse property details into a flat key-value dict.

    Uses the ``id="propertyDetails-preview"`` container and extracts
    ``<li class="entryItem">`` elements.  Key-value pairs (``"Key: Value"``)
    become ``{snake_key: value_string}``.  Single-word features (no ``: ``
    separator) become ``{snake_key: True}`` (boolean features like "Has Basement").

    Items in hidden-custom-fields sections and bare comma-containing items
    (likely stray values from hidden fields) are skipped.
    """
    container = soup.find(id="propertyDetails-preview")
    if not container:
        return None

    items = container.find_all("li", class_="entryItem")
    if not items:
        return None

    result: dict[str, str | bool] = {}
    for item in items:
        text = item.get_text(strip=True)
        if not text:
            continue

        parts = text.split(": ", 1)

        if len(parts) == 2:
            # Standard key-value pair
            key, value = parts
            result[normalize_field_name(key)] = value
        else:
            # Single value — check for hidden/stray fields
            if _is_hidden_entry(item):
                logger.debug("Skipping hidden field entry: %s", text)
                continue
            if "," in text:
                logger.debug("Skipping comma-containing single item: %s", text)
                continue
            # Boolean feature (e.g. "Has Basement", "Crawl Space")
            result[normalize_field_name(text)] = True

    return result or None


def _parse_schools(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    """Parse schools from SchoolsSectionRemodel."""
    result: list[dict[str, str | None]] = []
    section = soup.find(class_="SchoolsSectionRemodel")
    if not section:
        return result

    table = section.find(class_="schools-table")
    if not table:
        return result

    # Each school is a ListItem with col-10 class
    items = [li for li in table.find_all(class_="ListItem") if "col-10" in (li.get("class") or [])]

    for item in items:
        icon = item.find(class_="ListItem__primaryIcon")
        heading = item.find(class_="ListItem__heading")
        desc = item.find(class_="ListItem__description")

        rating_text = icon.get_text(strip=True) if icon else None
        # Rating is like "7/10" — extract just the number
        rating = None
        if rating_text:
            m = re.match(r"(\d+)", rating_text)
            if m:
                rating = m.group(1)

        entry: dict[str, str | None] = {
            "rating": rating,
            "name": heading.get_text(strip=True) if heading else None,
            "description": desc.get_text(strip=True) if desc else None,
        }
        result.append(entry)

    return result


def _parse_source_url(soup: BeautifulSoup) -> str | None:
    """Extract the original Redfin listing URL from the HTML.

    Tries three sources in order:
    1. <link rel="canonical"> href
    2. <meta property="og:url"> content
    3. SingleFile comment (saved from url=... or url: ...)
    """
    # 1. Canonical link
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        href = canonical["href"]
        if isinstance(href, str) and href.startswith("http"):
            return href

    # 2. Open Graph URL
    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        content = og_url["content"]
        if isinstance(content, str) and content.startswith("http"):
            return content

    # 3. SingleFile comment at top of file
    for element in soup.children:
        if hasattr(element, "strip") or not hasattr(element, "output_ready"):
            # Check Comment nodes
            from bs4 import Comment

            if isinstance(element, Comment):
                text = str(element)
                # "saved from url=(0123)https://..." format
                m = re.search(r"saved from url=\(\d+\)(https?://\S+)", text)
                if m:
                    return m.group(1)
                # "url: https://..." format (SingleFile)
                m = re.search(r"url:\s*(https?://\S+)", text)
                if m:
                    return m.group(1)

    return None


def _parse_climate_risks(soup: BeautifulSoup) -> dict[str, str | None]:
    """Parse climate risk factors (flood and fire)."""
    result: dict[str, str | None] = {
        "climate_flood_factor": None,
        "climate_fire_factor": None,
    }
    section = soup.find(class_="ClimateRiskDataSection")
    if not section:
        return result

    cards = section.find_all(class_="riskFactorCard")
    for card in cards:
        text = card.get_text(" ", strip=True)
        if "flood" in text.lower():
            # "Flood Factor - Major 70% chance of flooding in next 30 years"
            m = re.search(r"Flood Factor\s*[-–]\s*(\w+)", text, re.IGNORECASE)
            if m:
                result["climate_flood_factor"] = m.group(1)
        elif "fire" in text.lower():
            m = re.search(r"Fire Factor\s*[-–]\s*(\w+)", text, re.IGNORECASE)
            if m:
                result["climate_fire_factor"] = m.group(1)

    return result


def _extract_photos(
    soup: BeautifulSoup,
    slug: str,
    s3_client: Any = None,
) -> tuple[list[str], int]:
    """Extract base64-encoded photos and upload to S3.

    Returns (list of S3 keys for uploaded photos, number of failed uploads).
    """
    settings = get_settings()
    container = soup.find(class_="InlinePhotoPreviewRedesign")
    if not container:
        return [], 0

    imgs = container.find_all("img")
    s3_paths: list[str] = []
    failed = 0

    if s3_client is None:
        s3_client = _get_s3_client()

    for i, img in enumerate(imgs):
        src_val = img.get("src", "")
        src = src_val if isinstance(src_val, str) else ""
        if not src.startswith("data:image"):
            continue

        # Parse data URI: data:image/jpeg;base64,/9j/4AAQ...
        m = re.match(r"data:image/(\w+);base64,(.+)", src)
        if not m:
            continue

        ext = m.group(1)
        b64_data = m.group(2)

        try:
            image_bytes = base64.b64decode(b64_data)
        except Exception:
            logger.warning("Failed to decode base64 image %d for %s", i, slug)
            failed += 1
            continue

        s3_key = f"{settings.redfin_s3_photos_prefix}/{slug}/photo_{i}.{ext}"

        try:
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=image_bytes,
                ContentType=f"image/{ext}",
            )
            s3_paths.append(s3_key)
        except Exception:
            logger.warning("Failed to upload photo %d to S3 for %s", i, slug)
            failed += 1

    return s3_paths, failed


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def _parse_html_file(file_path: str, source_filename: str) -> tuple[dict, int]:
    """Open an HTML file, parse with lxml, and extract all listing data."""
    logger.info("Parsing %s", source_filename)

    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    data: dict = {}

    # Address
    data.update(_parse_address(soup, source_filename))

    slug = _slugify_address(data.get("address") or source_filename)

    # All parser functions
    data.update(_parse_listing_status(soup))
    data.update(_parse_key_stats(soup))

    # For sold listings the price-section statsValue is NOT the listing price.
    # If the statsLabel says "Sold Price" move it to sold_price; otherwise it is
    # just a Redfin estimate, so clear listing_price.
    if data.get("listing_status") == "SOLD":
        label = _get_price_label(soup)
        if label and "sold" in label.lower() and not data.get("sold_price"):
            data["sold_price"] = data["listing_price"]
        data["listing_price"] = None

    data.update(_parse_key_details(soup))
    data["description"] = _parse_description(soup)
    data.update(_parse_agent_info(soup))
    data["redfin_estimate"] = _parse_redfin_estimate(soup)
    data["sale_history"] = _parse_sale_history(soup)
    data["tax_history"] = _parse_tax_history(soup)
    data["property_details"] = _parse_property_details(soup)
    data["schools"] = _parse_schools(soup)
    data.update(_parse_climate_risks(soup))
    data["redfin_url"] = _parse_source_url(soup)

    # Photos
    photo_paths, photo_failures = _extract_photos(soup, slug)
    data["photo_s3_paths"] = photo_paths

    data["source_file"] = source_filename
    data["extracted_at"] = _parse_filename_date(source_filename)

    return data, photo_failures


def _upsert_listing(session, data: dict) -> bool:
    """Insert or update a listing record keyed on address.

    Returns True if the record was inserted/updated, False if skipped
    because the incoming data is older than what already exists.
    """
    address = data.get("address")
    if not address:
        logger.warning("Skipping record with no address from %s", data.get("source_file"))
        return False

    existing = (
        session.query(StagingRedfinListing).filter(StagingRedfinListing.address == address).first()
    )

    if existing:
        new_date = data.get("extracted_at")
        existing_date = existing.extracted_at
        # Skip update when incoming data is strictly older than what's in the DB
        if existing_date is not None and new_date is not None and new_date < existing_date:
            logger.info(
                "Skipping older extraction for %s (incoming %s < existing %s)",
                address,
                new_date,
                existing_date,
            )
            return False
        for key, value in data.items():
            if key != "id" and hasattr(existing, key):
                setattr(existing, key, value)
        logger.info("Updated existing listing for %s", address)
    else:
        filtered = {k: v for k, v in data.items() if hasattr(StagingRedfinListing, k)}
        record = StagingRedfinListing(**filtered)
        session.add(record)
        logger.info("Inserted new listing for %s", address)

    return True


def _archive_to_s3(file_path: str, source_filename: str) -> bool:
    """Upload processed HTML to S3 archive and delete local file.

    Returns True if the file was successfully archived (or already exists in S3).
    Returns False if the upload could not be verified — the local file is kept.
    """
    settings = get_settings()
    s3_key = f"{settings.redfin_s3_archive_prefix}/{source_filename}"

    try:
        client = _get_s3_client()

        if not os.path.exists(file_path):
            # File gone — verify it actually made it to S3 before considering it OK
            try:
                client.head_object(Bucket=settings.s3_bucket, Key=s3_key)
                logger.info("File already archived to S3 by another run: %s", source_filename)
                return True
            except Exception:
                logger.error(
                    "Local file missing and not found in S3 — data may be lost: %s",
                    source_filename,
                )
                return False

        client.upload_file(file_path, settings.s3_bucket, s3_key)

        # Verify the upload landed before deleting the local copy
        client.head_object(Bucket=settings.s3_bucket, Key=s3_key)

        os.remove(file_path)
        logger.info("Archived %s to s3://%s/%s", source_filename, settings.s3_bucket, s3_key)
        return True
    except Exception:
        logger.exception("Failed to archive %s to S3 — keeping local file", source_filename)
        return False


def _download_from_s3(s3_key: str) -> str:
    """Download file from S3 to a temp file. Returns temp file path."""
    settings = get_settings()
    client = _get_s3_client()

    suffix = os.path.splitext(s3_key)[1] or ".html"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)

    os.close(fd)
    client.download_file(settings.s3_bucket, s3_key, tmp_path)
    return tmp_path


def process_listings(
    *,
    directory: str | None = None,
    file_path: str | None = None,
    reprocess_s3_prefix: str | None = None,
) -> dict[str, int]:
    """Process Redfin HTML listings.

    Exactly one of directory, file_path, or reprocess_s3_prefix should be provided.
    If none provided, uses the configured redfin_html_dir.

    Returns dict with processed/error counts.
    """
    settings = get_settings()
    files: list[tuple[str, str, bool]] = []  # (path, filename, is_temp)

    if reprocess_s3_prefix:
        # List objects under the S3 prefix and download each
        client = _get_s3_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=reprocess_s3_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".html"):
                    tmp_path = _download_from_s3(key)
                    filename = os.path.basename(key)
                    files.append((tmp_path, filename, True))
    elif file_path:
        files.append((file_path, os.path.basename(file_path), False))
    else:
        search_dir = directory or settings.redfin_html_dir
        pattern = os.path.join(search_dir, "*.html")
        for path in sorted(glob.glob(pattern)):
            files.append((path, os.path.basename(path), False))

    if not files:
        logger.warning("No HTML files found to process")
        return {"processed": 0, "skipped": 0, "errors": 0}

    logger.info("Found %d HTML files to process", len(files))
    processed = 0
    skipped = 0
    errors = 0

    for path, filename, is_temp in files:
        session = SessionLocal()
        try:
            data, photo_failures = _parse_html_file(path, filename)
            upserted = _upsert_listing(session, data)
            session.commit()

            if upserted:
                processed += 1
            else:
                skipped += 1

            # Archive to S3 (skip if reprocessing from S3)
            if not reprocess_s3_prefix:
                if photo_failures:
                    logger.warning(
                        "Skipping archive for %s — %d photo upload(s) failed, "
                        "keeping file for retry",
                        filename,
                        photo_failures,
                    )
                else:
                    _archive_to_s3(path, filename)

        except Exception:
            session.rollback()
            errors += 1
            logger.exception("Error processing %s", filename)
        finally:
            session.close()
            # Clean up temp files from S3 downloads
            if is_temp and os.path.exists(path):
                os.remove(path)

    logger.info(
        "Processing complete: %d processed, %d skipped, %d errors", processed, skipped, errors
    )
    return {"processed": processed, "skipped": skipped, "errors": errors}
