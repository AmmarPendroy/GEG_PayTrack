import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px
from datetime import datetime

# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")
# ────────────────────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

@st.cache_data(ttl=10)
def load_summary_data():
    conn = get_connection()
    cur = conn.cursor()
    # ─── Totals ────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM projects")
    total_projects = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM contracts")
    total_contracts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM contractors")
    total_contractors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payment_requests")
    total_requests = cur.fetchone()[0]
    # ─── Status counts ────────────────────────────────────────────────────────
    cur.execute("SELECT status, COUNT(*) FROM payment_requests GROUP BY status")
    status_counts = {row[0]: row[1] for row in cur.fetchall()}
    # ─── Total paid counts ────────────────────────────────────────────────────
    paid_count     = status_counts.get("paid",     0)
    rejected_count = status_counts.get("rejected", 0)
    # ─── Amount sums ──────────────────────────────────────────────────────────
    # Contracts
    cur.execute("SELECT COALESCE(SUM(value_usd),0), COALESCE(SUM(value_iqd),0) FROM contracts")
    total_budget_usd, total_budget_iqd = cur.fetchone()
    # Paid amounts
    cur.execute("""
        SELECT
            COALESCE(SUM(amount_usd),0),
            COALESCE(SUM(amount_iqd),0)
        FROM payment_requests
        WHERE status='paid'
    """)
    total_paid_usd, total_paid_iqd = cur.fetchone()
    # ─── Average approval time (days) ─────────────────────────────────────────
    cur.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400)
        FROM payment_requests
        WHERE paid_date IS NOT NULL
    """)
    avg_approval_days = cur.fetchone()[0] or 0
    # ─── Recent activity log ──────────────────────────────────────────────────
    cur.execute("""
        SELECT timestamp, performed_by, action_type, target_table, target_id, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()
    return {
        "projects": total_projects,
        "contracts": total_contracts,
        "contractors": total_contractors,
        "requests": total_requests,
        "status": status_counts,
        "paid_count": paid_count,
        "rejected_count": rejected_count,
        "budget_usd": total_budget_usd,
        "budget_iqd": total_budget_iqd,
        "paid_usd": total_paid_usd,
        "paid_iqd": total_paid_iqd,
        "avg_days": avg_approval_days,
        "activity_log": activity_log
    }

data = load_summary_data()

# ────────────────────────────────────────────────────────────────────────────────
# Top‐line metrics (2 rows of 4)
# ────────────────────────────────────────────────────────────────────────────────
row1 = st.columns(4)
row1[0].metric("🏗️ Total Projects",     data["projects"])
row1[1].metric("📄 Total Contracts",    data["contracts"])
row1[2].metric("👷 Total Contractors",  data["contractors"])
row1[3].metric("💳 All Requests",       data["requests"])

row2 = st.columns(4)
row2[0].metric("⏳ Pending",   data["status"].get("pending",  0))
row2[1].metric("✅ Approved",  data["status"].get("approved", 0))
row2[2].metric("❌ Rejected",  data["rejected_count"])
row2[3].metric("💰 Paid Count", data["paid_count"])

# ────────────────────────────────────────────────────────────────────────────────
# Currency totals and approval time
# ────────────────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("💵 Total Budget (USD)", f"{data['budget_usd']:,.2f}")
col2.metric("💴 Total Budget (IQD)", f"{data['budget_iqd']:,.0f}")
col3.metric("⏱️ Avg Approval Time", f"{data['avg_days']:.1f} days")

col4, col5 = st.columns(2)
col4.metric("💵 Paid Amount (USD)", f"{data['paid_usd']:,.2f}")
col5.metric("💴 Paid Amount (IQD)", f"{data['paid_iqd']:,.0f}")

# ────────────────────────────────────────────────────────────────────────────────
# Budget vs Actual (grouped bar)
# ────────────────────────────────────────────────────────────────────────────────
ba_df = pd.DataFrame([
    {"Currency": "USD", "Type": "Budget",    "Amount": data["budget_usd"]},
    {"Currency": "USD", "Type": "Actual Paid","Amount": data["paid_usd"]},
    {"Currency": "IQD", "Type": "Budget",    "Amount": data["budget_iqd"]},
    {"Currency": "IQD", "Type": "Actual Paid","Amount": data["paid_iqd"]},
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

# ────────────────────────────────────────────────────────────────────────────────
# Existing: Payment status breakdown (if you still want the old chart)
# ────────────────────────────────────────────────────────────────────────────────
# …your prior Plotly status‐breakdown here…

# ────────────────────────────────────────────────────────────────────────────────
# Recent Payment Requests & Activity Log
# ────────────────────────────────────────────────────────────────────────────────
# …your existing tables for recent requests and activity log…
