"""Voximplant Management API client (JWT service-account auth).

Never logs credential JSON, phone numbers, or callback tokens.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

HttpFn = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]

API_BASE = "https://api.voximplant.com/platform_api"


def _b64url(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def encode_rs256_jwt(payload: dict[str, Any], private_key_pem: str, kid: str) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    ).encode("ascii")
    key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return signing_input.decode("ascii") + "." + _b64url(signature)


def load_credentials(source: str | Path) -> dict[str, Any]:
    text = str(source).strip()
    if text.startswith("{"):
        data = json.loads(text)
    else:
        data = json.loads(Path(text).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid Voximplant credentials")
    for required in ("account_id", "key_id", "private_key"):
        if required not in data:
            raise ValueError("invalid Voximplant credentials")
    return data


def _default_http(url: str, fields: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(
        {key: value for key, value in fields.items() if value is not None}
    ).encode()
    request = urllib.request.Request(url, data=encoded, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": {"msg": "http_error", "code": exc.code}}
        return parsed


class VoximplantAPI:
    def __init__(
        self,
        credentials: dict[str, Any],
        *,
        http: HttpFn | None = None,
    ) -> None:
        self._credentials = credentials
        self._http = http or _default_http

    def _token(self) -> str:
        now = int(time.time())
        return encode_rs256_jwt(
            {
                "iss": str(self._credentials["account_id"]),
                "iat": now - 5,
                "exp": now + 24,
            },
            str(self._credentials["private_key"]),
            str(self._credentials["key_id"]),
        )

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        url = f"{API_BASE}/{method}/"
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        return self._http(url, params, headers)

    @property
    def account_id(self) -> str:
        return str(self._credentials["account_id"])

    @property
    def key_id(self) -> str:
        return str(self._credentials["key_id"])
