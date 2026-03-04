"""Unit tests for package internals that don't require puccini-tosca."""

import pytest

# ---------------------------------------------------------------------------
# Import / metadata
# ---------------------------------------------------------------------------


class TestImport:
    def test_sardou_is_importable(self):
        import sardou  # noqa: F401

    def test_version_is_a_string(self):
        import sardou

        assert isinstance(sardou.__version__, str)

    def test_version_not_unknown(self):
        import sardou

        assert sardou.__version__ != "unknown"

    def test_sardou_class_exported(self):
        from sardou import Sardou

        assert callable(Sardou)


# ---------------------------------------------------------------------------
# DotDict
# ---------------------------------------------------------------------------


class TestDotDict:
    @pytest.fixture
    def DotDict(self):
        from sardou.sardou import DotDict

        return DotDict

    def test_attribute_access(self, DotDict):
        d = DotDict(foo="bar")
        assert d.foo == "bar"

    def test_nested_dict_becomes_dotdict(self, DotDict):
        d = DotDict(outer={"inner": 42})
        assert isinstance(d.outer, DotDict)
        assert d.outer.inner == 42

    def test_list_of_dicts_converted(self, DotDict):
        d = DotDict(items=[{"x": 1}, {"x": 2}])
        assert isinstance(d.items[0], DotDict)
        assert d.items[1].x == 2

    def test_contains(self, DotDict):
        d = DotDict(a=1)
        assert "a" in d
        assert "b" not in d

    def test_getitem(self, DotDict):
        d = DotDict(key="value")
        assert d["key"] == "value"

    def test_setitem(self, DotDict):
        d = DotDict(key="old")
        d["key"] = "new"
        assert d.key == "new"

    def test_delitem(self, DotDict):
        d = DotDict(key="value")
        del d["key"]
        assert "key" not in d

    def test_to_dict_roundtrip(self, DotDict):
        original = {"a": 1, "b": {"c": 2}, "d": [{"e": 3}]}
        d = DotDict(**original)
        assert d._to_dict() == original

    def test_to_json(self, DotDict):
        import json

        d = DotDict(x=1)
        parsed = json.loads(d._to_json())
        assert parsed == {"x": 1}


# ---------------------------------------------------------------------------
# prevalidate
# ---------------------------------------------------------------------------


class TestPrevalidate:
    @pytest.fixture
    def prevalidate(self):
        from sardou.validation import prevalidate

        return prevalidate

    def test_nonexistent_file_returns_false(self, prevalidate, tmp_path):
        result = prevalidate(tmp_path / "missing.yaml")
        assert result is False

    def test_empty_file_returns_false(self, prevalidate, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert prevalidate(f) is False

    def test_valid_minimal_template_returns_data(self, prevalidate, tmp_path):
        """prevalidate should return the parsed data for a structurally valid file."""
        f = tmp_path / "minimal.yaml"
        f.write_text(
            "tosca_definitions_version: tosca_2_0\n"
            "imports: []\n"
            "service_template:\n"
            "  node_templates: {}\n"
        )
        result = prevalidate(f)
        assert result is not False
        assert "service_template" in result

    def test_profile_key_renamed_to_url(self, prevalidate, tmp_path):
        """prevalidate should rewrite 'profile' import keys to 'url'."""
        f = tmp_path / "profile_import.yaml"
        f.write_text(
            "tosca_definitions_version: tosca_2_0\n"
            "imports:\n"
            "  - profile: some.profile\n"
            "service_template:\n"
            "  node_templates: {}\n"
        )
        result = prevalidate(f)
        assert result is not False
        assert result["imports"][0].get("url") == "some.profile"
        assert "profile" not in result["imports"][0]
