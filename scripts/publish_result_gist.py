"""
scripts/publish_result_gist.py

Publishes a text file's content to a private (secret) GitHub Gist, using
a token passed via the GIST_TOKEN environment variable.

Exists specifically to work around a real limitation: GitHub Actions'
full run-log content is served from Azure Blob Storage, not GitHub's own
API — a domain outside the small, deliberately restricted set Claude's
sandbox can reach. Gists, by contrast, are readable directly through
api.github.com, which is reachable — so publishing results here lets
Claude check a run's outcome directly, without needing a human to
copy-paste log output.

Usage:
    GIST_TOKEN=... python scripts/publish_result_gist.py <path-to-log-file>
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request

# Where collectors/city.py saves diagnostics on failure, if it does.
CITY_DIAGNOSTIC_DIR = "/tmp/city_diagnostics"

# Gist files are text-only and this keeps individual files a reasonable
# size to fetch back — truncate anything larger rather than fail outright.
MAX_FILE_CHARS = 300_000

# The screenshot has no natural size cap the way text does (a full-page
# screenshot of an unusually tall page could be several MB before even
# base64 inflation) — skip it entirely if it would blow past a sane
# limit, rather than risk the whole gist payload failing and losing
# even the basic result.txt summary along with it.
MAX_SCREENSHOT_BASE64_CHARS = 3_000_000  # ~2.2MB of raw screenshot data


def _read_truncated(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n\n...(truncated)"
    return content


def _collect_city_diagnostic_files() -> dict:
    """
    Picks up City's diagnostic files if collectors/city.py saved any
    (only happens on an actual failure) — a screenshot (base64-encoded,
    since Gist files are text-only), the page HTML, and any browser
    console messages. Silently returns nothing if City didn't fail this
    run, since there'd be nothing to pick up.
    """
    files = {}

    screenshot_path = f"{CITY_DIAGNOSTIC_DIR}/screenshot.png"
    if os.path.exists(screenshot_path):
        with open(screenshot_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        if len(encoded) > MAX_SCREENSHOT_BASE64_CHARS:
            print(
                f"CITY DIAGNOSTIC: screenshot too large to publish "
                f"({len(encoded)} base64 chars) — skipping it, keeping the rest"
            )
        else:
            files["city_screenshot_base64.txt"] = {"content": encoded}

    html = _read_truncated(f"{CITY_DIAGNOSTIC_DIR}/page.html")
    if html is not None:
        files["city_page.html"] = {"content": html}

    console_log = _read_truncated(f"{CITY_DIAGNOSTIC_DIR}/console.txt")
    if console_log is not None:
        files["city_console.txt"] = {"content": console_log}

    return files


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: publish_result_gist.py <path-to-log-file>")
        sys.exit(1)

    log_path = sys.argv[1]
    token = os.environ.get("GIST_TOKEN")

    if not token:
        print("GIST_TOKEN environment variable not set — skipping gist publish.")
        return

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if not content.strip():
        content = "(no output captured)"

    files = {"result.txt": {"content": content}}
    files.update(_collect_city_diagnostic_files())

    if not _publish_gist(files, token):
        # Whatever went wrong with the full payload, the basic summary
        # is the one thing that must get through if at all possible —
        # retry with just that, dropping the (larger, less essential)
        # diagnostic extras.
        if len(files) > 1:
            print("Retrying with just result.txt (dropping diagnostic extras)...")
            _publish_gist({"result.txt": {"content": content}}, token)


def _publish_gist(files: dict, token: str) -> bool:
    """Returns True on success, False on failure (never raises — a
    failure here must not make the run look like the actual collection
    test itself failed)."""
    payload = {
        "description": "EuroCompass v2 live collection test result",
        "public": False,
        "files": files,
    }

    request = urllib.request.Request(
        "https://api.github.com/gists",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "eurocompass-test-workflow",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
        print(f"Published result gist: {result['html_url']}")
        print(f"Gist ID: {result['id']}")
        return True
    except Exception as e:
        print(f"Failed to publish result gist (non-fatal): {e}")
        return False


if __name__ == "__main__":
    main()
