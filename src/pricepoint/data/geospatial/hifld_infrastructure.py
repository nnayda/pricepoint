"""Collect HIFLD infrastructure features.

Downloads cell towers, transmission lines, power plants, natural gas pipelines,
and petroleum pipelines from HIFLD ArcGIS endpoints and loads them into PostGIS.
"""

import logging

from pricepoint.config.settings import get_settings
from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    build_point_wkb,
    fetch_arcgis_dataset,
    verify_arcgis_dataset,
)
from pricepoint.db.models import (
    CellTower,
    Hospital,
    NatGasPipeline,
    PetroleumPipeline,
    PowerPlant,
    TransmissionLine,
)

logger = logging.getLogger(__name__)


# -- Cell Towers --------------------------------------------------------------


def _map_cell_tower(feature: dict) -> CellTower:
    """Map an ArcGIS feature to a CellTower model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return CellTower(
        objectid=attrs.get("OBJECTID"),
        licensee=attrs.get("Licensee"),
        callsign=attrs.get("Callsign"),
        city=attrs.get("LocCity"),
        state=attrs.get("LocState"),
        county=attrs.get("LocCounty"),
        structure_type=attrs.get("StrucType"),
        height_ft=attrs.get("AllStruc"),
        geom=build_point_wkb(geometry),
    )


def fetch_cell_towers() -> None:
    """Fetch all HIFLD cell tower features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.cell_towers_base_url,
        model_class=CellTower,
        mapper=_map_cell_tower,
        dataset_name="cell_towers",
    )


def verify_cell_towers() -> None:
    """Verify cell tower records were loaded."""
    verify_arcgis_dataset(CellTower, "cell_towers")


# -- Transmission Lines -------------------------------------------------------


def _map_transmission_line(feature: dict) -> TransmissionLine:
    """Map an ArcGIS feature to a TransmissionLine model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return TransmissionLine(
        objectid=attrs.get("OBJECTID"),
        line_type=attrs.get("TYPE"),
        status=attrs.get("STATUS"),
        owner=attrs.get("OWNER"),
        voltage=attrs.get("VOLTAGE"),
        volt_class=attrs.get("VOLT_CLASS"),
        sub_1=attrs.get("SUB_1"),
        sub_2=attrs.get("SUB_2"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_transmission_lines() -> None:
    """Fetch all HIFLD transmission line features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.transmission_lines_base_url,
        model_class=TransmissionLine,
        mapper=_map_transmission_line,
        dataset_name="transmission_lines",
    )


def verify_transmission_lines() -> None:
    """Verify transmission line records were loaded."""
    verify_arcgis_dataset(TransmissionLine, "transmission_lines")


# -- Power Plants -------------------------------------------------------------


def _map_power_plant(feature: dict) -> PowerPlant:
    """Map an ArcGIS feature to a PowerPlant model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return PowerPlant(
        objectid=attrs.get("OBJECTID"),
        plant_code=attrs.get("Plant_Code"),
        name=attrs.get("Plant_Name"),
        utility_name=attrs.get("Utility_Na"),
        state=attrs.get("State"),
        county=attrs.get("County"),
        primary_source=attrs.get("PrimSource"),
        install_mw=attrs.get("Install_MW"),
        total_mw=attrs.get("Total_MW"),
        geom=build_point_wkb(geometry),
    )


def fetch_power_plants() -> None:
    """Fetch all HIFLD power plant features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.power_plants_base_url,
        model_class=PowerPlant,
        mapper=_map_power_plant,
        dataset_name="power_plants",
    )


def verify_power_plants() -> None:
    """Verify power plant records were loaded."""
    verify_arcgis_dataset(PowerPlant, "power_plants")


# -- Natural Gas Pipelines ----------------------------------------------------


def _map_nat_gas_pipeline(feature: dict) -> NatGasPipeline:
    """Map an ArcGIS feature to a NatGasPipeline model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return NatGasPipeline(
        objectid=attrs.get("OBJECTID"),
        pipe_type=attrs.get("TYPEPIPE"),
        operator=attrs.get("Operator"),
        status=attrs.get("Status"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_nat_gas_pipelines() -> None:
    """Fetch all HIFLD natural gas pipeline features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.nat_gas_pipelines_base_url,
        model_class=NatGasPipeline,
        mapper=_map_nat_gas_pipeline,
        dataset_name="nat_gas_pipelines",
    )


def verify_nat_gas_pipelines() -> None:
    """Verify natural gas pipeline records were loaded."""
    verify_arcgis_dataset(NatGasPipeline, "nat_gas_pipelines")


# -- Petroleum Pipelines ------------------------------------------------------


def _map_petroleum_pipeline(feature: dict) -> PetroleumPipeline:
    """Map an ArcGIS feature to a PetroleumPipeline model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    paths = geometry.get("paths") if geometry else None
    return PetroleumPipeline(
        objectid=attrs.get("OBJECTID"),
        operator=attrs.get("Opername"),
        pipe_name=attrs.get("Pipename"),
        geom=build_multilinestring_wkb(paths),
    )


def fetch_petroleum_pipelines() -> None:
    """Fetch all HIFLD petroleum pipeline features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.petroleum_pipelines_base_url,
        model_class=PetroleumPipeline,
        mapper=_map_petroleum_pipeline,
        dataset_name="petroleum_pipelines",
    )


def verify_petroleum_pipelines() -> None:
    """Verify petroleum pipeline records were loaded."""
    verify_arcgis_dataset(PetroleumPipeline, "petroleum_pipelines")


# -- Hospitals ---------------------------------------------------------------


def _map_hospital(feature: dict) -> Hospital:
    """Map an ArcGIS feature to a Hospital model instance."""
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry")
    return Hospital(
        objectid=attrs.get("OBJECTID"),
        hifld_id=attrs.get("ID"),
        name=attrs.get("NAME"),
        address=attrs.get("ADDRESS"),
        city=attrs.get("CITY"),
        state=attrs.get("STATE"),
        zip_code=attrs.get("ZIP"),
        telephone=attrs.get("TELEPHONE"),
        hospital_type=attrs.get("TYPE"),
        status=attrs.get("STATUS"),
        population=attrs.get("POPULATION"),
        county=attrs.get("COUNTY"),
        countyfips=attrs.get("COUNTYFIPS"),
        owner=attrs.get("OWNER"),
        beds=attrs.get("BEDS"),
        trauma=attrs.get("TRAUMA"),
        helipad=attrs.get("HELIPAD"),
        website=attrs.get("WEBSITE"),
        naics_code=attrs.get("NAICS_CODE"),
        naics_desc=attrs.get("NAICS_DESC"),
        ttl_staff=attrs.get("TTL_STAFF"),
        geom=build_point_wkb(geometry),
    )


def fetch_hospitals() -> None:
    """Fetch all HIFLD hospital features and load into PostGIS."""
    settings = get_settings()
    fetch_arcgis_dataset(
        base_url=settings.hifld_hospitals_base_url,
        model_class=Hospital,
        mapper=_map_hospital,
        dataset_name="hifld_hospitals",
    )


def verify_hospitals() -> None:
    """Verify hospital records were loaded."""
    verify_arcgis_dataset(Hospital, "hifld_hospitals")
