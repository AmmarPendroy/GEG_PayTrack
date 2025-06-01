import streamlit as st
import hashlib
import uuid
from datetime import datetime

# === ROLE Constants ===
ROLES = ["Superadmin", "HQ Admin", "HQ Accountant", "Site PM", "Site Accountant"]

# === Login-related functions ===

def hash_password(password: str) -> str:
    """Hash the password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password: str, stored_hash: str) -> bool:
    """Verify input password against stored hash."""
    return hash_password(input_password) == stored_hash

def get_current_user():
    """Returns current user object from session, or None if not logged in."""
    return st.session_state.get("user", None)

def logout():
    """Clear session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# === UUID + timestamp helpers ===

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_timestamp() -> str:
    return datetime.utcnow().isoformat()
