"""Collect Redfin listing photos for image-based feature extraction.

Photo extraction is now integrated into redfin_listings.py, which extracts
base64-encoded photos from SingleFile HTML snapshots and uploads them to S3.
This stub is retained for API compatibility.
"""


def fetch_redfin_photos(*, listing_ids: list[str]) -> None:
    """Download listing photos and store them in S3-compatible object storage.

    Photos are now extracted directly from HTML snapshots by
    redfin_listings.process_listings(). This function is deprecated.
    """
    raise NotImplementedError(
        "Photo extraction is now handled by redfin_listings.process_listings()"
    )
