# pages/02_dashboard.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import altair as alt

# ─── 1) Page config ────────────────────────────────────────────
st.set_page_config(page_title="📊 Dashboard", layout="wide")

# ─── 2) Helpers ─────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ─── 3) Auth guard ──────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.error("⛔ You must be logged in to view the dashboard.")
    st.stop()

# ─── 4) Live data loader ────────────────────────────────────────
def load_summary_data(limit_requests: int = 10):
    conn = get_connection()
    cur = conn.cursor()

    # Total projects
    cur.execute("SELECT COUNT(*) AS count FROM projects")
    project_count = cur.fetchone()["count"]

    # Payment requests by status
    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM payment_requests
        GROUP BY status
    """)
    status_rows = cur.fetchall()
    status_counts = {r["status"]: r["count"] for r in status_rows}

    # Recent activity log
    cur.execute("""
        SELECT
            a.timestamp,
            u.username,
            a.action_type,
            a.details
        FROM activity_log a
        LEFT JOIN users u ON a.performed_by = u.id
        ORDER BY a.timestamp DESC
        LIMIT 20
    """)
    activity_rows = cur.fetchall()

    # Recent payment requests
    cur.execute(f"""
        SELECT
            pr.id,
            pr.requested_date,
            u.username        AS requester,
            p.name            AS project,
            c.title           AS contract,
            pr.amount_usd,
            pr.amount_iqd,
            pr.status,
            pr.comments
        FROM payment_requests pr
        LEFT JOIN users u       ON pr.requested_by = u.id
        LEFT JOIN contracts c   ON pr.contract_id = c.id
        LEFT JOIN projects p    ON c.project_id = p.id
        ORDER BY pr.requested_date DESC
        LIMIT %s
    """, (limit_requests,))
    recent_pr_rows = cur.fetchall()

    conn.close()
    return project_count, status_counts, activity_rows, recent_pr_rows

# Load data
project_count, status_counts, activity_log, recent_payments = load_summary_data()

# ─── 5) UI Layout ───────────────────────────────────────────────
st.title("📊 Dashboard")
st.markdown(f"Welcome back, **{user['username']}**!")

if st.button("🔄 Refresh"):
    st.experimental_rerun()

# — Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏗️ Total Projects", project_count)
col2.metric("📋 Submitted", status_counts.get("submitted", 0))
col3.metric("💰 Paid",      status_counts.get("paid",      0))
col4.metric("❌ Rejected",  status_counts.get("rejected",  0))

# — Enhanced Payment status chart with legend & filter
st.markdown("---")
st.subheader("📈 Payment Requests by Status")

all_statuses = list(status_counts.keys())
selected_statuses = st.multiselect(
    "Filter statuses", all_statuses, default=all_statuses
)

df_status = pd.DataFrame([
    {"Status": s.capitalize(), "Count": c}
    for s, c in status_counts.items() if s in selected_statuses
])

if not df_status.empty:
    chart = (
        alt.Chart(df_status)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Status:N", sort="-y", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Count:Q", title="Number of Requests"),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(scheme="set3"),
                legend=alt.Legend(title="Status", orient="right")
            ),
            tooltip=["Status:N", "Count:Q"]
        )
        .properties(width="container", height=350)
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No data for the selected statuses.")

# — Recent Payment Requests list (expanded columns) ───────────────
st.markdown("---")
st.subheader("💸 Recent Payment Requests")
if recent_payments:
    df_pr = pd.DataFrame(recent_payments)
    df_pr["requested_date"] = pd.to_datetime(df_pr["requested_date"]) \
                                 .dt.strftime("%Y-%m-%d")
    df_pr = df_pr.rename(columns={
        "id":             "Request ID",
        "requested_date": "Date",
        "requester":      "Requested By",
        "project":        "Project",
        "contract":       "Contract",
        "amount_usd":     "Amount (USD)",
        "amount_iqd":     "Amount (IQD)",
        "status":         "Status",
        "comments":       "Comments"
    })
    st.dataframe(df_pr, use_container_width=True)
else:
    st.info("No recent payment requests found.")

# — Recent Activity log ───────────────────────────────────────────
st.markdown("---")
st.subheader("🕒 Recent Activity")
if activity_log:
    df_act = pd.DataFrame(activity_log)
    df_act["timestamp"] = pd.to_datetime(df_act["timestamp"]) \
                               .dt.strftime("%Y-%m-%d %H:%M:%S")
    df_act = df_act.rename(columns={
        "timestamp":   "When",
        "username":    "User",
        "action_type": "Action",
        "details":     "Details"
    })
    st.dataframe(df_act, use_container_width=True)
else:
    st.info("No recent activities recorded.")
