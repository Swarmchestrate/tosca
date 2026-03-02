"""Tests for the sardou library API"""
import json
from pathlib import Path

import pytest

from sardou import Sardou
from sardou.sardou import Sardou as SardouInternal
from tests.marks import requires_puccini

CDT_DIR = Path(__file__).parent / "templates" / "cdt"
SAT_DIR = Path(__file__).parent / "templates" / "sat"


# ---------------------------------------------------------------------------
# requirements.py — convert_node_filter_to_capabilities
# ---------------------------------------------------------------------------

class TestConvertNodeFilterToCapabilities:
    @pytest.fixture
    def convert(self):
        from sardou.requirements import convert_node_filter_to_capabilities
        return convert_node_filter_to_capabilities

    def test_empty_filter_returns_empty_dict(self, convert):
        assert convert({}) == {}

    def test_no_and_key_returns_empty_dict(self, convert):
        assert convert({"$or": []}) == {}

    def test_equal_constraint_extracted(self, convert):
        node_filter = {
            "$and": [
                {
                    "$equal": [
                        {"$get_property": ["SELF", "TARGET", "CAPABILITY", "host", "num-cpus"]},
                        4,
                    ]
                }
            ]
        }
        result = convert(node_filter)
        assert result["host"]["properties"]["num-cpus"] == 4

    def test_non_equal_constraint_stored_as_dict(self, convert):
        node_filter = {
            "$and": [
                {
                    "$greater_or_equal": [
                        {"$get_property": ["SELF", "TARGET", "CAPABILITY", "host", "mem-size"]},
                        "2 GB",
                    ]
                }
            ]
        }
        result = convert(node_filter)
        assert result["host"]["properties"]["mem-size"] == {"$greater_or_equal": "2 GB"}

    def test_multiple_capabilities_grouped(self, convert):
        node_filter = {
            "$and": [
                {
                    "$equal": [
                        {"$get_property": ["SELF", "TARGET", "CAPABILITY", "host", "num-cpus"]},
                        2,
                    ]
                },
                {
                    "$equal": [
                        {"$get_property": ["SELF", "TARGET", "CAPABILITY", "os", "distribution"]},
                        "ubuntu",
                    ]
                },
            ]
        }
        result = convert(node_filter)
        assert result["host"]["properties"]["num-cpus"] == 2
        assert result["os"]["properties"]["distribution"] == "ubuntu"


# ---------------------------------------------------------------------------
# requirements.py — extract_nodes_with_filter
# ---------------------------------------------------------------------------

class TestExtractNodesWithFilter:
    @pytest.fixture
    def extract(self):
        from sardou.requirements import extract_nodes_with_filter
        return extract_nodes_with_filter

    def _tosca(self, node_templates):
        return {"service_template": {"node_templates": node_templates}}

    def test_no_requirements_returns_empty(self, extract):
        tosca = self._tosca({"app": {"type": "swch:Microservice"}})
        assert extract(tosca) == {}

    def test_requirement_without_filter_ignored(self, extract):
        tosca = self._tosca({
            "app": {
                "requirements": [{"host": {"node": "some-node"}}]
            }
        })
        assert extract(tosca) == {}

    def test_node_with_filter_captured(self, extract):
        nf = {"$and": []}
        tosca = self._tosca({
            "app": {
                "requirements": [{"host": {"node_filter": nf}}]
            }
        })
        result = extract(tosca)
        assert "app" in result
        assert result["app"] is nf

    def test_missing_service_template_returns_empty(self, extract):
        assert extract({}) == {}


# ---------------------------------------------------------------------------
# requirements.py — tosca_to_ask_dict
# ---------------------------------------------------------------------------

