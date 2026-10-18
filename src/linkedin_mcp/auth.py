from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlencode, urlparse

from linkedin_mcp.config import Settings

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
SCOPES = ("openid", "profile", "w_member_social")


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


def wait_for_callback(port: int) -> dict:
    with CallbackServer(("localhost", port), CallbackHandler) as server:
        server.result = None
        while server.result is None:
            server.handle_request()
        return server.result
