import time

import requests


DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0

session = requests.Session()


def get(url, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    retries = kwargs.pop("retries", DEFAULT_RETRIES)
    backoff = kwargs.pop("backoff", DEFAULT_BACKOFF)

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = session.get(
                url,
                timeout=timeout,
                **kwargs
            )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(backoff * attempt)

    print(f"[HTTP GET ERROR] {last_error}")
    return None


def post(url, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    retries = kwargs.pop("retries", DEFAULT_RETRIES)
    backoff = kwargs.pop("backoff", DEFAULT_BACKOFF)

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = session.post(
                url,
                timeout=timeout,
                **kwargs
            )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(backoff * attempt)

    print(f"[HTTP POST ERROR] {last_error}")
    return None
