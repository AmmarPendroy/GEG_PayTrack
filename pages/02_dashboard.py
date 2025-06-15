# pages/02_dashboard.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px

# ────────────────────────────────────────────────────────────────────────────────
# Page config
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

# ────────────────────────────────────────────────────────────────────────────────
# DB connection
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ────────────────────────────────────────────────────────────────────────────────
# Detect USD/IQD column names once
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def detect_money_cols():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='contracts'")
    c_cols = {r["column_name"] for r in cur.fetchall()}
    usd_c = next((c for c in ["value_usd","contract_value_usd","budget_usd"] if c in c_cols), None)
    iqd_c = next((c for c in ["value_iqd","contract_value_iqd","budget_iqd"] if c in c_cols), None)

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='payment_requests'")
    pr_cols = {r["column_name"] for r in cur.fetchall()}
    usd_pr = next((c for c in ["amount_usd","paid_amount_usd"] if c in pr_cols), None)
    iqd_pr = next((c for c in ["amount_iqd","paid_amount_iqd"] if c in pr_cols), None)

    conn.close()
    return usd_c, iqd_c, usd_pr, iqd_pr

usd_contract_col, iqd_contract_col, usd_pr_col, iqd_pr_col = detect_money_cols()

# ────────────────────────────────────────────────────────────────────────────────
# Load reference data
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_reference_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY name")
    projects = cur.fetchall()
    conn.close()
    return projects

projects = load_reference_data()

# ────────────────────────────────────────────────────────────────────────────────
# Project filter dropdown
# ────────────────────────────────────────────────────────────────────────────────
project_options = ["All Projects"] + [p["name"] for p in projects]
selected_project_name = st.selectbox("📁 Filter Dashboard by Project", project_options)
selected_project_id = (
    next((p["id"] for p in projects if p["name"] == selected_project_name), None)
    if selected_project_name != "All Projects" else None
)

# ────────────────────────────────────────────────────────────────────────────────
# Load summary metrics (filtered by project)
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_summary_data(project_id=None):
    conn = get_connection()
    cur = conn.cursor()
    where = "WHERE c.project_id = %s" if project_id else ""
    params = (project_id,) if project_id else ()

    # Contracts count
    cur.execute(f"SELECT COUNT(*) AS c FROM contracts c {where}", params)
    total_contracts = cur.fetchone()["c"]

    # Contractors count
    cur.execute(f"SELECT COUNT(DISTINCT c.contractor_id) AS c FROM contracts c {where}", params)
    total_contractors = cur.fetchone()["c"]

    # Payment requests count
    cur.execute(f"SELECT COUNT(*) AS c FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where}", params)
    total_requests = cur.fetchone()["c"]

    # Status breakdown
    cur.execute(
        f"SELECT pr.status, COUNT(*) AS c "
        f"FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} "
        "GROUP BY pr.status",
        params
    )
    rows = cur.fetchall()
    status = {r["status"].lower(): r["c"] for r in rows}
    pending = status.get("pending", 0)
    approved = status.get("approved", 0)
    rejected = status.get("rejected", 0)
    paid_cnt = status.get("paid", 0)

    # Budget sums
    if usd_contract_col:
        cur.execute(f"SELECT COALESCE(SUM(c.{usd_contract_col}),0) AS s FROM contracts c {where}", params)
        budget_usd = cur.fetchone()["s"]
    else:
        budget_usd = 0
    if iqd_contract_col:
        cur.execute(f"SELECT COALESCE(SUM(c.{iqd_contract_col}),0) AS s FROM contracts c {where}", params)
        budget_iqd = cur.fetchone()["s"]
    else:
        budget_iqd = 0

    # Paid sums
    if usd_pr_col:
        cur.execute(
            f"SELECT COALESCE(SUM(pr.{usd_pr_col}),0) AS s "
            f"FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND pr.status='paid'",
            params
        )
        paid_usd = cur.fetchone()["s"]
    else:
        paid_usd = 0
    if iqd_pr_col:
        cur.execute(
            f"SELECT COALESCE(SUM(pr.{iqd_pr_col}),0) AS s "
            f"FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND pr.status='paid'",
            params
        )
        paid_iqd = cur.fetchone()["s"]
    else:
        paid_iqd = 0

    # Average approval time
    cur.execute(
        f"SELECT AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400) AS avg_days "
        f"FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND paid_date IS NOT NULL",
        params
    )
    avg_days = cur.fetchone()["avg_days"] or 0

    conn.close()
    return {
        "contracts": total_contracts,
        "contractors": total_contractors,
        "requests": total_requests,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "paid_cnt": paid_cnt,
        "budget_usd": budget_usd,
        "budget_iqd": budget_iqd,
        "paid_usd": paid_usd,
        "paid_iqd": paid_iqd,
        "avg_days": avg_days
    }

data = load_summary_data(project_id=selected_project_id)

