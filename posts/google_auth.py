"""
google_auth.py
==============
Standalone service module for verifying Google ID tokens.

Why not django-allauth?
  django-allauth requires django.contrib.sites, email backends, and a
  browser-based redirect flow.  For a pure REST API that receives a token
  minted by a mobile app or SPA, the simpler approach is to verify the
  token directly against Google's tokeninfo endpoint — no extra apps,
  no extra migrations, no browser redirects.

Usage (inside a view):
    from posts.google_auth import verify_google_token, GoogleAuthError

    try:
        payload = verify_google_token(id_token_string)
    except GoogleAuthError as e:
        return Response({'error': str(e)}, status=400)

    google_id   = payload['sub']
    email       = payload['email']
    name        = payload.get('name', '')
    picture_url = payload.get('picture', '')
"""

import urllib.request
import urllib.error
import json

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleAuthError(Exception):
    """Raised when a Google ID token cannot be verified."""
    pass


def verify_google_token(id_token: str) -> dict:
    """
    Verify a Google ID token by calling Google's tokeninfo endpoint.

    Args:
        id_token: The raw ID token string sent by the client.

    Returns:
        dict with at minimum: sub, email, email_verified, aud, exp
        May also include: name, picture, given_name, family_name

    Raises:
        GoogleAuthError: If the token is invalid, expired, or the request fails.

    Notes:
        - This makes a synchronous HTTP request to Google. For high-traffic
          production use, consider caching public keys and verifying locally
          with google-auth library (google.oauth2.id_token.verify_oauth2_token).
        - The 'aud' claim should match your Google OAuth Client ID.
          Add GOOGLE_CLIENT_ID to settings.py and uncomment the check below.
    """
    if not id_token or not isinstance(id_token, str):
        raise GoogleAuthError("No ID token provided.")

    url = f"{GOOGLE_TOKENINFO_URL}?id_token={id_token}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise GoogleAuthError(f"Google rejected the token: {body}")
    except urllib.error.URLError as e:
        raise GoogleAuthError(f"Could not reach Google to verify token: {e.reason}")
    except json.JSONDecodeError:
        raise GoogleAuthError("Unexpected response format from Google.")

    # Validate required fields are present
    if 'sub' not in payload:
        raise GoogleAuthError("Token payload missing 'sub' (Google user ID).")
    if 'email' not in payload:
        raise GoogleAuthError("Token payload missing 'email'.")
    if payload.get('email_verified') not in (True, 'true'):
        raise GoogleAuthError("Google email address is not verified.")

    # Optional: enforce your app's Client ID
    # from django.conf import settings
    # if payload.get('aud') != settings.GOOGLE_CLIENT_ID:
    #     raise GoogleAuthError("Token was not issued for this application.")

    return payload  