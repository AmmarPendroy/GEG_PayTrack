import psycopg2
import streamlit as st

# ---------------------------------------
# Connect to Neon PostgreSQL
# ---------------------------------------
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])
