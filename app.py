import streamlit as st
import psycopg2
import hashlib

# ---------------------------------------
# Load Database URL from secrets
# ---------------------------------------
DB_URL = st.secrets["DATABASE_URL"]

# ---------------------------------------
# Hash password with SHA-256
# ---------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------------------------------
# Connect to PostgreSQL Neon DB
# ---------------------------------------
def get_db_connection():
    return psycopg2.connect(DB_URL)

# ---------------------------------------
# Authenticate user from Neon 'users' table
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
# Login page
# ---------------------------------------
def login_page():
    st.title("GEG PayTrack Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome, {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

# ---------------------------------------
# Role-specific dashboards (scaffolded)
# ---------------------------------------
def show_superadmin():
    st.header("👑 Superadmin Dashboard")
    st.write("Full system control.")

def show_hq_admin():
    st.header("🏢 HQ Admin Dashboard")
    st.write("Manage users, projects, and view all data.")

def show_hq_accountant():
    st.header("💰 HQ Accountant Dashboard")
    st.write("Review and log payments.")

def show_site_pm():
    st.header("📋 Site PM Dashboard")
    st.write("Manage contracts and payment requests.")

def show_site_accountant():
    st.header("📊 Site Accountant Dashboard")
    st.write("Assist PM and track payments.")

# ---------------------------------------
# Main app logic
# ---------------------------------------
def main():
    st.set_page_config(page_title="GEG PayTrack", page_icon="🏗️", layout="centered")

    # Session state to track login
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        login_page()
    else:
        user = st.session_state.user
        st.sidebar.success(f"Logged in as: {user['username']} ({user['role']})")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

        # Route by role
        if user["role"] == "Superadmin":
            show_superadmin()
        elif user["role"] == "HQ Admin":
            show_hq_admin()
        elif user["role"] == "HQ Accountant":
            show_hq_accountant()
        elif user["role"] == "Site PM":
            show_site_pm()
        elif user["role"] == "Site Accountant":
            show_site_accountant()
        else:
            st.error("Unknown role. Please contact administrator.")

if __name__ == "__main__":
    main()
