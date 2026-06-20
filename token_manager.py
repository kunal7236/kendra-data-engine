import requests

TOKEN_ENDPOINT = "https://janaushadhi.gov.in:8443/auth/generateGuestToken"

def fetch_janaushadhi_token():
    """Fetch fresh Janaushadhi guest token from API"""
    try:
        response = requests.get(TOKEN_ENDPOINT, verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("responseBody")
        if not token:
            raise ValueError("No token in response")
        print("✓ Fresh token generated successfully")
        return token
    except Exception as e:
        print(f"❌ Failed to fetch token: {e}")
        raise
