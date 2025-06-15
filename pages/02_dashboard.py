# pages/02_dashboard.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

@st.cache_data(ttl=10)
def load_summary_data():
    conn = get_connection()
    cur = conn.cursor()

    # ─── Totals ───────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) AS count FROM projects")
    total_projects = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM contracts")
    total_contracts = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM contractors")
    total_contractors = cur.fetchone()["count"]

    cur.execute("SELECT COUNT(*) AS count FROM payment_requests")
    total_requests = cur.fetchone()["count"]

    # ─── Status counts ────────────────────────────────────────────────────────
    cur.execute("""
        SELECT status, COUNT(*) AS count
        FROM payment_requests
        GROUP BY status
    """)
    status_rows = cur.fetchall()
    status_counts = {r["status"]: r["count"] for r in status_rows}

    # ─── Paid / Rejected counts ───────────────────────────────────────────────
    paid_count     = status_counts.get("paid",     0)
    rejected_count = status_counts.get("rejected", 0)

    # ─── Budget sums (USD + IQD) ──────────────────────────────────────────────
    cur.execute("""
        SELECT
          COALESCE(SUM(value_usd),0) AS total_usd,
          COALESCE(SUM(value_iqd),0) AS total_iqd
        FROM contracts
    """)
    b = cur.fetchone()
    total_budget_usd = b["total_usd"]
    total_budget_iqd = b["total_iqd"]

    # ─── Paid sums (USD + IQD) ────────────────────────────────────────────────
    cur.execute("""
        SELECT
          COALESCE(SUM(amount_usd),0) AS paid_usd,
          COALESCE(SUM(amount_iqd),0) AS paid_iqd
        FROM payment_requests
        WHERE status='paid'
    """)
    p = cur.fetchone()
    total_paid_usd = p["paid_usd"]
    total_paid_iqd = p["paid_iqd"]

    # ─── Avg approval time (days) ─────────────────────────────────────────────
    cur.execute("""
        SELECT 
          AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400) 
          AS avg_days
        FROM payment_requests
        WHERE paid_date IS NOT NULL
    """)
    avg_days = cur.fetchone()["avg_days"] or 0

    # ─── Recent activity log ─────────────────────────────────────────────────
    cur.execute("""
        SELECT timestamp, performed_by, action_type, target_table, target_id, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()
    return {
        "projects":      total_projects,
        "contracts":     total_contracts,
        "contractors":   total_contractors,
        "requests":      total_requests,
        "status":        status_counts,
        "paid_count":    paid_count,
        "rejected_count":rejected_count,
        "budget_usd":    total_budget_usd,
        "budget_iqd":    total_budget_iqd,
        "paid_usd":      total_paid_usd,
        "paid_iqd":      total_paid_iqd,
        "avg_days":      avg_days,
        "activity_log":  activity_log
    }

data = load_summary_data()

# ─── Top‐line metrics (2 rows of 4) ─────────────────────────────────────────
r1 = st.columns(4)
r1[0].metric("🏗️ Total Projects",    data["projects"])
r1[1].metric("📄 Total Contracts",   data["contracts"])
r1[2].metric("👷 Total Contractors", data["contractors"])
r1[3].metric("💳 All Requests",      data["requests"])

r2 = st.columns(4)
r2[0].metric("⏳ Pending",   data["status"].get("pending",  0))
r2[1].metric("✅ Approved",  data["status"].get("approved", 0))
r2[2].metric("❌ Rejected",  data["rejected_count"])
r2[3].metric("💰 Paid Count",data["paid_count"])

# ─── Currency totals + approval time ────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("💵 Total Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("💴 Total Budget (IQD)", f"{data['budget_iqd']:,.0f}")
c3.metric("⏱️ Avg Approval Time",   f"{data['avg_days']:.1f} days")

c4, c5 = st.columns(2)
c4.metric("💵 Paid Amount (USD)", f"{data['paid_usd']:,.2f}")
c5.metric("💴 Paid Amount (IQD)", f"{data['paid_iqd']:,.0f}")

# ─── Budget vs Actual (grouped bar) ────────────────────────────────────────
ba_df = pd.DataFrame([
    {"Currency": "USD", "Type": "Budget",     "Amount": data["budget_usd"]},
    {"Currency": "USD", "Type": "Actual Paid", "Amount": data["paid_usd"]},
    {"Currency": "IQD", "Type": "Budget",     "Amount": data["budget_iqd"]},
    {"Currency": "IQD", "Type": "Actual Paid", "Amount": data["paid_iqd"]},
])
fig = px.bar(
    ba_df,
    x="Currency",
    y="Amount",
    color="Type",
    barmode="group",
    text="Amount",
    title="Budget vs Actual by Currency"
)
fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig.update_layout(yaxis_title="Amount", xaxis_title="")
st.plotly_chart(fig, use_container_width=True)

# ─── (Optional) Re–include your old status‐breakdown chart here ────────────
# ─── Recent Payment Requests & Activity Log… ──────────────────────────────
