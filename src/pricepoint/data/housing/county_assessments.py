"""Collect county property assessment records.

Sources: county assessor websites, bulk data downloads.
"""


def fetch_county_assessments(*, county: str, state: str) -> None:
    """Download property assessment records for the given county.

    Stores results in the ``properties`` table.
    """
    raise NotImplementedError
