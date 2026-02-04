"""Collect Redfin listing photos for image-based feature extraction.

Sources: Redfin listing pages.
"""


def fetch_redfin_photos(*, listing_ids: list[str]) -> None:
    """Download listing photos and store them in S3-compatible object storage.

    Photos are keyed by listing ID for later retrieval by the feature pipeline.
    """
    raise NotImplementedError
