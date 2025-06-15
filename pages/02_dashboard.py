# pages/02_dashboard.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd

# ─── 1) Page config ────────────────────────────────────────────
st.set_page_config(page_title="📊 Dashboard", layout="wide")

# ─── 2) Helpers ─────────────────────────────────────────────────
def get_connection():
    """Return a new connection to the PostgreSQL database."""
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ─── 3) Auth guard ──────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.error("⛔ You must be logged in to view the dashboard.")
    st.stop()

# ─── 4) Live data loader ────────────────────────────────────────
def load_summary_data():
    """
    Query the database for:
      • Total projects count
      • Payment request counts by status
      • The 20 most recent activity_log entries
    """
    conn = get_connection()
    cur = conn.cursor()

    # 4a) Total projects
    cur.execute("SELECT COUNT(*) AS count FROM projects")
    project_count = cur.fetchone()["count"]

    # 4b) Payment requests grouped by status (real-time)
    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM payment_requests
        GROUP BY status
    """)
    status_rows = cur.fetchall()
    # Convert to dict for easy lookup
    status_counts = {row["status"]: row["count"] for row in status_rows}

    # 4c) Recent activity log
    cur.execute("""
        SELECT
            a.timestamp,
            u.username,
            a.action_type,
            a.details
        FROM activity_log a
        LEFT JOIN users u
          ON a.performed_by = u.id
        ORDER BY a.timestamp DESC
        LIMIT 20
    """)
    activity_rows = cur.fetchall()

    conn.close()
    return project_count, status_counts, activity_rows

# Load live summary
project_count, status_counts, activity_log = load_summary_data()

# ─── 5) UI Layout ───────────────────────────────────────────────
st.title("📊 Dashboard")
st.markdown(f"Welcome back, **{user['username']}**!")

# Refresh button
if st.button("🔄 Refresh"):
    st.rerun()

# ─── 5a) Summary metrics ────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏗️ Total Projects", project_count)
col2.metric("📋 Submitted", status_counts.get("submitted", 0))
col3.metric("💰 Paid", status_counts.get("paid", 0))
col4.metric("❌ Rejected", status_counts.get("rejected", 0))

# ─── 5b) Payment status chart ──────────────────────────────────
st.markdown("---")
st.subheader("📈 Payment Requests by Status")
if status_counts:
    df_status = pd.DataFrame([
        {"Status": status.capitalize(), "Count": count}
        for status, count in status_counts.items()
    ])
    st.bar_chart(df_status.set_index("Status")["Count"])
else:
    st.info("No payment requests found.")

# ─── 5c) Recent activity log ───────────────────────────────────
st.markdown("---")
st.subheader("🕒 Recent Activity")
if activity_log:
    df_activity = pd.DataFrame(activity_log)
    df_activity["timestamp"] = pd.to_datetime(df_activity["timestamp"]) \
                                    .dt.strftime("%Y-%m-%d %H:%M:%S")
    df_activity = df_activity.rename(columns={
        "timestamp": "When",
        "username": "User",
        "action_type": "Action",
        "details": "Details"
    })
    st.dataframe(df_activity, use_container_width=True)
else:
    st.info("No recent activities recorded.")
