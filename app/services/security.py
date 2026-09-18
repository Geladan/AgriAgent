"""Webhook security helpers.

Twilio signs every webhook request with an HMAC-SHA1 of the full request
URL plus the sorted POST parameters (concatenated key+value with NO
separators), keyed by your Twilio auth token. The result is base64-encoded
and sent in the X-Twilio-Signature header. Verifying it proves the request
really came from Twilio.

Africa's Talking USSD callbacks do NOT include a signature header — the
recommended protections are HTTPS + restricting the callback to AT's
source IPs in the AT dashboard.
"""
import base64
import hashlib
import hmac

from fastapi import Request


def _public_url(request: Request) -> str:
    """Reconstruct the URL Twilio actually called (works behind proxies)."""
    scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get("X-Forwarded-Host", request.url.netloc)
    return f"{scheme}://{host}{request.url.path}{'?' + request.url.query if request.url.query else ''}"


def verify_twilio_signature(request: Request, form: dict, auth_token: str) -> bool:
    """Verify the X-Twilio-Signature header for the current request.

    Returns True when no auth token is configured (mock mode) so the
    demo keeps working without Twilio credentials.
    """
    if not auth_token:
        return True

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    url = _public_url(request)
    if form:
        url += "".join(f"{k}{v}" for k, v in sorted(form.items()))

    expected = hmac.new(auth_token.encode(), url.encode(), hashlib.sha1).digest()
    try:
        return hmac.compare_digest(expected, base64.b64decode(signature))
    except Exception:  # noqa: BLE001 — malformed header
        return False