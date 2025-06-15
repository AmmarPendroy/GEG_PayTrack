import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime

# ——— Page Config ———
st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

# ——— DB Connection ———
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ——— Load Logged-in User ———
user = st.session_state.get("user", {})
role = user.get("role")

# ——— Access Check ———
if not role:
    st.error("You must be logged in to view the dashboard.")
    st.stop()

# ——— Load Summary Data for Dashboard ———
def load_summary_data():
    conn = get_connection()
    cur = conn.cursor()

    project_filter = ""
    if role in ["Site PM", "Site Accountant"]:
        cur.execute("SELECT id FROM users WHERE username = %s", (user["username"],))
        user_row = cur.fetchone()
        cur.execute("""
            SELECT DISTINCT p.id FROM projects p
            JOIN contracts c ON p.id = c.project_id
            JOIN payment_requests pr ON c.id = pr.contract_id
            WHERE pr.requested_by = %s
        """, (user_row["id"],))
        project_ids = [str(r["id"]) for r in cur.fetchall()]
        if project_ids:
            placeholders = ",".join(["%s"] * len(project_ids))
            project_filter = f"WHERE p.id IN ({placeholders})"

    # Project count
    cur.execute(f"SELECT COUNT(*) FROM projects p {project_filter}", tuple(project_ids) if project_filter else ())
    project_count = cur.fetchone()["count"]

    # Payment requests by status
    cur.execute(f"""
        SELECT pr.status, COUNT(*) AS count
        FROM payment_requests pr
        JOIN contracts c ON pr.contract_id = c.id
        JOIN projects p ON c.project_id = p.id
        {project_filter.replace('p.id', 'p.id') if project_filter else ''}
        GROUP BY pr.status
    """, tuple(project_ids) if project_filter else ())
    status_counts = {row["status"]: row["count"] for row in cur.fetchall()}

    # Recent activity log
    cur.execute("""
        SELECT a.timestamp, u.username, a.action, a.details
        FROM activity_log a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()
    return project_count, status_counts, activity_log

# ——— Load Live Data ———
project_count, status_counts, activity_log = load_summary_data()

# ——— Layout ———
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏗️ Projects", project_count)
col2.metric("📝 Submitted", status_counts.get("submitted", 0))
col3.metric("💰 Paid", status_counts.get("paid", 0))
col4.metric("❌ Rejected", status_counts.get("rejected", 0))

# ——— Activity Log ———
st.markdown("---")
st.subheader("📜 Recent Activity Log")

if not activity_log:
    st.info("No recent activities logged.")
else:
    df = pd.DataFrame(activity_log)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(df, use_container_width=True)
