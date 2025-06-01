import psycopg2
import streamlit as st
from utils.db_connection import get_db_connection
from datetime import datetime

# ---------------------------------------
# Authenticate User (used in login)
# ---------------------------------------
def authenticate_user(username: str, password: str):
    import hashlib
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    try:
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

        if user and user[2] == hashed_password:
            return {
                "user_id": user[0],
                "username": user[1],
                "role": user[3],
                "assigned_projects": user[4]
            }
        return None

    except Exception as e:
        st.error(f"Auth error: {e}")
        return None
