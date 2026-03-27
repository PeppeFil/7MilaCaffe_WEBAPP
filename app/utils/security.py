import hmac
import secrets
from urllib.parse import urljoin, urlparse

from flask import Request, session


CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(token: str | None) -> bool:
    session_token = session.get(CSRF_SESSION_KEY)
    if not token or not session_token:
        return False
    return hmac.compare_digest(str(token), str(session_token))


def request_csrf_token(request: Request) -> str | None:
    return request.form.get("csrf_token") or request.headers.get("X-CSRFToken")


def is_safe_redirect_target(target: str | None, host_url: str) -> bool:
    if not target:
        return False

    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))

    return (
        test_url.scheme in {"http", "https"}
        and ref_url.netloc == test_url.netloc
    )
