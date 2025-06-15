import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="📊 Dashboard", layout="wide")

# ─── Access Guard ───────────────────────────────────────────────
user = st.session_state.get("user", {})
if not user:
    st.error("⛔ Unauthorized. Please log in.")
    st.stop()

# ─── DB Connection ──────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ─── Refresh Button ─────────────────────────────────────────────
if st.button("🔄 Refresh Dashboard"):
    st.experimental_rerun()

# ─── Header ─────────────────────────────────────────────────────
st.title("📊 Project Overview Dashboard")
st.markdown("Welcome back, **{}**!".format(user["username"]))

# ─── Metrics Summary ────────────────────────────────────────────
def load_summary_data():
    conn = get_connection()
    cur = conn.cursor()

    # Filter based on role and assigned projects
    project_filter = ""
    if user["role"] in ["Site PM", "Site Accountant"]:
        project_filter = f"""
            WHERE id IN (
                SELECT project_id FROM user_projects WHERE user_id = (
                    SELECT id FROM users WHERE username = %s
                )
            )
        """

    # Project Status Counts
    cur.execute(f"""
        SELECT status, COUNT(*) as count FROM projects
        {project_filter}
        GROUP BY status
    """, (user["username"],) if project_filter else ())
    project_rows = cur.fetchall()

    # Payment Status Counts
    cur.execute(f"""
        SELECT status, COUNT(*) as count FROM payments
        {project_filter.replace("id", "project_id") if project_filter else ""}
        GROUP BY status
    """, (user["username"],) if project_filter else ())
    payment_rows = cur.fetchall()

    # Activity Log (latest 10)
    cur.execute("""
        SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 10
    """)
    activity = cur.fetchall()

    conn.close()
    return project_rows, payment_rows, activity

projects, payments, activity_log = load_summary_data()

# ─── Render Project Status Cards ────────────────────────────────
st.subheader("🏗️ Project Status")
project_cols = st.columns(len(projects) if projects else 1)
for i, row in enumerate(projects):
    with project_cols[i]:
        st.metric(label=row["status"], value=row["count"])

# ─── Render Payment Status Cards ────────────────────────────────
st.subheader("💰 Payment Requests")
payment_cols = st.columns(len(payments) if payments else 1)
for i, row in enumerate(payments):
    with payment_cols[i]:
        st.metric(label=row["status"], value=row["count"])

# ─── Render Recent Activity ─────────────────────────────────────
st.subheader("🕒 Recent Activity")
if activity_log:
    df = pd.DataFrame(activity_log)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(df[["timestamp", "username", "action"]], use_container_width=True)
else:
    st.info("No recent activity logged.")
