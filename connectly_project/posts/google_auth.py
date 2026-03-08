import urllib.request
import urllib.error
import json

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleAuthError(Exception):
    pass

def verify_google_token(id_token: str) -> dict:
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

    if 'sub' not in payload:
        raise GoogleAuthError("Token payload missing 'sub' (Google user ID).")
    if 'email' not in payload:
        raise GoogleAuthError("Token payload missing 'email'.")
    if payload.get('email_verified') not in (True, 'true'):
        raise GoogleAuthError("Google email address is not verified.")

    return payload  