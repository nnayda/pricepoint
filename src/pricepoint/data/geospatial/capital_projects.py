"""Collect municipal capital improvement project data.

Sources: city budget portals, open-data APIs.
"""


def fetch_capital_projects(*, city: str) -> None:
    """Download capital improvement project records for the given city.

    Stores results in the database.
    """
    raise NotImplementedError
