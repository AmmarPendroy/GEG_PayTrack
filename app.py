import streamlit as st
import psycopg2
import hashlib
import datetime

# ---------- Config ----------
DB_URL = st.secrets["DATABASE_URL"]

# ---------- Utility ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def connect_db():
    return psycopg2.connect(DB_URL)

def login_user(username, password):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, hashed_password FROM users WHERE username = %s", (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result and result[3] == hash_password(password):
        return {"id": result[0], "username": result[1], "role": result[2]}
    return None

# ---------- Session State ----------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------- Login Page ----------
def login_page():
    st.title("GEG PayTrack Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome, {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

# ---------- Role-Based Pages ----------
def show_superadmin():
    st.header("👑 Superadmin Panel")
    st.write("Manage roles, users, and full system configuration.")

def show_hq_admin():
    st.header("🏢 HQ Admin Panel")
    st.write("Manage users, view all projects and payment requests.")

def show_hq_accountant():
    st.header("💰 HQ Accountant Panel")
    st.write("Review payment requests and log payments.")

def show_site_pm():
    st.header("📋 Site PM Panel")
    st.write("Manage site contracts and submit payment requests.")

def show_site_accountant():
    st.header("📊 Site Accountant Panel")
    st.write("Track payments and assist PMs.")

# ---------- Main ----------
def main():
    if st.session_state.user is None:
        login_page()
    else:
        role = st.session_state.user["role"]
        st.sidebar.write(f"Logged in as: `{st.session_state.user['username']}` ({role})")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

        if role == "Superadmin":
            show_superadmin()
        elif role == "HQ Admin":
            show_hq_admin()
        elif role == "HQ Accountant":
            show_hq_accountant()
        elif role == "Site PM":
            show_site_pm()
        elif role == "Site Accountant":
            show_site_accountant()
        else:
            st.error("Unknown role!")

main()
