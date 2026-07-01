import requests


DEFAULT_TIMEOUT = 15

session = requests.Session()


def get(url, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

    try:
        response = session.get(
            url,
            timeout=timeout,
            **kwargs
        )

        response.raise_for_status()
        return response

    except requests.RequestException as e:
        print(f"[HTTP GET ERROR] {e}")
        return None


def post(url, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

    try:
        response = session.post(
            url,
            timeout=timeout,
            **kwargs
        )

        response.raise_for_status()
        return response

    except requests.RequestException as e:
        print(f"[HTTP POST ERROR] {e}")
        return None
