"""Tests for HIFLD infrastructure collectors."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.hifld_infrastructure import (
    _map_cell_tower,
    _map_hospital,
    _map_nat_gas_pipeline,
    _map_petroleum_pipeline,
    _map_power_plant,
    _map_transmission_line,
    fetch_cell_towers,
    fetch_hospitals,
    fetch_nat_gas_pipelines,
    fetch_petroleum_pipelines,
    fetch_power_plants,
    fetch_transmission_lines,
)

# -- Helpers ------------------------------------------------------------------

_SAMPLE_PATHS = [[[-78.6, 35.7], [-78.5, 35.8], [-78.4, 35.9]]]


def _make_point_feature(attrs_override=None, x=-78.6, y=35.7):
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {"attributes": attrs, "geometry": {"x": x, "y": y}}


def _make_line_feature(attrs_override=None, paths=None):
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {
        "attributes": attrs,
        "geometry": {"paths": paths if paths is not None else _SAMPLE_PATHS},
    }


# -- Cell Tower ---------------------------------------------------------------


class TestMapCellTower:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 1,
                "Licensee": "AT&T",
                "Callsign": "WQHT123",
                "LocCity": "Raleigh",
                "LocState": "NC",
                "LocCounty": "Wake",
                "StrucType": "TOWER",
                "AllStruc": 150.0,
            }
        )
        record = _map_cell_tower(feature)
        assert record.objectid == 1
        assert record.licensee == "AT&T"
        assert record.callsign == "WQHT123"
        assert record.city == "Raleigh"
        assert record.state == "NC"
        assert record.county == "Wake"
        assert record.structure_type == "TOWER"
        assert record.height_ft == 150.0
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature()
        feature["geometry"] = None
        record = _map_cell_tower(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_cell_tower(feature)
        assert record.objectid is None
        assert record.licensee is None


# -- Transmission Line --------------------------------------------------------


class TestMapTransmissionLine:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 2,
                "TYPE": "AC",
                "STATUS": "In Service",
                "OWNER": "Duke Energy",
                "VOLTAGE": 230.0,
                "VOLT_CLASS": "230-345",
                "SUB_1": "Substation A",
                "SUB_2": "Substation B",
            }
        )
        record = _map_transmission_line(feature)
        assert record.objectid == 2
        assert record.line_type == "AC"
        assert record.status == "In Service"
        assert record.owner == "Duke Energy"
        assert record.voltage == 230.0
        assert record.volt_class == "230-345"
        assert record.sub_1 == "Substation A"
        assert record.sub_2 == "Substation B"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_transmission_line(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_transmission_line(feature)
        assert record.objectid is None
        assert record.line_type is None


# -- Power Plant --------------------------------------------------------------


class TestMapPowerPlant:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 3,
                "Plant_Code": 12345,
                "Plant_Name": "Shearon Harris",
                "Utility_Na": "Duke Energy",
                "State": "NC",
                "County": "Wake",
                "PrimSource": "Nuclear",
                "Install_MW": 900.0,
                "Total_MW": 950.0,
            }
        )
        record = _map_power_plant(feature)
        assert record.objectid == 3
        assert record.plant_code == 12345
        assert record.name == "Shearon Harris"
        assert record.utility_name == "Duke Energy"
        assert record.state == "NC"
        assert record.county == "Wake"
        assert record.primary_source == "Nuclear"
        assert record.install_mw == 900.0
        assert record.total_mw == 950.0
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature()
        feature["geometry"] = None
        record = _map_power_plant(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_power_plant(feature)
        assert record.objectid is None
        assert record.name is None


# -- Natural Gas Pipeline -----------------------------------------------------


class TestMapNatGasPipeline:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 4,
                "TYPEPIPE": "Interstate",
                "Operator": "Williams Companies",
                "Status": "In Service",
            }
        )
        record = _map_nat_gas_pipeline(feature)
        assert record.objectid == 4
        assert record.pipe_type == "Interstate"
        assert record.operator == "Williams Companies"
        assert record.status == "In Service"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_nat_gas_pipeline(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_nat_gas_pipeline(feature)
        assert record.objectid is None
        assert record.pipe_type is None


# -- Petroleum Pipeline -------------------------------------------------------


class TestMapPetroleumPipeline:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 5,
                "Opername": "Colonial Pipeline",
                "Pipename": "Colonial Main",
            }
        )
        record = _map_petroleum_pipeline(feature)
        assert record.objectid == 5
        assert record.operator == "Colonial Pipeline"
        assert record.pipe_name == "Colonial Main"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_petroleum_pipeline(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_petroleum_pipeline(feature)
        assert record.objectid is None
        assert record.operator is None


# -- Fetch functions ----------------------------------------------------------


class TestFetchCellTowers:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(hifld_cell_towers_base_url="http://test/0")
        fetch_cell_towers()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_cell_towers"


class TestFetchTransmissionLines:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(
            hifld_transmission_lines_base_url="http://test/0"
        )
        fetch_transmission_lines()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_transmission_lines"


class TestFetchPowerPlants:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(hifld_power_plants_base_url="http://test/0")
        fetch_power_plants()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_power_plants"


class TestFetchNatGasPipelines:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(
            hifld_nat_gas_pipelines_base_url="http://test/0"
        )
        fetch_nat_gas_pipelines()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_nat_gas_pipelines"


class TestFetchPetroleumPipelines:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(
            hifld_petroleum_pipelines_base_url="http://test/0"
        )
        fetch_petroleum_pipelines()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_petroleum_pipelines"


# -- Hospital -----------------------------------------------------------------


class TestMapHospital:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 6,
                "ID": "0001234",
                "NAME": "WakeMed Raleigh Campus",
                "ADDRESS": "3000 New Bern Ave",
                "CITY": "Raleigh",
                "STATE": "NC",
                "ZIP": "27610",
                "TELEPHONE": "919-350-8000",
                "TYPE": "GENERAL ACUTE CARE",
                "STATUS": "OPEN",
                "POPULATION": 500000,
                "COUNTY": "WAKE",
                "COUNTYFIPS": "37183",
                "OWNER": "GOVERNMENT - STATE",
                "BEDS": 919,
                "TRAUMA": "LEVEL I",
                "HELIPAD": "Y",
                "WEBSITE": "http://wakemed.org",
                "NAICS_CODE": "622110",
                "NAICS_DESC": "GENERAL MEDICAL AND SURGICAL HOSPITALS",
                "TTL_STAFF": 3500,
            }
        )
        record = _map_hospital(feature)
        assert record.objectid == 6
        assert record.hifld_id == "0001234"
        assert record.name == "WakeMed Raleigh Campus"
        assert record.address == "3000 New Bern Ave"
        assert record.city == "Raleigh"
        assert record.state == "NC"
        assert record.zip_code == "27610"
        assert record.telephone == "919-350-8000"
        assert record.hospital_type == "GENERAL ACUTE CARE"
        assert record.status == "OPEN"
        assert record.population == 500000
        assert record.county == "WAKE"
        assert record.countyfips == "37183"
        assert record.owner == "GOVERNMENT - STATE"
        assert record.beds == 919
        assert record.trauma == "LEVEL I"
        assert record.helipad == "Y"
        assert record.website == "http://wakemed.org"
        assert record.naics_code == "622110"
        assert record.naics_desc == "GENERAL MEDICAL AND SURGICAL HOSPITALS"
        assert record.ttl_staff == 3500
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature()
        feature["geometry"] = None
        record = _map_hospital(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_hospital(feature)
        assert record.objectid is None
        assert record.name is None


class TestFetchHospitals:
    @patch("pricepoint.data.geospatial.hifld_infrastructure.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_infrastructure.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(hifld_hospitals_base_url="http://test/0")
        fetch_hospitals()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "hifld_hospitals"
