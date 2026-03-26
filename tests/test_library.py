"""Tests for the sardou library API"""

import json
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from sardou import Sardou
from sardou.sardou import Sardou as SardouInternal
from tests.marks import requires_puccini

CDT_DIR = Path(__file__).parent / "templates" / "cdt"
SAT_DIR = Path(__file__).parent / "templates" / "sat"

_yaml = YAML(typ="safe")


def _load_sardou(filepath, mode):
    """Create a Sardou instance from *filepath* using the given input mode."""
    if mode == "path":
        return Sardou(str(filepath))
    # mode == "dict"
    with open(filepath) as f:
        data = _yaml.load(f)
    return Sardou(content=data)


# ---------------------------------------------------------------------------
# requirements.py — build_expression
# ---------------------------------------------------------------------------


class TestBuildExpression:
    @pytest.fixture
    def build(self):
        from sardou.requirements import build_expression

        return build_expression

    def test_empty_filter_returns_empty_lambda(self, build):
        assert build({}) == "lambda vals: ()"

    def test_no_and_key_returns_empty_lambda(self, build):
        assert build({"$or": []}) == "lambda vals: ()"

    def test_equal_constraint(self, build):
        node_filter = {
            "$and": [
                {
                    "$equal": [
                        {
                            "$get_property": [
                                "SELF",
                                "TARGET",
                                "CAPABILITY",
                                "host",
                                "num-cpus",
                            ]
                        },
                        4,
                    ]
                }
            ]
        }
        result = build(node_filter)
        assert result == "lambda vals: ((vals['host.num-cpus'] == 4))"

    def test_greater_or_equal_constraint(self, build):
        node_filter = {
            "$and": [
                {
                    "$greater_or_equal": [
                        {
                            "$get_property": [
                                "SELF",
                                "TARGET",
                                "CAPABILITY",
                                "host",
                                "mem-size",
                            ]
                        },
                        2,
                    ]
                }
            ]
        }
        result = build(node_filter)
        assert result == "lambda vals: ((vals['host.mem-size'] >= 2))"

    def test_string_value_quoted(self, build):
        node_filter = {
            "$and": [
                {
                    "$equal": [
                        {
                            "$get_property": [
                                "SELF",
                                "TARGET",
                                "CAPABILITY",
                                "locality",
                                "city",
                            ]
                        },
                        "budapest",
                    ]
                }
            ]
        }
        result = build(node_filter)
        assert result == "lambda vals: ((vals['locality.city'] == 'budapest'))"

    def test_multiple_conditions_joined_with_and(self, build):
        node_filter = {
            "$and": [
                {
                    "$greater_or_equal": [
                        {
                            "$get_property": [
                                "SELF",
                                "TARGET",
                                "CAPABILITY",
                                "host",
                                "num-cpus",
                            ]
                        },
                        2,
                    ]
                },
                {
                    "$greater_or_equal": [
                        {
                            "$get_property": [
                                "SELF",
                                "TARGET",
                                "CAPABILITY",
                                "host",
                                "mem-size",
                            ]
                        },
                        4,
                    ]
                },
            ]
        }
        result = build(node_filter)
        assert (
            result
            == "lambda vals: ((vals['host.num-cpus'] >= 2) and (vals['host.mem-size'] >= 4))"
        )

    def test_short_property_path_skipped(self, build):
        node_filter = {
            "$and": [
                {
                    "$equal": [
                        {"$get_property": ["SELF", "TARGET"]},
                        4,
                    ]
                }
            ]
        }
        assert build(node_filter) == "lambda vals: ()"


# ---------------------------------------------------------------------------
# requirements.py — extract_colocation_groups
# ---------------------------------------------------------------------------


class TestExtractColocationGroups:
    @pytest.fixture
    def extract(self):
        from sardou.requirements import extract_colocation_groups

        return extract_colocation_groups

    def test_no_policies_returns_empty(self, extract):
        assert extract({"service_template": {}}) == []

    def test_non_colocation_policy_ignored(self, extract):
        tosca = {
            "service_template": {
                "policies": [
                    {
                        "p1": {
                            "type": "swch:Scheduling.AntiColocation",
                            "targets": ["a", "b"],
                        }
                    }
                ]
            }
        }
        assert extract(tosca) == []

    def test_colocation_targets_extracted(self, extract):
        tosca = {
            "service_template": {
                "policies": [
                    {
                        "p1": {
                            "type": "swch:Scheduling.Colocation",
                            "targets": ["a", "b", "c"],
                        }
                    }
                ]
            }
        }
        result = extract(tosca)
        assert result == [["a", "b", "c"]]

    def test_multiple_colocation_groups(self, extract):
        tosca = {
            "service_template": {
                "policies": [
                    {
                        "p1": {
                            "type": "swch:Scheduling.Colocation",
                            "targets": ["a", "b"],
                        }
                    },
                    {
                        "p2": {
                            "type": "swch:Scheduling.Colocation",
                            "targets": ["c", "d"],
                        }
                    },
                ]
            }
        }
        result = extract(tosca)
        assert len(result) == 2

    def test_empty_dict_returns_empty(self, extract):
        assert extract({}) == []


