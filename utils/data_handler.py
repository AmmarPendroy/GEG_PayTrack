import psycopg2
import streamlit as st
from utils.db_connection import get_db_connection
from datetime import datetime

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
# Fetch All Contractors
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
