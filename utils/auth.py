import streamlit as st
import psycopg2
import hashlib
from utils.db_connection import get_db_connection

# ---------------------------------------
# Password Hashing (SHA-256)
# ---------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------------------------------
# Authenticate User
# ---------------------------------------
def authenticate_user(username: str, password: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, hashed_password, role, assigned_projects
        FROM users
        WHERE username = %s
    """, (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and user[2] == hash_password(password):
        return {
            "user_id": user[0],
            "username": user[1],
            "role": user[3],
            "assigned_projects": user[4]
        }
    return None

# ---------------------------------------
# Get Current User from Session
# ---------------------------------------
def get_current_user():
    return st.session_state.get("user")

# ---------------------------------------
# Role Check Utility
# ---------------------------------------
def check_role(allowed_roles: list) -> bool:
    user = get_current_user()
    if not user:
        return False
    return user["role"] in allowed_roles

# ---------------------------------------
# Check if user has access to a specific project
# ---------------------------------------
def has_project_access(project_id: str) -> bool:
    user = get_current_user()
    if not user:
        return False
    if user["role"] in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        return True
    return project_id in user["assigned_projects"]
