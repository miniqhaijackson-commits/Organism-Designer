import secrets
from backend import db

def register_device(name: str, type: str, capabilities: list) -> str:
    """
    Registers a new device and returns a unique token for it.
    """
    token = secrets.token_urlsafe(32)
    db.add_device(name, type, token, capabilities)
    return token

def authenticate_device(token: str) -> bool:
    """
    Authenticates a device using its token.
    """
    return db.verify_device(token)
