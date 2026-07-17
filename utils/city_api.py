from utils import http_client
import base64
import json
import os
import time
from datetime import datetime

API_BASE_URL = "https://citybankplc.com/admin/api/v1"
AUTH_URL = f"{API_BASE_URL}/auth-token"
EXCHANGE_RATES_URL = f"{API_BASE_URL}/exchange-rates"

AUTH_KEY = b"YGRAq4E7OmSUtZmPwxOnGhgNjF7kmkFO"
AUTH_USER = "api-user"
AUTH_PASSWORD = "a@i_u$e4_*b1"

TIMEOUT = 20
_last_api_error = None

S_BOX = (
    0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,
    0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
    0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,
    0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
    0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,
    0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
    0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,
    0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
    0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,
    0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
    0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,
    0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
    0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,
    0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
    0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,
    0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
    0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,
    0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
    0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,
    0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
    0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,
    0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
    0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,
    0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
    0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,
    0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
    0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,
    0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
    0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,
    0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
    0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,
    0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16,
)

RCON = (0x01,0x02,0x04,0x08,0x10,0x20,0x40)


def _xor_bytes(left, right):
    return bytes(a ^ b for a, b in zip(left, right))


def _pad(data):
    pad = 16 - (len(data) % 16)
    return data + bytes([pad]) * pad


def _sub_word(word):
    return bytes(S_BOX[b] for b in word)


def _rot_word(word):
    return word[1:] + word[:1]


def _expand_key(key):
    words = [key[i:i + 4] for i in range(0, len(key), 4)]

    for i in range(8, 60):
        temp = words[i - 1]

        if i % 8 == 0:
            sw = _sub_word(_rot_word(temp))
            temp = bytes([sw[0] ^ RCON[(i // 8) - 1], *sw[1:]])

        elif i % 8 == 4:
            temp = _sub_word(temp)

        words.append(_xor_bytes(words[i - 8], temp))

    return [b"".join(words[i:i + 4]) for i in range(0, len(words), 4)]


def _add_round_key(state, key):
    for i, b in enumerate(key):
        state[i] ^= b


def _sub_bytes(state):
    for i, b in enumerate(state):
        state[i] = S_BOX[b]


def _shift_rows(state):
    state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
    state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
    state[3], state[7], state[11], state[15] = state[15], state[3], state[7], state[11]


def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF


def _mix_single_column(state, i):
    c = state[i:i + 4]
    t = c[0] ^ c[1] ^ c[2] ^ c[3]
    u = c[0]

    state[i] ^= t ^ _xtime(c[0] ^ c[1])
    state[i + 1] ^= t ^ _xtime(c[1] ^ c[2])
    state[i + 2] ^= t ^ _xtime(c[2] ^ c[3])
    state[i + 3] ^= t ^ _xtime(c[3] ^ u)


def _mix_columns(state):
    for i in range(0, 16, 4):
        _mix_single_column(state, i)


def _encrypt_block(block, keys):
    state = bytearray(block)

    _add_round_key(state, keys[0])

    for r in range(1, 14):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, keys[r])

    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, keys[14])

    return bytes(state)


def _encrypt_aes_256_cbc(data, key, iv):
    keys = _expand_key(key)

    previous = iv
    output = []

    padded = _pad(data)

    for i in range(0, len(padded), 16):
        block = padded[i:i + 16]
        block = _xor_bytes(block, previous)
        cipher = _encrypt_block(block, keys)
        output.append(cipher)
        previous = cipher

    return b"".join(output)


def _build_auth_param():
    payload = {
        "user": AUTH_USER,
        "password": AUTH_PASSWORD,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "uuid": f"{int(time.time()*1000)}{os.urandom(6).hex()}",
    }

    plaintext = json.dumps(payload, separators=(",", ":")).encode()

    iv = os.urandom(16)

    encrypted = _encrypt_aes_256_cbc(
        plaintext,
        AUTH_KEY,
        iv,
    )

    return (
        base64.b64encode(iv).decode()
        + ":"
        + base64.b64encode(encrypted).decode()
    )


def _get_token():
    global _last_api_error

    response = http_client.post(
        AUTH_URL,
        json={"param": _build_auth_param()},
        timeout=TIMEOUT,
    )

    if response is None:
        _last_api_error = "Authentication request failed."
        return None

    token = (
        response.json()
        .get("data", {})
        .get("access_token")
    )

    if not token:
        _last_api_error = "Authentication token missing."
        return None

    return token


def get_exchange_rates():
    global _last_api_error

    _last_api_error = None

    token = _get_token()

    if not token:
        return None

    response = http_client.post(
        EXCHANGE_RATES_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        json={},
        timeout=TIMEOUT,
    )

    if response is None:
        _last_api_error = "Exchange rate request failed."
        return None

    data = (
        response.json()
        .get("data", {})
        .get("forex_rates_data", [])
    )

    if not data:
        _last_api_error = "No exchange rates returned."
        return None

    return data

def get_last_api_error():
    return _last_api_error