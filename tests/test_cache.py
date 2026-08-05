"""Tests for sardou.cache — ETag-based HTTP cache."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

import pytest

from sardou.cache import (
    DEFAULT_CACHE_DIR,
    _cached_path_for_url,
    fetch,
    resolve_imports,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ETAG = '"test-etag-123"'
BODY = b"tosca_definitions_version: tosca_2_0\n"


class _Handler(BaseHTTPRequestHandler):
    """Tiny HTTP handler that supports ETag / If-None-Match."""

    body = BODY
    etag = ETAG

    def do_GET(self):
        inm = self.headers.get("If-None-Match")
        if inm and inm == self.etag:
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("ETag", self.etag)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):
        pass  # suppress noisy output


@pytest.fixture()
def local_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


# ---------------------------------------------------------------------------
# fetch()
# ---------------------------------------------------------------------------


class TestFetch:
    def test_first_fetch_downloads(self, local_server, tmp_path):
        url = f"{local_server}/profile.yaml"
        path = fetch(url, cache_dir=tmp_path)
        assert path.exists()
        assert path.read_bytes() == BODY

    def test_etag_stored(self, local_server, tmp_path):
        url = f"{local_server}/profile.yaml"
        path = fetch(url, cache_dir=tmp_path)
        meta = json.loads(path.with_suffix(".yaml.meta").read_text())
        assert meta["etag"] == ETAG

    def test_second_fetch_uses_304(self, local_server, tmp_path):
        url = f"{local_server}/profile.yaml"
        fetch(url, cache_dir=tmp_path)
        # Second fetch — server returns 304, cached file unchanged
        path = fetch(url, cache_dir=tmp_path)
        assert path.read_bytes() == BODY

    def test_network_error_falls_back_to_cache(self, tmp_path):
        url = "http://127.0.0.1:1/unreachable.yaml"
        cached = _cached_path_for_url(tmp_path, url)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(BODY)

        path = fetch(url, cache_dir=tmp_path)
        assert path.read_bytes() == BODY

    def test_network_error_no_cache_returns_none(self, tmp_path):
        url = "http://127.0.0.1:1/unreachable.yaml"
        assert fetch(url, cache_dir=tmp_path) is None


# ---------------------------------------------------------------------------
# resolve_imports()
# ---------------------------------------------------------------------------


class TestResolveImports:
    def test_no_imports_unchanged(self, tmp_path):
        data = {"tosca_definitions_version": "tosca_2_0"}
        result = resolve_imports(data, cache_dir=tmp_path)
        assert result is data

    def test_local_import_not_fetched(self, tmp_path):
        data = {"imports": [{"url": "/some/local/file.yaml"}]}
        resolve_imports(data, cache_dir=tmp_path)
        assert data["imports"][0]["url"] == "/some/local/file.yaml"

    def test_remote_import_rewritten(self, local_server, tmp_path):
        url = f"{local_server}/profile.yaml"
        data = {"imports": [{"url": url}]}
        resolve_imports(data, cache_dir=tmp_path)
        assert data["imports"][0]["url"].startswith(str(tmp_path))
        assert Path(data["imports"][0]["url"]).exists()

    def test_duplicate_url_not_fetched_twice(self, local_server, tmp_path):
        url = f"{local_server}/profile.yaml"
        data = {"imports": [{"url": url}, {"url": url}]}
        with patch("sardou.cache.fetch", wraps=fetch) as mock_fetch:
            resolve_imports(data, cache_dir=tmp_path)
            assert mock_fetch.call_count == 1

    def test_default_cache_dir(self):
        assert DEFAULT_CACHE_DIR == Path.home() / ".cache" / "sardou"


# ---------------------------------------------------------------------------
# Nested-import revalidation
# ---------------------------------------------------------------------------


class _NestedHandler(BaseHTTPRequestHandler):
    """Serves a fixed parent that imports a mutable child."""

    # /parent.yaml — never changes; imports /child.yaml
    parent_etag = '"parent-1"'
    child_etag = '"child-1"'
    child_body = b"tosca_definitions_version: tosca_2_0\nname: child-v1\n"

    def do_GET(self):
        if self.path == "/parent.yaml":
            etag, body = self.parent_etag, (
                b"tosca_definitions_version: tosca_2_0\n"
                b"imports:\n"
                b"- url: http://%s/child.yaml\n" % self.headers["Host"].encode()
            )
        else:
            etag, body = self.child_etag, self.child_body

        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@pytest.fixture()
def nested_server():
    server = HTTPServer(("127.0.0.1", 0), _NestedHandler)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield server, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_changed_nested_import_is_refetched(nested_server, tmp_path):
    _, base = nested_server
    parent_url = f"{base}/parent.yaml"

    # First resolution caches parent + child (child-v1).
    resolve_imports({"imports": [{"url": parent_url}]}, cache_dir=tmp_path)
    child_cached = _cached_path_for_url(tmp_path, f"{base}/child.yaml")
    assert b"child-v1" in child_cached.read_bytes()

    # The pristine parent must keep its http import, not a rewritten local one.
    parent_cached = _cached_path_for_url(tmp_path, parent_url)
    assert "http://" in parent_cached.read_text()

    # Child changes upstream (new etag + body).
    _NestedHandler.child_etag = '"child-2"'
    _NestedHandler.child_body = b"tosca_definitions_version: tosca_2_0\nname: child-v2\n"

    # Second resolution: parent is unchanged (304) but the child must be
    # revalidated and re-fetched.
    resolve_imports({"imports": [{"url": parent_url}]}, cache_dir=tmp_path)
    assert b"child-v2" in child_cached.read_bytes()
