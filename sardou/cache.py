import json
import logging
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "sardou"

yaml = YAML()
yaml.width = 4096


def _meta_path(cached: Path) -> Path:
    return cached.with_suffix(cached.suffix + ".meta")


def _resolved_path(cached: Path) -> Path:
    """Sibling path holding the import-rewritten copy Puccini reads.

    Kept separate from the pristine cached file so that ``fetch`` can keep
    revalidating against the original upstream bytes via ETag.
    """
    return cached.with_suffix(".resolved" + cached.suffix)


def _cached_path_for_url(cache_dir: Path, url: str) -> Path:
    parsed = urlparse(url)
    return cache_dir / parsed.netloc / parsed.path.lstrip("/")


def fetch(url: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Fetch *url*, returning a local cached path.

    Uses ETag for conditional requests — a 304 reuses the existing
    cached file; a 200 stores the new content and ETag.
    Falls back to the cached copy on network errors.
    """
    cached = _cached_path_for_url(cache_dir, url)
    meta = _meta_path(cached)

    etag = None
    if meta.exists():
        etag = json.loads(meta.read_text()).get("etag")

    req = Request(url)
    if etag and cached.exists():
        req.add_header("If-None-Match", etag)

    try:
        resp = urlopen(req, timeout=10)
        # 200 — new or updated content
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(resp.read())
        new_etag = resp.headers.get("ETag")
        if new_etag:
            meta.write_text(json.dumps({"etag": new_etag}))
        logger.debug("Cached (fresh): %s", url)
    except URLError as exc:
        if hasattr(exc, "code") and exc.code == 304:
            logger.debug("Cached (not modified): %s", url)
        elif cached.exists():
            logger.warning("Network error fetching %s — using cached copy", url)
        else:
            logger.warning("Failed to fetch %s — skipping cache", url)
            return None

    return cached


def resolve_imports(
    data: dict, cache_dir: Path = DEFAULT_CACHE_DIR, _seen: set | None = None
) -> dict:
    """Rewrite remote URLs in *imports* to local cached paths, recursively."""
    if _seen is None:
        _seen = set()

    for imp in data.get("imports", []):
        if not isinstance(imp, dict):
            continue

        url = imp.get("url", "")
        if not url.startswith(("http://", "https://")):
            continue

        if url in _seen:
            cached = _cached_path_for_url(cache_dir, url)
            resolved = _resolved_path(cached)
            imp["url"] = str(resolved if resolved.exists() else cached)
            continue

        _seen.add(url)
        local = fetch(url, cache_dir)
        if local is None:
            continue

        # Verify the cached file is valid YAML before rewriting the URL.
        # Always read the *pristine* cached copy so its original http(s)
        # imports are revalidated on every call.
        with local.open("r") as f:
            nested = yaml.load(f)
        if not isinstance(nested, dict):
            continue

        # Recursively resolve imports inside the nested document. The pristine
        # cached file is never overwritten; the rewritten copy goes to a
        # sibling ".resolved" file which Puccini reads offline.
        if nested.get("imports"):
            resolve_imports(nested, cache_dir, _seen)
            resolved = _resolved_path(local)
            with resolved.open("w") as f:
                yaml.dump(nested, f)
            imp["url"] = str(resolved)
        else:
            imp["url"] = str(local)

    return data
