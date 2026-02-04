"""Collect macroeconomic indicators (mortgage rates, CPI, unemployment, etc.).

Sources: FRED API, BLS API.
"""


def fetch_macro_indicators(*, start_date: str, end_date: str) -> None:
    """Download macroeconomic time-series data for the given date range.

    Stores results in the database.
    """
    raise NotImplementedError
