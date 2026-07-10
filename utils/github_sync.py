import base64
import os

import requests

try:
    import streamlit as st
except ImportError:
    st = None


API = "https://api.github.com"


def get_secret(name):
    """
    Get a secret from environment variables first,
    then Streamlit Secrets.
    """

    value = os.getenv(name)

    if value:
        return value

    if st is not None:
        return st.secrets[name]

    raise RuntimeError(f"Missing secret: {name}")


def upload_file(path_in_repo, content, message):
    """
    Create or update a file in GitHub.
    """

    token = get_secret("GITHUB_TOKEN")
    owner = get_secret("GITHUB_USERNAME")
    repo = get_secret("GITHUB_REPO")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    url = f"{API}/repos/{owner}/{repo}/contents/{path_in_repo}"

    # -----------------------------
    # Get current file information
    # -----------------------------

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    sha = None

    if response.status_code == 200:

        existing = response.json()

        sha = existing["sha"]

        existing_content = base64.b64decode(
            existing["content"]
        ).decode("utf-8")

        # Nothing changed
        if existing_content == content:
            return False

    elif response.status_code != 404:

        print("GitHub GET Error")
        print(response.status_code)
        print(response.text)

        response.raise_for_status()

    payload = {
        "message": message,
        "content": base64.b64encode(
            content.encode("utf-8")
        ).decode("utf-8"),
    }

    if sha:
        payload["sha"] = sha

    # -----------------------------
    # First upload attempt
    # -----------------------------

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    # -----------------------------
    # Retry once if SHA changed
    # -----------------------------

    if response.status_code == 422:

        print("GitHub returned 422. Retrying with latest SHA...")

        latest = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        if latest.status_code == 200:

            payload["sha"] = latest.json()["sha"]

            response = requests.put(
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

    # -----------------------------
    # Final error handling
    # -----------------------------

    if not response.ok:

        print("GitHub API Error")
        print(response.status_code)
        print(response.text)

    response.raise_for_status()

    return True