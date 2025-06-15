import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

# ────────────────────────────────────────────────────────────────────────────────
# Database connection helper
# ────────────────────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ────────────────────────────────────────────────────────────────────────────────
# Load summary data (project counts, payment status summary, activity log)
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_summary_data():
    conn = get_connection()
    cur = conn.cursor()

    # Count projects
    cur.execute("SELECT COUNT(*) FROM projects")
    project_count = cur.fetchone()["count"]

    # Payment status breakdown
    cur.execute("SELECT status, COUNT(*) FROM payment_requests GROUP BY status")
    status_counts_raw = cur.fetchall()
    status_counts = {row['status']: row['count'] for row in status_counts_raw}

    # Activity log
    cur.execute("""
        SELECT timestamp, performed_by, action_type, target_table, target_id, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()
    return project_count, status_counts, activity_log

# ────────────────────────────────────────────────────────────────────────────────
# Load recent payment requests
# ────────────────────────────────────────────────────────────────────────────────
def load_recent_payment_requests(limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT pr.*, 
               c.title AS contract_title,
               p.id AS project_id_join,
               p.name AS project_name,
               co.id AS contractor_id_join,
               co.name AS contractor_name,
               u.username AS requested_by
        FROM payment_requests pr
        LEFT JOIN contracts c ON pr.contract_id = c.id
        LEFT JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        LEFT JOIN users u ON pr.requested_by = u.id
        ORDER BY pr.created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ────────────────────────────────────────────────────────────────────────────────
# 1. Project summary
# ────────────────────────────────────────────────────────────────────────────────
project_count, status_counts, activity_log = load_summary_data()
st.metric("🏗️ Total Projects", value=project_count)

# ────────────────────────────────────────────────────────────────────────────────
# 2. Payment status chart (modern style with legend)
# ────────────────────────────────────────────────────────────────────────────────
import plotly.express as px
status_data = pd.DataFrame(
    [
        {"Status": k.capitalize(), "Count": v} for k, v in status_counts.items()
    ]
)
fig = px.bar(
    status_data,
    x="Status",
    y="Count",
    color="Status",
    color_discrete_sequence=px.colors.qualitative.Pastel,
    title="Payment Requests by Status",
)
fig.update_layout(showlegend=True, xaxis_title="Status", yaxis_title="Count")
st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────────
# 3. Recent Payment Requests (all columns + Short ID)
# ────────────────────────────────────────────────────────────────────────────────
st.subheader("💸 Recent Payment Requests")
recent_payments = load_recent_payment_requests()
if recent_payments:
    df_pr = pd.DataFrame(recent_payments)
    df_pr["requested_date"] = pd.to_datetime(df_pr["requested_date"]).dt.date
    df_pr["paid_date"] = pd.to_datetime(df_pr["paid_date"]).dt.date
    df_pr["created_at"] = pd.to_datetime(df_pr["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df_pr["updated_at"] = pd.to_datetime(df_pr["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")

    short_ids = []
    for idx, row in df_pr.iterrows():
        abbr = (row["contractor_name"].replace(" ", "")[:3] or "UNK").upper()
        short_ids.append(f"{row['project_name']}-{abbr}-{idx+1}")
    df_pr.insert(0, "Short ID", short_ids)
    df_pr.drop(columns=["id"], inplace=True)

    st.dataframe(df_pr, use_container_width=True)
else:
    st.info("No recent payment requests found.")

# ────────────────────────────────────────────────────────────────────────────────
# 4. Recent activity log (last 20 entries)
# ────────────────────────────────────────────────────────────────────────────────
st.subheader("🕒 Recent Activity")
if activity_log:
    df_log = pd.DataFrame(activity_log)
    df_log["timestamp"] = pd.to_datetime(df_log["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
    df_log.rename(columns={
        "timestamp": "Timestamp",
        "performed_by": "User",
        "action_type": "Action",
        "target_table": "Target Table",
        "target_id": "Target ID",
        "details": "Details"
    }, inplace=True)
    st.dataframe(df_log, use_container_width=True)
else:
    st.info("No recent activities recorded.")
