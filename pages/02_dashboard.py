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

    # ── Basic counts ───────────────────────────────────────
    def single_count(table):
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        return cur.fetchone()["cnt"]

    total_projects    = single_count("projects")
    total_contracts   = single_count("contracts")
    total_contractors = single_count("contractors")
    total_requests    = single_count("payment_requests")

    # ── Status breakdown ───────────────────────────────────
    cur.execute("""
        SELECT status, COUNT(*) AS cnt
        FROM payment_requests
        GROUP BY status
    """)
    status_rows = cur.fetchall()
    status_counts = {r["status"]: r["cnt"] for r in status_rows}
    paid_count     = status_counts.get("paid", 0)
    rejected_count = status_counts.get("rejected", 0)

    # ── Figure out which money-columns exist ───────────────
    # Contracts table candidates
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'contracts'
    """)
    contract_cols = {r["column_name"] for r in cur.fetchall()}

    usd_contract_col = next(
        (c for c in ["value_usd", "contract_value_usd", "budget_usd"] if c in contract_cols),
        None
    )
    iqd_contract_col = next(
        (c for c in ["value_iqd", "contract_value_iqd", "budget_iqd"] if c in contract_cols),
        None
    )

    # Payment_requests table candidates
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'payment_requests'
    """)
    pr_cols = {r["column_name"] for r in cur.fetchall()}

    usd_pr_col = next(
        (c for c in ["amount_usd", "paid_amount_usd"] if c in pr_cols),
        None
    )
    iqd_pr_col = next(
        (c for c in ["amount_iqd", "paid_amount_iqd"] if c in pr_cols),
        None
    )

    # ── Sums ────────────────────────────────────────────────
    # Contracts budgets
    if usd_contract_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({usd_contract_col}),0) AS total_usd
            FROM contracts
        """)
        total_budget_usd = cur.fetchone()["total_usd"]
    else:
        total_budget_usd = 0

    if iqd_contract_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({iqd_contract_col}),0) AS total_iqd
            FROM contracts
        """)
        total_budget_iqd = cur.fetchone()["total_iqd"]
    else:
        total_budget_iqd = 0

    # Paid amounts
    if usd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({usd_pr_col}),0) AS paid_usd
            FROM payment_requests
            WHERE status='paid'
        """)
        total_paid_usd = cur.fetchone()["paid_usd"]
    else:
        total_paid_usd = 0

    if iqd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({iqd_pr_col}),0) AS paid_iqd
            FROM payment_requests
            WHERE status='paid'
        """)
        total_paid_iqd = cur.fetchone()["paid_iqd"]
    else:
        total_paid_iqd = 0

    # ── Avg approval time ───────────────────────────────────
    cur.execute("""
        SELECT 
          AVG(EXTRACT(EPOCH FROM (paid_date - requested_date)) / 86400) 
          AS avg_days
        FROM payment_requests
        WHERE paid_date IS NOT NULL
    """)
    avg_days = cur.fetchone()["avg_days"] or 0

    # ── Recent activity log ─────────────────────────────────
    cur.execute("""
        SELECT timestamp, performed_by, action_type, target_table, target_id, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()

    return {
        "projects":       total_projects,
        "contracts":      total_contracts,
        "contractors":    total_contractors,
        "requests":       total_requests,
        "status":         status_counts,
        "paid_count":     paid_count,
        "rejected_count": rejected_count,
        "budget_usd":     total_budget_usd,
        "budget_iqd":     total_budget_iqd,
        "paid_usd":       total_paid_usd,
        "paid_iqd":       total_paid_iqd,
        "avg_days":       avg_days,
        "activity_log":   activity_log
    }

data = load_summary_data()

# ── Top metrics ─────────────────────────────────────────────
r1 = st.columns(4)
r1[0].metric("🏗️ Total Projects",    data["projects"])
r1[1].metric("📄 Total Contracts",   data["contracts"])
r1[2].metric("👷 Total Contractors", data["contractors"])
r1[3].metric("💳 All Requests",      data["requests"])

r2 = st.columns(4)
r2[0].metric("⏳ Pending",    data["status"].get("pending",  0))
r2[1].metric("✅ Approved",   data["status"].get("approved", 0))
r2[2].metric("❌ Rejected",   data["rejected_count"])
r2[3].metric("💰 Paid Count", data["paid_count"])

# ── Currency totals + approval time ─────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("💵 Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("💴 Budget (IQD)", f"{data['budget_iqd']:,.0f}")
c3.metric("⏱️ Avg Approval", f"{data['avg_days']:.1f} days")

c4, c5 = st.columns(2)
c4.metric("💵 Paid (USD)", f"{data['paid_usd']:,.2f}")
c5.metric("💴 Paid (IQD)", f"{data['paid_iqd']:,.0f}")

# ── Budget vs Actual chart ───────────────────────────────────
ba_df = pd.DataFrame([
    {"Currency": "USD", "Type": "Budget",     "Amount": data["budget_usd"]},
    {"Currency": "USD", "Type": "Actual Paid", "Amount": data["paid_usd"]},
    {"Currency": "IQD", "Type": "Budget",     "Amount": data["budget_iqd"]},
    {"Currency": "IQD", "Type": "Actual Paid", "Amount": data["paid_iqd"]},
])
fig = px.bar(
    ba_df, x="Currency", y="Amount",
    color="Type", barmode="group", text="Amount",
    title="Budget vs Actual by Currency"
)
fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig.update_layout(yaxis_title="Amount", xaxis_title="")
st.plotly_chart(fig, use_container_width=True)

# ── …then your existing status‐breakdown, recent‐requests table, activity‐log, etc. ───
