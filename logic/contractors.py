import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime

def render_contractor_module(user):
    st.subheader("👷 Contractor Management")

    allowed_roles = ["Superadmin", "HQ Admin", "Site PM"]
    if user["role"] not in allowed_roles:
        st.warning("⛔ You do not have permission to access this module.")
        return

    # Add Contractor Form
    with st.expander("➕ Add New Contractor", expanded=True):
        with st.form("add_contractor_form"):
            name = st.text_input("Contractor Name")
            contact = st.text_input("Contact Person")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            address = st.text_area("Address")
            submitted = st.form_submit_button("Add Contractor")

            if submitted:
                if name:
                    success = add_contractor(name, contact, phone, email, address, user["username"])
                    if success:
                        st.success("✅ Contractor added successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add contractor.")
                else:
                    st.warning("Please provide at least the contractor name.")

    # View Contractors
    st.markdown("### 📋 All Contractors")
    contractors = get_all_contractors()
    if contractors:
        st.dataframe(contractors, use_container_width=True)
    else:
        st.info("No contractors found.")

def add_contractor(name, contact, phone, email, address, created_by):
    try:
        conn = psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contractors (id, name, contact_person, phone, email, address, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), name, contact, phone, email, address, created_by, datetime.utcnow()
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def get_all_contractors():
    try:
        conn = psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT name, contact_person, phone, email, address, created_at FROM contractors ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Database Error: {e}")
        return []
