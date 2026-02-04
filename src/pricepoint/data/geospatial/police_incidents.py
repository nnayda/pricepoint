"""Collect police incident data with geographic coordinates.

Sources: municipal open-data portals (e.g., Socrata SODA API).
"""


def fetch_police_incidents(*, city: str, start_date: str, end_date: str) -> None:
    """Download police incident records for the given city and date range.

    Stores results in the PostGIS ``police_incidents`` table.
    """
    raise NotImplementedError
