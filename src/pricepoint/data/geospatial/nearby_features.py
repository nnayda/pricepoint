"""Collect nearby point-of-interest features (parks, transit stops, amenities).

Sources: OpenStreetMap Overpass API, municipal GIS layers.
"""


def fetch_nearby_features(*, latitude: float, longitude: float, radius_m: int = 1000) -> None:
    """Download nearby POI features within the given radius.

    Stores results in the PostGIS database.
    """
    raise NotImplementedError
