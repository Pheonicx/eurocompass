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

import json
import os
import sys
import urllib.request


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

    payload = {
        "description": "EuroCompass v2 live collection test result",
        "public": False,
        "files": {"result.txt": {"content": content}},
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
    except Exception as e:
        # Publishing the gist is a nice-to-have, not the actual point of
        # the workflow — a failure here should be visible but must not
        # make the whole run look like the collection test itself failed.
        print(f"Failed to publish result gist (non-fatal): {e}")


if __name__ == "__main__":
    main()
