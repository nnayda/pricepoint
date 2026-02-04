"""Collect school location and rating data.

Sources: GreatSchools API, state education department datasets.
"""


def fetch_schools(*, state: str, district: str | None = None) -> None:
    """Download school records for the given state/district.

    Stores results in the PostGIS ``schools`` table.
    """
    raise NotImplementedError
