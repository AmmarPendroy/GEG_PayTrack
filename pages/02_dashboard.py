# pages/02_dashboard.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

# DB connection
@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# Load references
@st.cache_data(ttl=600)
def load_reference_data():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY name")
    projects = cur.fetchall()
    return projects

projects = load_reference_data()

# Project filter
project_options = ["All Projects"] + [p["name"] for p in projects]
selected_project_name = st.selectbox("📁 Filter Dashboard by Project", project_options)
selected_project_id = next((p["id"] for p in projects if p["name"] == selected_project_name), None) if selected_project_name != "All Projects" else None

@st.cache_data(ttl=30)
def load_summary_data(project_id=None):
    conn = get_connection(); cur = conn.cursor()
    where = "WHERE c.project_id = %s" if project_id else ""
    params = (project_id,) if project_id else ()

    cur.execute(f"SELECT COUNT(*) AS c FROM contracts c {where}", params)
    contracts = cur.fetchone()["c"]

    cur.execute(f"SELECT COUNT(DISTINCT c.contractor_id) AS c FROM contracts c {where}", params)
    contractors = cur.fetchone()["c"]

    cur.execute(f"SELECT COUNT(*) AS c FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where}", params)
    requests = cur.fetchone()["c"]

    cur.execute(f"SELECT pr.status, COUNT(*) AS c FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} GROUP BY pr.status", params)
    rows = cur.fetchall()
    status = {r["status"].lower(): r["c"] for r in rows}
    pending   = status.get("pending", 0)
    approved  = status.get("approved", 0)
    rejected  = status.get("rejected", 0)
    paid_cnt  = status.get("paid", 0)

    cur.execute(f"SELECT COALESCE(SUM(value_usd),0) AS usd FROM contracts c {where}", params)
    budget_usd = cur.fetchone()["usd"]

    cur.execute(f"SELECT COALESCE(SUM(value_iqd),0) AS iqd FROM contracts c {where}", params)
    budget_iqd = cur.fetchone()["iqd"]

    cur.execute(f"SELECT COALESCE(SUM(pr.amount_usd),0) AS usd FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND pr.status='paid'", params)
    paid_usd = cur.fetchone()["usd"]

    cur.execute(f"SELECT COALESCE(SUM(pr.amount_iqd),0) AS iqd FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND pr.status='paid'", params)
    paid_iqd = cur.fetchone()["iqd"]

    cur.execute(f"SELECT AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400) AS avg_days FROM payment_requests pr JOIN contracts c ON pr.contract_id = c.id {where} AND paid_date IS NOT NULL", params)
    avg_days = cur.fetchone()["avg_days"] or 0

    conn.close()
    return {
        "contracts": contracts,
        "contractors": contractors,
        "requests": requests,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "paid_cnt": paid_cnt,
        "budget_usd": budget_usd,
        "budget_iqd": budget_iqd,
        "paid_usd": paid_usd,
        "paid_iqd": paid_iqd,
        "avg_days": avg_days,
    }

data = load_summary_data(project_id=selected_project_id)

if selected_project_id:
    st.markdown(f"**📁 Viewing data for project:** `{selected_project_name}`")
else:
    st.markdown("**📁 Viewing data for:** _All Projects_")

cols = st.columns(4)
cols[0].metric("Total Contracts", data["contracts"])
cols[1].metric("Contractors", data["contractors"])
cols[2].metric("All Requests", data["requests"])
cols[3].metric("Pending", data["pending"])

cols2 = st.columns(4)
cols2[0].metric("Approved", data["approved"])
cols2[1].metric("Rejected", data["rejected"])
cols2[2].metric("Paid Count", data["paid_cnt"])
cols2[3].metric("Avg Approval", f"{data['avg_days']:.1f} days")

c1, c2 = st.columns(2)
c1.metric("Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("Budget (IQD)", f"{data['budget_iqd']:,.0f}")
