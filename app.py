import streamlit as st
import psycopg2
import hashlib
import pandas as pd

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
# Contractor Form
# ---------------------------------------
def contractor_form():
    st.subheader("➕ Add New Contractor")
    name = st.text_input("Contractor Name")
    person = st.text_input("Contact Person")
    email = st.text_input("Contact Email")
    phone = st.text_input("Contact Phone")
    address = st.text_area("Address")

    if st.button("Submit Contractor"):
        if name:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO contractors (name, contact_person, contact_email, contact_phone, address)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, person, email, phone, address))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Contractor added successfully.")
        else:
            st.error("Contractor name is required.")

# ---------------------------------------
# Contractor Table View
# ---------------------------------------
def contractor_list():
    st.subheader("📋 Contractor List")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, contact_person, contact_email, contact_phone, address, created_at
        FROM contractors
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if rows:
        df = pd.DataFrame(rows, columns=["Name", "Contact", "Email", "Phone", "Address", "Created"])
        st.dataframe(df)
    else:
        st.info("No contractors found.")

# ---------------------------------------
# Dashboards per role
# ---------------------------------------
def show_superadmin():
    st.header("👑 Superadmin Dashboard")
    st.write("Full system access.")

def show_hq_admin():
    st.header("🏢 HQ Admin Dashboard")
    contractor_form()
    contractor_list()

def show_hq_accountant():
    st.header("💰 HQ Accountant Dashboard")
    st.write("Review and log payments.")

def show_site_pm():
    st.header("📋 Site PM Dashboard")
    contractor_form()
    contractor_list()

def show_site_accountant():
    st.header("📊 Site Accountant Dashboard")
    st.write("Track payment progress.")

# ---------------------------------------
# Login Page
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
# Main App Logic
# ---------------------------------------
def main():
    st.set_page_config(page_title="GEG PayTrack", page_icon="🏗️", layout="centered")

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
