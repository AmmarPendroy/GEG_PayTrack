import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime

st.title("👷 Contractors")

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Add Contractor Form ===
with st.expander("➕ Add New Contractor", expanded=True):
    with st.form("add_contractor_form"):
        name = st.text_input("Contractor Name", max_chars=100)
        contact_person = st.text_input("Contact Person")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        address = st.text_area("Address")

        submitted = st.form_submit_button("Add Contractor")

        if submitted:
            if not name:
                st.warning("Contractor name is required.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO contractors (id, name, contact_person, email, phone, address, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()), name, contact_person, email, phone, address, datetime.utcnow()
                    ))
                    conn.commit()
                    conn.close()
                    st.success("✅ Contractor added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Database error: {e}")

# === View Contractors ===
st.markdown("### 📋 Contractor List")

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, contact_person, email, phone, address, created_at FROM contractors ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()

    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No contractors yet.")
except Exception as e:
    st.error(f"Failed to load data: {e}")
