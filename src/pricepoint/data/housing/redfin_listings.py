"""Collect Redfin listing data (price, beds, baths, sqft, etc.).

Sources: Redfin Data Center CSV downloads.
"""


def fetch_redfin_listings(*, region: str) -> None:
    """Download Redfin listing data for the given region.

    Stores results in the database.
    """
    raise NotImplementedError
