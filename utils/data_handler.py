import psycopg2
import streamlit as st
from utils.db_connection import get_db_connection
from datetime import datetime

# ---------------------------------------
# Authenticate User
# (Moved here temporarily to match import in login page)
# ---------------------------------------
def authenticate_user(username: str, password: str):
    from utils.auth import hash_password  # local import to avoid circular
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
# Add Contractor
# ---------------------------------------
def add_contractor(name, contact_person=None, contact_email=None, contact_phone=None, address=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contractors (name, contact_person, contact_email, contact_phone, address, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            contact_person,
            contact_email,
            contact_phone,
            address,
            datetime.utcnow(),
            datetime.utcnow()
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding contractor: {e}")
        return False

# ---------------------------------------
# Get All Contractors
# ---------------------------------------
def get_all_contractors():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT name, contact_person, contact_email, contact_phone, address, created_at
            FROM contractors
            ORDER BY created_at DESC
        """)
        contractors = cur.fetchall()
        cur.close()
        conn.close()
        return contractors
    except Exception as e:
        st.error(f"Error loading contractors: {e}")
        return []