# ---------------------------------------------------------------------------
# requirements.py — extract_reqs_with_filter
# ---------------------------------------------------------------------------


class TestExtractNodesWithFilter:
    @pytest.fixture
    def extract(self):
        from sardou.requirements import extract_reqs_with_filter

        return extract_reqs_with_filter

    def _tosca(self, node_templates):
        return {"service_template": {"node_templates": node_templates}}

    def test_no_requirements_returns_empty(self, extract):
        tosca = self._tosca({"app": {"type": "swch:Microservice"}})
        assert extract(tosca) == {}

    def test_requirement_without_filter_ignored(self, extract):
        tosca = self._tosca(
            {"app": {"requirements": [{"host": {"node": "some-node"}}]}}
        )
        assert extract(tosca) == {}

    def test_node_with_filter_captured(self, extract):
        nf = {"$and": []}
        tosca = self._tosca({"app": {"requirements": [{"host": {"node_filter": nf}}]}})
        result = extract(tosca)
        assert "app" in result
        assert result["app"]["node_filter"] is nf

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

    def test_output_has_expression_and_colocated(self, to_ask):
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
                                                "$greater_or_equal": [
                                                    {
                                                        "$get_property": [
                                                            "SELF",
                                                            "TARGET",
                                                            "CAPABILITY",
                                                            "host",
                                                            "num-cpus",
                                                        ]
                                                    },
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
        assert "expression" in result["worker"]
        assert "colocated" in result["worker"]
        assert "vals['host.num-cpus'] >= 4" in result["worker"]["expression"]

    def test_colocated_empty_when_no_policies(self, to_ask):
        tosca = {
            "service_template": {
                "node_templates": {
                    "svc": {"requirements": [{"host": {"node_filter": {"$and": []}}}]}
                }
            }
        }
        result = to_ask(tosca)
        assert result["svc"]["colocated"] == []

    def test_colocation_groups_representative_only(self, to_ask):
        tosca = {
            "service_template": {
                "node_templates": {
                    "a": {"requirements": [{"host": {"node_filter": {"$and": []}}}]},
                    "b": {"requirements": [{"host": {"node_filter": {"$and": []}}}]},
                },
                "policies": [
                    {
                        "col": {
                            "type": "swch:Scheduling.Colocation",
                            "targets": ["a", "b"],
                        }
                    }
                ],
            }
        }
        result = to_ask(tosca)
        assert "a" in result
        assert "b" not in result
        assert result["a"]["colocated"] == ["b"]

    def test_expression_is_evaluable_lambda(self, to_ask):
        tosca = {
            "service_template": {
                "node_templates": {
                    "svc": {
                        "requirements": [
                            {
                                "host": {
                                    "node_filter": {
                                        "$and": [
                                            {
                                                "$greater_or_equal": [
                                                    {
                                                        "$get_property": [
                                                            "SELF",
                                                            "TARGET",
                                                            "CAPABILITY",
                                                            "host",
                                                            "num-cpus",
                                                        ]
                                                    },
                                                    2,
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
        fn = eval(result["svc"]["expression"])
        assert fn({"host.num-cpus": 4}) is True
        assert fn({"host.num-cpus": 1}) is False


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
                {
                    "capacity": {"properties": {"instances": {"$primitive": 3}}},
                    "host": {"properties": {"num-cpus": {"$primitive": 2}}},
                },
            )
        }
        result = extract(nodes)
        assert "cloud_capacity_flavour" in result
        assert result["cloud_capacity_flavour"]["small"] == 3

    def test_overall_based_returns_capacity_raw(self, extract):
        nodes = {
            "pool": self._node(
                {"eu.swch::OverallCapacity": {}},
                {"capacity": {"properties": {"total": {"$primitive": 100}}}},
            )
        }
        result = extract(nodes)
        assert "cloud_capacity_raw" in result
        assert result["cloud_capacity_raw"]["total"] == 100

    def test_flavour_dict_populated(self, extract):
        nodes = {
            "medium": self._node(
                {"eu.swch::Capacity": {}},
                {"host": {"properties": {"mem-size": {"$primitive": "4"}}}},
            )
        }
        result = extract(nodes)
        assert "medium" in result["cloud_flavours"]
        assert result["cloud_flavours"]["medium"]["host"]["mem-size"] == "4"

    def test_empty_nodes_returns_empty_flavour(self, extract):
        result = extract({})
        assert "cloud_flavours" not in result

    def test_overall_node_excluded_from_flavour(self, extract):
        nodes = {
            "overall": self._node(
                {"eu.swch::OverallCapacity": {}},
                {"capacity": {"properties": {}}},
            )
        }
        result = extract(nodes)
        assert ("cloud_flavours" not in result) or (
            "overall" not in result["cloud_flavours"]
        )


# ---------------------------------------------------------------------------
# monitoring.py — extract_monitoring
# ---------------------------------------------------------------------------


class TestExtractMonitoring:
    @pytest.fixture
    def extract(self):
        from sardou.monitoring import extract_monitoring

        return extract_monitoring

    def test_node_with_metrics_and_slo(self, extract):
        nodes = {
            "app": {
                "capabilities": {
                    "metrics": {
                        "properties": {
                            "raw": [{"name": "cpu_util", "sensor": "Netdata"}],
                            "composite": [
                                {"name": "cpu_avg", "formula": "mean(cpu_util)"}
                            ],
                        }
                    },
                    "slo-constraints": {
                        "properties": {
                            "name": "cpu_slo",
                            "metric": "cpu_avg",
                            "operator": ">",
                            "threshold": 80.0,
                        }
                    },
                }
            }
        }
        result = extract(nodes)
        assert "app" in result
        assert "metrics" in result["app"]
        assert "slo-constraints" in result["app"]
        assert result["app"]["metrics"]["raw"][0]["name"] == "cpu_util"
        assert result["app"]["slo-constraints"]["threshold"] == 80.0

    def test_node_with_metrics_only(self, extract):
        nodes = {
            "svc": {
                "capabilities": {
                    "metrics": {
                        "properties": {"raw": [{"name": "mem_usage"}]}
                    }
                }
            }
        }
        result = extract(nodes)
        assert "svc" in result
        assert result["svc"]["metrics"]["raw"][0]["name"] == "mem_usage"
        assert result["svc"]["slo-constraints"] == {}

    def test_node_with_slo_only(self, extract):
        nodes = {
            "svc": {
                "capabilities": {
                    "slo-constraints": {
                        "properties": {
                            "name": "latency",
                            "operator": "<",
                            "threshold": 100,
                        }
                    }
                }
            }
        }
        result = extract(nodes)
        assert "svc" in result
        assert result["svc"]["slo-constraints"]["threshold"] == 100
        assert result["svc"]["metrics"] == {}

    def test_node_without_capabilities_excluded(self, extract):
        nodes = {"worker": {"properties": {"image": "nginx"}}}
        assert extract(nodes) == {}

    def test_node_with_unrelated_capabilities_excluded(self, extract):
        nodes = {
            "worker": {
                "capabilities": {"host": {"properties": {"num-cpus": 4}}}
            }
        }
        assert extract(nodes) == {}

    def test_multiple_nodes_mixed(self, extract):
        nodes = {
            "monitored": {
                "capabilities": {
                    "metrics": {"properties": {"raw": [{"name": "cpu"}]}}
                }
            },
            "plain": {"properties": {"image": "nginx"}},
        }
        result = extract(nodes)
        assert "monitored" in result
        assert "plain" not in result

    def test_empty_nodes_returns_empty(self, extract):
        assert extract({}) == {}

    def test_get_monitoring_raises_on_non_sat(self):
        fake = object.__new__(SardouInternal)
        fake.kind = "cdt"
        with pytest.raises(TypeError):
            fake.get_monitoring()


# ---------------------------------------------------------------------------
# Sardou public API (requires puccini-tosca)
# ---------------------------------------------------------------------------


@requires_puccini
@pytest.mark.parametrize("mode", ["path", "dict"])
class TestSardouCDTAPI:
    """Tests for the Sardou class used as a library, not via CLI."""

    @pytest.fixture
    def cloud_overall(self, mode):
        return _load_sardou(CDT_DIR / "cloud-overall.yaml", mode)

    @pytest.fixture
    def cloud_instances(self, mode):
        return _load_sardou(CDT_DIR / "cloud-instances.yaml", mode)

    def test_sardou_raises_on_missing_file(self, mode):
        if mode == "dict":
            pytest.skip("missing-file check only applies to path mode")
        with pytest.raises(FileNotFoundError):
            Sardou("/tmp/definitely_does_not_exist.yaml")

    def test_sardou_instance_has_path(self, cloud_overall, mode):
        if mode == "path":
            assert cloud_overall.path is not None
        else:
            assert cloud_overall.path is None

    def test_kind_cdt_for_capacity_template(self, cloud_overall, mode):
        assert cloud_overall.kind == "cdt"

    def test_get_capacities_returns_dict(self, cloud_overall, mode):
        caps = cloud_overall.get_capacities()
        assert isinstance(caps, dict)
        assert "cloud_flavours" in caps

    def test_get_capacities_raises_on_sat(self, mode):
        """get_capacities() must raise TypeError when called on a SAT."""
        fake = object.__new__(SardouInternal)
        fake.kind = "sat"
        with pytest.raises(TypeError):
            fake.get_capacities()

    def test_get_monitoring_raises_on_cdt(self, mode):
        """get_monitoring() must raise TypeError when called on a CDT."""
        fake = object.__new__(SardouInternal)
        fake.kind = "cdt"
        with pytest.raises(TypeError):
            fake.get_monitoring()

    def test_get_requirements_returns_dict(self, cloud_overall, mode):
        reqs = cloud_overall.get_requirements()
        assert isinstance(reqs, dict)

    def test_get_cluster_returns_valid_json(self, cloud_overall, mode):
        cluster_json = cloud_overall.get_cluster()
        parsed = json.loads(cluster_json)
        assert isinstance(parsed, dict)

    def test_raw_attribute_is_accessible(self, cloud_overall, mode):
        assert hasattr(cloud_overall, "raw")

    def test_cloud_instances_parses(self, cloud_instances, mode):
        assert cloud_instances.kind == "cdt"


@requires_puccini
@pytest.mark.parametrize("mode", ["path", "dict"])
class TestSardouSATAPI:
    """Tests for the Sardou class loaded with a SAT (service application template)."""

    @pytest.fixture
    def bookinfo(self, mode):
        return _load_sardou(SAT_DIR / "BookInfo.yaml", mode)

    def test_is_sat_true(self, bookinfo, mode):
        assert bookinfo.kind == "sat"

    def test_get_requirements_returns_dict(self, bookinfo, mode):
        reqs = bookinfo.get_requirements()
        assert isinstance(reqs, dict)

    def test_get_qos_returns_list(self, bookinfo, mode):
        assert isinstance(bookinfo.get_qos(), list)

    def test_get_monitoring_returns_dict(self, bookinfo, mode):
        monitoring = bookinfo.get_monitoring()
        assert isinstance(monitoring, dict)

    def test_get_capacities_raises_type_error(self, bookinfo, mode):
        with pytest.raises(TypeError):
            bookinfo.get_capacities()

    def test_get_cluster_returns_valid_json(self, bookinfo, mode):
        parsed = json.loads(bookinfo.get_cluster())
        assert isinstance(parsed, dict)

    def test_raw_attribute_accessible(self, bookinfo, mode):
        assert hasattr(bookinfo, "raw")


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@requires_puccini
@pytest.mark.parametrize("mode", ["path", "dict"])
class TestSATTemplateOutput:
    """Verify that SAT templates produce meaningful, non-empty results."""

    @pytest.fixture
    def bookinfo(self, mode):
        return _load_sardou(SAT_DIR / "BookInfo.yaml", mode)

    def test_bookinfo_requirements_non_empty(self, bookinfo, mode):
        reqs = bookinfo.get_requirements()
        assert reqs, "BookInfo SAT should produce non-empty requirements"

    def test_bookinfo_requirements_have_capabilities(self, bookinfo, mode):
        reqs = bookinfo.get_requirements()
        for node_name, entry in reqs.items():
            assert "expression" in entry, (
                f"Requirement entry '{node_name}' should have expression"
            )
            assert entry["expression"], (
                f"Expression for '{node_name}' should be non-empty"
            )

    def test_bookinfo_requirements_have_metadata(self, bookinfo, mode):
        reqs = bookinfo.get_requirements()
        for node_name, entry in reqs.items():
            assert "colocated" in entry, (
                f"Requirement entry '{node_name}' should have colocated"
            )

    def test_bookinfo_colocation_applied(self, bookinfo):
        reqs = bookinfo.get_requirements()
        # details_v1 and productpage_v1 are colocated; only details_v1 should be representative
        has_colocated = any(len(e["colocated"]) > 0 for e in reqs.values())
        assert has_colocated, "At least one node should have colocated peers"

    def test_bookinfo_expressions_are_evaluable(self, bookinfo):
        reqs = bookinfo.get_requirements()
        for node_name, entry in reqs.items():
            fn = eval(entry["expression"])
            assert callable(fn), (
                f"Expression for '{node_name}' should be a callable lambda"
            )


@requires_puccini
@pytest.mark.parametrize("mode", ["path", "dict"])
class TestCDTTemplateOutput:
    """Verify that CDT templates produce meaningful, non-empty capacities."""

    @pytest.fixture(params=["cloud-overall.yaml", "cloud-instances.yaml"])
    def cdt(self, request, mode):
        return _load_sardou(CDT_DIR / request.param, mode)

    @pytest.fixture()
    def edge_cdt(self, mode):
        return _load_sardou(CDT_DIR / "edge.yaml", mode)

    def test_capacities_non_empty(self, cdt, mode):
        caps = cdt.get_capacities()
        assert caps, "CDT should produce non-empty capacities"

    def test_capacities_have_cloud_flavours(self, cdt, mode):
        caps = cdt.get_capacities()
        assert "cloud_flavours" in caps
        assert caps["cloud_flavours"], "CDT cloud_flavours dict should be non-empty"

    def test_edge_capacities_have_edge_instances(self, edge_cdt, mode):
        caps = edge_cdt.get_capacities()
        assert "edge_instances" in caps
        assert caps["edge_instances"], "CDT edge_instances dict should be non-empty"

    def test_flavour_entries_have_properties(self, cdt, mode):
        caps = cdt.get_capacities()
        for flavour_name, flavour in caps["cloud_flavours"].items():
            assert flavour, (
                f"Flavour '{flavour_name}' should have at least one capability"
            )

    def test_edge_flavour_entries_have_properties(self, edge_cdt, mode):
        caps = edge_cdt.get_capacities()
        for flavour_name, edge in caps["edge_instances"].items():
            assert edge, f"Edge '{flavour_name}' should have at least one capability"

    def test_cloud_flavour_capacity(self, cdt, mode):
        caps = cdt.get_capacities()
        assert caps.get("cloud_capacity_flavour") or caps.get("cloud_capacity_raw"), (
            "Cloud CDT should have a cloud_capacity_"
        )

    def test_edge_flavour_capacity_is_empty(self, edge_cdt, mode):
        caps = edge_cdt.get_capacities()
        assert not caps.get("cloud_capacity_flavour"), (
            "Edge CDT should not have cloud_capacity_flavour"
        )


OFFER_DIR = Path(__file__).parent / "templates" / "offer"

_rdt_scenarios = [
    ("cloud-instances", "cloud-instances.yaml", "offer-cloud.yaml"),
    ("cloud-overall", "cloud-overall.yaml", "offer-cloud.yaml"),
    ("edge", "edge.yaml", "offer-edge.yaml"),
]


@requires_puccini
@pytest.mark.parametrize(
    "cdt_file, offer_file",
    [(c, o) for _, c, o in _rdt_scenarios],
    ids=[name for name, _, _ in _rdt_scenarios],
)
class TestSardouRDTAPI:
    """Tests for RDT generation from a CDT and a selected offer."""

    @pytest.fixture
    def cdt(self, cdt_file):
        return Sardou(str(CDT_DIR / cdt_file))

    @pytest.fixture
    def offer(self, offer_file):
        with open(OFFER_DIR / offer_file) as f:
            return _yaml.load(f)

    @pytest.fixture
    def rdt(self, cdt, offer, tmp_path):
        out = str(tmp_path / "rdt.yaml")
        cdt.generate_rdt(offer, out)
        return Sardou(out)

    def test_rdt_has_one_node_per_offer_entry(self, rdt, offer):
        nodes = rdt.nodeTemplates._to_dict()
        assert set(nodes.keys()) == set(_get_offer_keys(offer))

    def test_rdt_nodes_keyed_by_offer_key(self, rdt, offer):
        nodes = rdt.nodeTemplates._to_dict()
        for key in _get_offer_keys(offer):
            assert key in nodes

    def test_rdt_node_has_count(self, rdt):
        nodes = rdt.nodeTemplates._to_dict()
        for node in nodes.values():
            assert "count" in node

    def test_duplicate_res_id_produces_separate_nodes(self, rdt, offer):
        """Nodes with same res_id but different keys should be separate."""
        nodes = rdt.nodeTemplates._to_dict()
        keys = _get_offer_keys(offer)
        for key in keys:
            assert key in nodes

    def test_rdt_node_inherits_cdt_type(self, cdt, rdt, offer):
        cdt_nodes = cdt.nodeTemplates._to_dict()
        rdt_nodes = rdt.nodeTemplates._to_dict()
        for key in _get_offer_keys(offer):
            res_id = _get_offer_res_id(offer, key)
            cdt_types = set(cdt_nodes[res_id]["types"])
            rdt_types = set(rdt_nodes[key]["types"])
            assert cdt_types.issubset(rdt_types)

    def test_rdt_metadata_has_kind(self, rdt):
        assert rdt.metadata._to_dict().get("kind") == "RDT"

    def test_invalid_res_id_raises(self, cdt, offer_file):  # noqa: ARG002
        # Simulate new-offer.json structure with invalid res_id
        bad_offer = {
            "details_v1": {
                "bad-resource": {"ids": {"res_id": "nonexistent"}, "count": 1}
            }
        }
        with pytest.raises(KeyError):
            cdt.generate_rdt(bad_offer, "/dev/null")

    def test_offer_properties_merged_into_node(self, cdt, offer_file, tmp_path):  # noqa: ARG002
        """Properties from offer are added to the RDT node."""
        res_id = next(iter(cdt.nodeTemplates._to_dict()))
        offer = {
            "ms1": {
                "offer-key": {
                    "ids": {"res_id": res_id},
                    "count": 1,
                    "properties": {
                        "ingress-rules": [{"from": 80, "to": 80, "protocol": "TCP"}]
                    },
                }
            }
        }
        out = str(tmp_path / "rdt.yaml")
        cdt.generate_rdt(offer, out)
        rdt = Sardou(out)
        props = rdt.nodeTemplates._to_dict()["offer-key"]["properties"]
        assert "ingress-rules" in props

    def test_offer_properties_do_not_overwrite_cdt_properties(self, cdt, offer_file, tmp_path):  # noqa: ARG002
        """Existing CDT node properties are not overwritten by offer properties."""
        cdt_nodes = cdt.nodeTemplates._to_dict()
        res_id = next(
            k for k, v in cdt_nodes.items() if v.get("properties")
        )
        existing_prop = next(iter(cdt_nodes[res_id]["properties"]))
        offer = {
            "ms1": {
                "offer-key": {
                    "ids": {"res_id": res_id},
                    "count": 1,
                    "properties": {existing_prop: "OVERWRITTEN"},
                }
            }
        }
        out = str(tmp_path / "rdt.yaml")
        cdt.generate_rdt(offer, out)
        rdt = Sardou(out)
        props = rdt.nodeTemplates._to_dict()["offer-key"]["properties"]
        assert props[existing_prop] != "OVERWRITTEN"

    def test_get_cluster_returns_valid_json(self, rdt):
        cluster_json = rdt.get_cluster()
        parsed = json.loads(cluster_json)
        assert isinstance(parsed, dict)


# Helper functions for offer key extraction
def _get_offer_keys(offer):
    if isinstance(offer, list):
        offer = offer[0]
    if all(isinstance(v, dict) and "res_id" in v for v in offer.values()):
        return list(offer.keys())
    keys = []
    for ms_data in offer.values():
        if isinstance(ms_data, dict):
            for offer_key, offer_data in ms_data.items():
                if isinstance(offer_data, dict) and "ids" in offer_data:
                    keys.append(offer_key)
    return keys


def _get_offer_res_id(offer, key):
    if isinstance(offer, list):
        offer = offer[0]
    if key in offer and "res_id" in offer[key]:
        return offer[key]["res_id"]
    for ms_data in offer.values():
        if isinstance(ms_data, dict):
            if key in ms_data and "ids" in ms_data[key]:
                return ms_data[key]["ids"].get("res_id")
    return None
