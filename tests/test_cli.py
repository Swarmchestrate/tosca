"""CLI smoke tests """
import subprocess
from pathlib import Path

import pytest
from tests.marks import requires_puccini

CDT_DIR = Path(__file__).parent / "templates" / "cdt"
SAT_DIR = Path(__file__).parent / "templates" / "sat"


def run(*args, **kwargs):
    """Run the sardou CLI and return the CompletedProcess."""
    return subprocess.run(
        ["sardou", *args],
        capture_output=True,
        text=True,
        **kwargs,
    )


class TestHelp:
    def test_help_exits_zero(self):
        result = run("--help")
        assert result.returncode == 0


class TestBadArguments:
    def test_no_args_exits_nonzero(self):
        result = run()
        assert result.returncode != 0

    def test_missing_file_exits_one(self, tmp_path):
        result = run(str(tmp_path / "not_there.yaml"))
        assert result.returncode == 1

    def test_missing_file_prints_error(self, tmp_path):
        result = run(str(tmp_path / "not_there.yaml"))
        assert "exist" in result.stderr.lower() and "error" in result.stderr.lower()


class TestInvalidYaml:
    def test_empty_file_exits_one(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = run(str(f))
        assert result.returncode == 1

    def test_non_yaml_file_exits_one(self, tmp_path):
        f = tmp_path / "junk.yaml"
        f.write_text(":::not valid yaml:::")
        result = run(str(f))
        assert result.returncode == 1


@requires_puccini
class TestCDTTemplates:
    """Smoke-test that each CDT template passes sardou parsing end-to-end."""

    def test_cloud_overall_parses(self):
        result = run(str(CDT_DIR / "cloud-overall.yaml"))
        assert result.returncode == 0, result.stderr

    def test_cloud_instances_parses(self):
        result = run(str(CDT_DIR / "cloud-instances.yaml"))
        assert result.returncode == 0, result.stderr

    def test_edge_parses(self):
        result = run(str(CDT_DIR / "edge.yaml"))
        assert result.returncode == 0, result.stderr


@requires_puccini
class TestSATTemplates:
    """Smoke-test that each SAT template passes sardou parsing end-to-end."""

    def test_bookinfo_parses(self):
        result = run(str(SAT_DIR / "BookInfo.yaml"))
        assert result.returncode == 0, result.stderr