class TestToscaToAskDict:
    @pytest.fixture
    def to_ask(self):
        from sardou.requirements import tosca_to_ask_dict
        return tosca_to_ask_dict

    def test_no_node_filters_returns_empty(self, to_ask):
        tosca = {"service_template": {"node_templates": {"app": {"type": "X"}}}}
        assert to_ask(tosca) == {}

    def test_output_has_metadata_and_capabilities(self, to_ask):
        tosca = {
            "service_template": {
                "node_templates": {
                    "worker": {
                        "requirements": [
                            {
                                "host": {
                                    "node_filter": {
                                        "$and": [
                                            {
                                                "$equal": [
                                                    {"$get_property": ["SELF", "TARGET", "CAPABILITY", "host", "num-cpus"]},
                                                    4,
                                                ]
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        result = to_ask(tosca)
        assert "worker" in result
        assert "metadata" in result["worker"]
        assert "capabilities" in result["worker"]
        assert result["worker"]["capabilities"]["host"]["properties"]["num-cpus"] == 4

    def test_metadata_fields_present(self, to_ask):
        tosca = {
            "service_template": {
                "node_templates": {
                    "svc": {
                        "requirements": [
                            {"host": {"node_filter": {"$and": []}}}
                        ]
                    }
                }
            }
        }
        meta = to_ask(tosca)["svc"]["metadata"]
        for field in ("created_by", "created_at", "description", "version"):
            assert field in meta


# ---------------------------------------------------------------------------
# capacities.py — _unwrap
# ---------------------------------------------------------------------------

class TestUnwrap:
    @pytest.fixture
    def unwrap(self):
        from sardou.capacities import _unwrap
        return _unwrap

    def test_primitive_passthrough(self, unwrap):
        assert unwrap(42) == 42
        assert unwrap("hello") == "hello"

    def test_dollar_primitive(self, unwrap):
        assert unwrap({"$primitive": 7}) == 7

    def test_dollar_list(self, unwrap):
        assert unwrap({"$list": [{"$primitive": 1}, {"$primitive": 2}]}) == [1, 2]

    def test_plain_dict_passthrough(self, unwrap):
        assert unwrap({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_plain_dict_with_nested_primitive_not_recursed(self, unwrap):
        # _unwrap only unwraps at the top level; plain dicts are returned as-is
        result = unwrap({"key": {"$primitive": 99}})
        assert result == {"key": {"$primitive": 99}}


# ---------------------------------------------------------------------------
# capacities.py — _is_overall
# ---------------------------------------------------------------------------

class TestIsOverall:
    @pytest.fixture
    def is_overall(self):
        from sardou.capacities import _is_overall
        return _is_overall

    def test_matching_type_returns_true(self, is_overall):
        node = {"types": {"eu.swarmchestrate::OverallCapacity": {}}}
        assert is_overall(node) is True

    def test_non_matching_type_returns_false(self, is_overall):
        node = {"types": {"eu.swarmchestrate::Capacity": {}}}
        assert is_overall(node) is False

    def test_no_types_key_returns_false(self, is_overall):
        assert is_overall({}) is False


# ---------------------------------------------------------------------------
# capacities.py — extract_capacities
# ---------------------------------------------------------------------------

class TestExtractCapacities:
    @pytest.fixture
    def extract(self):
        from sardou.capacities import extract_capacities
        return extract_capacities

    def _node(self, types, caps=None):
        return {"types": types, "capabilities": caps or {}}

    def test_instance_based_returns_capacity_flavour(self, extract):
        nodes = {
            "small": self._node(
                {"eu.swch::Capacity": {}},
                {"capacity": {"properties": {"instances": {"$primitive": 3}}},
                 "host": {"properties": {"num-cpus": {"$primitive": 2}}}},
            )
        }
        result = extract(nodes)
        assert "capacity_flavour" in result
        assert result["capacity_flavour"]["small"] == 3

    def test_overall_based_returns_capacity_raw(self, extract):
        nodes = {
            "pool": self._node(
                {"eu.swch::OverallCapacity": {}},
                {"capacity": {"properties": {"total": {"$primitive": 100}}}},
            )
        }
        result = extract(nodes)
        assert "capacity_raw" in result
        assert result["capacity_raw"]["total"] == 100

    def test_flavour_dict_populated(self, extract):
        nodes = {
            "medium": self._node(
                {"eu.swch::Capacity": {}},
                {"host": {"properties": {"mem-size": {"$primitive": "4 GB"}}}},
            )
        }
        result = extract(nodes)
        assert "medium" in result["flavour"]
        assert result["flavour"]["medium"]["host"]["mem-size"] == "4 GB"

    def test_empty_nodes_returns_empty_flavour(self, extract):
        result = extract({})
        assert result["flavour"] == {}

    def test_overall_node_excluded_from_flavour(self, extract):
        nodes = {
            "overall": self._node(
                {"eu.swch::OverallCapacity": {}},
                {"capacity": {"properties": {}}},
            )
        }
        result = extract(nodes)
        assert "overall" not in result["flavour"]


# ---------------------------------------------------------------------------
# Sardou public API (requires puccini-tosca)
# ---------------------------------------------------------------------------

@requires_puccini
class TestSardouCDTAPI:
    """Tests for the Sardou class used as a library, not via CLI."""

    @pytest.fixture
    def cloud_overall(self):
        return Sardou(str(CDT_DIR / "cloud-overall.yaml"))

    @pytest.fixture
    def cloud_instances(self):
        return Sardou(str(CDT_DIR / "cloud-instances.yaml"))

    def test_sardou_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            Sardou("/tmp/definitely_does_not_exist.yaml")

    def test_sardou_instance_has_path(self, cloud_overall):
        assert cloud_overall.path is not None

    def test_is_sat_false_for_capacity_template(self, cloud_overall):
        assert cloud_overall.isSAT is False

    def test_get_capacities_returns_dict(self, cloud_overall):
        caps = cloud_overall.get_capacities()
        assert isinstance(caps, dict)
        assert "flavour" in caps

    def test_get_capacities_raises_on_sat(self):
        """get_capacities() must raise TypeError when called on a SAT."""
        # Build a minimal fake Sardou without going through __init__
        fake = object.__new__(SardouInternal)
        fake.isSAT = True
        with pytest.raises(TypeError):
            fake.get_capacities()

    def test_get_requirements_returns_dict(self, cloud_overall):
        reqs = cloud_overall.get_requirements()
        assert isinstance(reqs, dict)

    def test_get_qos_returns_list(self, cloud_overall):
        qos = cloud_overall.get_qos()
        assert isinstance(qos, list)

    def test_get_cluster_returns_valid_json(self, cloud_overall):
        cluster_json = cloud_overall.get_cluster()
        parsed = json.loads(cluster_json)
        assert isinstance(parsed, dict)

    def test_raw_attribute_is_accessible(self, cloud_overall):
        assert hasattr(cloud_overall, "raw")

    def test_cloud_instances_parses(self, cloud_instances):
        assert cloud_instances.isSAT is False


@requires_puccini
class TestSardouSATAPI:
    """Tests for the Sardou class loaded with a SAT (service application template)."""

    @pytest.fixture
    def bookinfo(self):
        return Sardou(str(SAT_DIR / "BookInfo.yaml"))

    def test_is_sat_true(self, bookinfo):
        assert bookinfo.isSAT is True

    def test_get_requirements_returns_dict(self, bookinfo):
        reqs = bookinfo.get_requirements()
        assert isinstance(reqs, dict)

    def test_get_qos_returns_list(self, bookinfo):
        assert isinstance(bookinfo.get_qos(), list)

    def test_get_capacities_raises_type_error(self, bookinfo):
        with pytest.raises(TypeError):
            bookinfo.get_capacities()

    def test_get_cluster_returns_valid_json(self, bookinfo):
        parsed = json.loads(bookinfo.get_cluster())
        assert isinstance(parsed, dict)

    def test_raw_attribute_accessible(self, bookinfo):
        assert hasattr(bookinfo, "raw")