# Display filter context
if selected_project_id:
    st.markdown(f"**📁 Viewing data for project:** `{selected_project_name}`")
else:
    st.markdown("**📁 Viewing data for:** _All Projects_")

# Metrics
r1 = st.columns(4)
r1[0].metric("Total Contracts", data["contracts"])
r1[1].metric("Contractors", data["contractors"])
r1[2].metric("All Requests", data["requests"])
r1[3].metric("Pending", data["pending"])

r2 = st.columns(4)
r2[0].metric("Approved", data["approved"])
r2[1].metric("Rejected", data["rejected"])
r2[2].metric("Paid Count", data["paid_cnt"])
r2[3].metric("Avg Approval", f"{data['avg_days']:.1f} days")

c1, c2 = st.columns(2)
c1.metric("Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("Budget (IQD)", f"{data['budget_iqd']:,.0f}")

# Budget vs Actual chart (filtered)
ba_df = pd.DataFrame([
    {"Type": "Budget USD", "Amount": data["budget_usd"]},
    {"Type": "Paid USD",   "Amount": data["paid_usd"]},
    {"Type": "Budget IQD", "Amount": data["budget_iqd"]},
    {"Type": "Paid IQD",   "Amount": data["paid_iqd"]}
])
fig = px.bar(ba_df, x="Type", y="Amount", text="Amount", title="Budget vs Actual (Filtered)")
fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
st.plotly_chart(fig, use_container_width=True)

# Pending Payment Requests (filtered)
@st.cache_data(ttl=30)
def load_pending_requests(project_id=None):
    conn = get_connection(); cur = conn.cursor()
    where = "AND c.project_id = %s" if project_id else ""
    params = (project_id,) if project_id else ()
    cur.execute(
        f"""
        SELECT pr.*, c.title AS contract_title,
               p.name AS project_name,
               co.name AS contractor_name,
               u.username AS requested_by
        FROM payment_requests pr
        JOIN contracts c ON pr.contract_id=c.id
        JOIN projects p ON c.project_id=p.id
        JOIN contractors co ON c.contractor_id=co.id
        JOIN users u ON pr.requested_by=u.id
        WHERE pr.status='pending' {where}
        ORDER BY pr.created_at DESC
        """,
        params
    )
    rows = cur.fetchall()
    conn.close()
    return rows

st.subheader("📝 Pending Payment Requests")
pending_list = load_pending_requests(project_id=selected_project_id)
if pending_list:
    df_p = pd.DataFrame(pending_list)
    df_p["requested_date"] = pd.to_datetime(df_p["requested_date"]).dt.date
    df_p["created_at"]     = pd.to_datetime(df_p["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    short_ids = [
        f"{row['project_name']}-{row['contractor_name'][:3].upper()}-{i+1}"
        for i, row in df_p.iterrows()
    ]
    df_p.insert(0, "Short ID", short_ids)
    df_p.drop(columns=["id","updated_at","paid_date"], inplace=True, errors="ignore")
    st.dataframe(df_p, use_container_width=True)
else:
    st.info("No pending payment requests.")

# Recent Payment Requests (filtered)
@st.cache_data(ttl=30)
def load_recent_payment_requests(limit=5, project_id=None):
    conn = get_connection(); cur = conn.cursor()
    where = "AND c.project_id = %s" if project_id else ""
    params = (limit,) + ((project_id,) if project_id else ())
    cur.execute(
        f"""
        SELECT pr.*, c.title    AS contract_title,
               p.name     AS project_name,
               co.name    AS contractor_name,
               u.username AS requested_by
        FROM payment_requests pr
        JOIN contracts c ON pr.contract_id=c.id
        JOIN projects p ON c.project_id=p.id
        JOIN contractors co ON c.contractor_id=co.id
        JOIN users u ON pr.requested_by=u.id
        WHERE TRUE {where}
        ORDER BY pr.created_at DESC
        LIMIT %s
        """,
        params
    )
    rows = cur.fetchall()
    conn.close()
    return rows

st.subheader("💸 Recent Payment Requests")
recent = load_recent_payment_requests(limit=5, project_id=selected_project_id)
if recent:
    df_r = pd.DataFrame(recent)
    df_r["requested_date"] = pd.to_datetime(df_r["requested_date"]).dt.date
    df_r["paid_date"]      = pd.to_datetime(df_r["paid_date"]).dt.date
    df_r["created_at"]     = pd.to_datetime(df_r["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df_r["updated_at"]     = pd.to_datetime(df_r["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")
    short_ids = [
        f"{row['project_name']}-{row['contractor_name'][:3].upper()}-{i+1}"
        for i, row in df_r.iterrows()
    ]
    df_r.insert(0, "Short ID", short_ids)
    df_r.drop(columns=["id"], inplace=True)
    st.dataframe(df_r, use_container_width=True)
else:
    st.info("No recent payment requests found.")
