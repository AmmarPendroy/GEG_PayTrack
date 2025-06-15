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
    """Returns a new database connection."""
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
    cur.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM payment_requests
        GROUP BY status
        """
    )
    status_rows = cur.fetchall()
    status_counts = {r["status"]: r["count"] for r in status_rows}

    # Recent activity log
    cur.execute(
        """
        SELECT
            a.timestamp,
            u.username,
            a.action_type,
            a.details
        FROM activity_log a
        LEFT JOIN users u ON a.performed_by = u.id
        ORDER BY a.timestamp DESC
        LIMIT 20
        """
    )
    activity_rows = cur.fetchall()

    # Recent payment requests with all columns
    cur.execute(
        """
        SELECT
            pr.id,
            pr.contract_id,
            pr.requested_by   AS requested_by_id,
            u.username        AS requested_by,
            pr.requested_date,
            pr.paid_date,
            pr.amount_usd,
            pr.amount_iqd,
            pr.note,
            pr.status,
            pr.comments,
            pr.created_at,
            pr.updated_at,
            c.id               AS contract_id_join,
            c.title            AS contract_title,
            p.id               AS project_id_join,
            p.name             AS project_name,
            co.id              AS contractor_id_join,
            co.name            AS contractor_name
        FROM payment_requests pr
        LEFT JOIN users u        ON pr.requested_by = u.id
        LEFT JOIN contracts c    ON pr.contract_id = c.id
        LEFT JOIN projects p     ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        ORDER BY pr.requested_date DESC
        LIMIT %s
        """,
        (limit_requests,)
    )
    recent_pr_rows = cur.fetchall()

    conn.close()
    return project_count, status_counts, activity_rows, recent_pr_rows

# Load data
total_projects, status_counts, activity_log, recent_payments = load_summary_data()

# ─── 5) UI Layout ───────────────────────────────────────────────
st.title("📊 Dashboard")
st.markdown(f"Welcome back, **{user['username']}**!")

if st.button("🔄 Refresh"):
    st.experimental_rerun()

# — Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏗️ Total Projects", total_projects)
col2.metric("📋 Submitted", status_counts.get("submitted", 0))
col3.metric("💰 Paid",      status_counts.get("paid",      0))
col4.metric("❌ Rejected",  status_counts.get("rejected",  0))

# — Enhanced Payment status chart with legend & filter
st.markdown("---")
st.subheader("📈 Payment Requests by Status")

all_statuses = list(status_counts.keys())
selected_statuses = st.multiselect("Filter statuses", all_statuses, default=all_statuses)

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

# — Recent Payment Requests list (all columns + Short ID)
st.markdown("---")
st.subheader("💸 Recent Payment Requests")
if recent_payments:
    df_pr = pd.DataFrame(
        recent_payments,
        columns=[
            "id", "contract_id", "requested_by_id", "requested_by",
            "requested_date", "paid_date", "amount_usd", "amount_iqd",
            "note", "status", "comments", "created_at", "updated_at",
            "contract_id_join", "contract_title", "project_id_join",
            "project_name", "contractor_id_join", "contractor_name"
        ]
    )
    # Format dates
    df_pr["requested_date"] = pd.to_datetime(df_pr["requested_date"]).dt.strftime("%Y-%m-%d")
    df_pr["paid_date"] = pd.to_datetime(df_pr["paid_date"]).dt.strftime("%Y-%m-%d")
    df_pr["created_at"] = pd.to_datetime(df_pr["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df_pr["updated_at"] = pd.to_datetime(df_pr["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")

    # Generate Short ID: projectName-contractorID-serial
    short_ids = [
        f"{row['project_name']}-{row['contractor_id_join']}-{idx+1}"
        for idx, row in df_pr.iterrows()
    ]
    df_pr.insert(0, "Short ID", short_ids)
    # Drop full UUID request ID
    df_pr.drop(columns=["id"], inplace=True)

    # Rename columns for clarity
    df_pr = df_pr.rename(columns={
        "contract_id": "Contract ID",
        "requested_by_id": "Requested By ID",
        "requested_by": "Requested By",
        "requested_date": "Requested Date",
        "paid_date": "Paid Date",
        "amount_usd": "Amount (USD)",
        "amount_iqd": "Amount (IQD)",
        "note": "Note",
        "status": "Status",
        "comments": "Comments",
        "created_at": "Created At",
        "updated_at": "Updated At",
        "contract_id_join": "Contract ID (Join)",
        "contract_title": "Contract Title",
        "project_id_join": "Project ID (Join)",
        "project_name": "Project Name",
        "contractor_id_join": "Contractor ID (Join)",
        "contractor_name": "Contractor Name"
    })
    st.dataframe(df_pr, use_container_width=True)
else:
    st.info("No recent payment requests found.")

# — Recent Activity log ───────────────────────────────────────────
st.markdown("---")
st.subheader("🕒 Recent Activity")
if activity_log:
    df_act = pd.DataFrame(activity_log, columns=["timestamp", "username", "action_type", "details"])
    df_act["timestamp"] = pd.to_datetime(df_act["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df_act = df_act.rename(columns={
        "timestamp":   "When",
        "username":    "User",
        "action_type": "Action",
        "details":     "Details"
    })
    st.dataframe(df_act, use_container_width=True)
else:
    st.info("No recent activities recorded.")
