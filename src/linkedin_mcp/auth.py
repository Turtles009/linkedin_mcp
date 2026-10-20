from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

import httpx
from pydantic import (
    AwareDatetime,
    BaseModel,
    SecretStr,
    field_serializer,
)

from linkedin_mcp.config import Settings

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
SCOPES = ("openid", "profile", "w_member_social")
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def build_authorization_url(settings: Settings, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": str(settings.redirect_uri),
        "state": state,
        "scope": " ".join(SCOPES),
    }

    return AUTHORIZATION_URL + "?" + urlencode(params, quote_via=quote)


class CallbackServer(HTTPServer):
    result: dict | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_error(404, "Invalid URL")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"You can close this tab")
        assert isinstance(self.server, CallbackServer)
        self.server.result = parse_qs(parsed.query)


class TokenData(BaseModel):
    access_token: SecretStr
    expires_at: AwareDatetime

    @field_serializer("access_token", when_used="json")
    def reveal_token(self, v: SecretStr) -> str:
        return v.get_secret_value()


def wait_for_callback(port: int) -> dict:
    with CallbackServer(("localhost", port), CallbackHandler) as server:
        server.result = None
        while server.result is None:
            server.handle_request()
        return server.result


def exchange_code_for_token(settings: Settings, code: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret.get_secret_value(),
        "redirect_uri": str(settings.redirect_uri),
    }

    response = httpx.post(
        TOKEN_URL,
        data=payload,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def save_token(path: Path, token_response: dict, now: datetime) -> None:
    token = TokenData(
        access_token=token_response["access_token"],
        expires_at=now + timedelta(seconds=int(token_response["expires_in"])),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.model_dump_json())


def load_token(path: Path) -> TokenData:
    text = path.read_text()
    model = TokenData.model_validate_json(text)

    return model
