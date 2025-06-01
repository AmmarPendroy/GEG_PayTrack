import psycopg2
import hashlib
import streamlit as st

# Load DB URL securely
DB_URL = st.secrets["DATABASE_URL"]

# ---------------------------------------
# PostgreSQL Connection
# ---------------------------------------
def get_db_connection():
    return psycopg2.connect(DB_URL)

# ---------------------------------------
# Password Hashing
# ---------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------------------------------
# Authenticate User
# ---------------------------------------
def authenticate_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, hashed_password, role
        FROM users
        WHERE username = %s
    """, (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and user[2] == hash_password(password):
        return {
            "id": user[0],
            "username": user[1],
            "role": user[3]
        }
    return None

# ---------------------------------------
# Database Schema Reference (for Dev use)
# ---------------------------------------
DB_SCHEMA = {
    "users": ["id", "username", "hashed_password", "role", "assigned_projects", "created_at", "updated_at"],
    "roles": ["id", "name", "permissions_json", "created_at", "updated_at"],
    "contractors": ["id", "name", "contact_person", "contact_email", "contact_phone", "address", "created_at", "updated_at"],
    "contracts": ["id", "title", "contractor_id", "project_id", "total_amount", "currency", "start_date", "end_date", "description", "created_at", "updated_at"],
    "projects": ["id", "name", "location", "start_date", "end_date", "status", "created_at", "updated_at"],
    "payment_requests": ["id", "contract_id", "requested_amount", "requested_date", "requested_by_user_id", "status", "approved_rejected_date", "approved_rejected_by_user_id", "notes", "created_at", "updated_at"],
    "contractor_payments": ["id", "payment_request_id", "paid_amount", "payment_date", "paid_by_user_id", "payment_method", "reference_number", "created_at", "updated_at"]
}
