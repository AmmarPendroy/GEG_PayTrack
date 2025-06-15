import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px

# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Dashboard")

def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ─── Detect your USD/IQD column names once ────────────────────────────────────
@st.cache_data(ttl=3600)
def detect_money_cols():
    conn = get_connection(); cur = conn.cursor()
    # contracts table
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'contracts'
    """)
    contract_cols = {r["column_name"] for r in cur.fetchall()}
    usd_c = next((c for c in ["value_usd","contract_value_usd","budget_usd"] if c in contract_cols), None)
    iqd_c = next((c for c in ["value_iqd","contract_value_iqd","budget_iqd"] if c in contract_cols), None)

    # payment_requests table
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'payment_requests'
    """)
    pr_cols = {r["column_name"] for r in cur.fetchall()}
    usd_pr = next((c for c in ["amount_usd","paid_amount_usd"] if c in pr_cols), None)
    iqd_pr = next((c for c in ["amount_iqd","paid_amount_iqd"] if c in pr_cols), None)

    conn.close()
    return usd_c, iqd_c, usd_pr, iqd_pr

usd_contract_col, iqd_contract_col, usd_pr_col, iqd_pr_col = detect_money_cols()

# ─── Load project/contractor/contract lists for selectors ────────────────────
@st.cache_data(ttl=60)
def load_reference_data():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id,name FROM projects ORDER BY name")
    projects = cur.fetchall()
    cur.execute("SELECT id,name FROM contractors ORDER BY name")
    contractors = cur.fetchall()
    cur.execute("SELECT id,title FROM contracts ORDER BY title")
    contracts = cur.fetchall()
    conn.close()
    return projects, contractors, contracts

projects, contractors_list, contracts_list = load_reference_data()

# ─── Sidebar refresh button ───────────────────────────────────────────────────
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# ─── Load all the summary numbers ──────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_summary_data():
    conn = get_connection(); cur = conn.cursor()

    # — basic counts —
    def cnt(table):
        cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
        return cur.fetchone()["c"]
    total_projects    = cnt("projects")
    total_contracts   = cnt("contracts")
    total_contractors = cnt("contractors")
    total_requests    = cnt("payment_requests")

    # — status breakdown (lowercased to avoid KeyError) —
    cur.execute("""
        SELECT status, COUNT(*) AS c
        FROM payment_requests
        GROUP BY status
    """)
    rows = cur.fetchall()
    status_counts = {r["status"].lower(): r["c"] for r in rows}
    pending   = status_counts.get("pending",   0)
    approved  = status_counts.get("approved",  0)
    rejected  = status_counts.get("rejected",  0)
    paid_cnt  = status_counts.get("paid",      0)

    # — total budgets (USD + IQD) —
    if usd_contract_col:
        cur.execute(f"SELECT COALESCE(SUM({usd_contract_col}),0) AS s FROM contracts")
        total_budget_usd = cur.fetchone()["s"]
    else:
        total_budget_usd = 0

    if iqd_contract_col:
        cur.execute(f"SELECT COALESCE(SUM({iqd_contract_col}),0) AS s FROM contracts")
        total_budget_iqd = cur.fetchone()["s"]
    else:
        total_budget_iqd = 0

    # — total paid amounts (USD + IQD) —
    if usd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({usd_pr_col}),0) AS s
            FROM payment_requests
            WHERE status='paid'
        """)
        total_paid_usd = cur.fetchone()["s"]
    else:
        total_paid_usd = 0

    if iqd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({iqd_pr_col}),0) AS s
            FROM payment_requests
            WHERE status='paid'
        """)
        total_paid_iqd = cur.fetchone()["s"]
    else:
        total_paid_iqd = 0

    # — average approval time (days) —
    cur.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400) AS avg_days
        FROM payment_requests
        WHERE paid_date IS NOT NULL
    """)
    avg_days = cur.fetchone()["avg_days"] or 0

    # — recent activity log —
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
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "paid_count": paid_cnt,
        "budget_usd": total_budget_usd,
        "budget_iqd": total_budget_iqd,
        "paid_usd": total_paid_usd,
        "paid_iqd": total_paid_iqd,
        "avg_days": avg_days,
        "activity_log": activity_log
    }

data = load_summary_data()

# ─── Top‐line metrics ──────────────────────────────────────────────────────────
r1 = st.columns(4)
r1[0].metric("🏗️ Total Projects",    data["projects"])
r1[1].metric("📄 Total Contracts",   data["contracts"])
r1[2].metric("👷 Total Contractors", data["contractors"])
r1[3].metric("💳 All Requests",      data["requests"])

r2 = st.columns(4)
r2[0].metric("⏳ Pending",   data["pending"])
r2[1].metric("✅ Approved",  data["approved"])
r2[2].metric("❌ Rejected",  data["rejected"])
r2[3].metric("💰 Paid Count",data["paid_count"])

c1, c2, c3 = st.columns(3)
c1.metric("💵 Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("💴 Budget (IQD)", f"{data['budget_iqd']:,.0f}")
c3.metric("⏱️ Avg Approval", f"{data['avg_days']:.1f} days")

c4, c5 = st.columns(2)
c4.metric("💵 Paid (USD)", f"{data['paid_usd']:,.2f}")
c5.metric("💴 Paid (IQD)", f"{data['paid_iqd']:,.0f}")

# ─── Budget vs Actual by Currency ─────────────────────────────────────────────
ba_df = pd.DataFrame([
    {"Currency": "USD", "Type": "Budget", "Amount": data["budget_usd"]},
    {"Currency": "USD", "Type": "Actual", "Amount": data["paid_usd"]},
    {"Currency": "IQD", "Type": "Budget", "Amount": data["budget_iqd"]},
    {"Currency": "IQD", "Type": "Actual", "Amount": data["paid_iqd"]},
])
fig = px.bar(
    ba_df, x="Currency", y="Amount", color="Type", barmode="group", text="Amount",
    title="Budget vs Actual by Currency"
)
fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig.update_layout(yaxis_title="Amount", xaxis_title="")
st.plotly_chart(fig, use_container_width=True)

# ─── Budget vs Actual by Project/Contractor/Contract ────────────────────────
st.subheader("🔍 Budget vs Actual by Entity")
entity_type = st.selectbox(
    "Select entity type",
    ["Project", "Contractor", "Contract"],
    key="entity_type"
)

def get_entity_financials(entity, entity_id):
    conn = get_connection(); cur = conn.cursor()
    # budgets
    if usd_contract_col:
        if entity == "Project":
            cur.execute(f"""
                SELECT COALESCE(SUM({usd_contract_col}),0) AS val
                FROM contracts
                WHERE project_id = %s
            """, (entity_id,))
        elif entity == "Contractor":
            cur.execute(f"""
                SELECT COALESCE(SUM({usd_contract_col}),0) AS val
                FROM contracts
                WHERE contractor_id = %s
            """, (entity_id,))
        else:  # Contract
            cur.execute(f"""
                SELECT COALESCE({usd_contract_col},0) AS val
                FROM contracts
                WHERE id = %s
            """, (entity_id,))
        bud_usd = cur.fetchone()["val"]
    else:
        bud_usd = 0

    if iqd_contract_col:
        if entity == "Project":
            cur.execute(f"""
                SELECT COALESCE(SUM({iqd_contract_col}),0) AS val
                FROM contracts
                WHERE project_id = %s
            """, (entity_id,))
        elif entity == "Contractor":
            cur.execute(f"""
                SELECT COALESCE(SUM({iqd_contract_col}),0) AS val
                FROM contracts
                WHERE contractor_id = %s
            """, (entity_id,))
        else:
            cur.execute(f"""
                SELECT COALESCE({iqd_contract_col},0) AS val
                FROM contracts
                WHERE id = %s
            """, (entity_id,))
        bud_iqd = cur.fetchone()["val"]
    else:
        bud_iqd = 0

    # actual paid
    if usd_pr_col:
        if entity in ("Project", "Contractor"):
            join_cond = "c.project_id" if entity == "Project" else "c.contractor_id"
            cur.execute(f"""
                SELECT COALESCE(SUM(pr.{usd_pr_col}),0) AS val
                FROM payment_requests pr
                JOIN contracts c ON pr.contract_id = c.id
                WHERE pr.status='paid' AND {join_cond} = %s
            """, (entity_id,))
        else:
            cur.execute(f"""
                SELECT COALESCE(SUM({usd_pr_col}),0) AS val
                FROM payment_requests
                WHERE status='paid' AND contract_id = %s
            """, (entity_id,))
        paid_usd = cur.fetchone()["val"]
    else:
        paid_usd = 0

    if iqd_pr_col:
        if entity in ("Project", "Contractor"):
            join_cond = "c.project_id" if entity == "Project" else "c.contractor_id"
            cur.execute(f"""
                SELECT COALESCE(SUM(pr.{iqd_pr_col}),0) AS val
                FROM payment_requests pr
                JOIN contracts c ON pr.contract_id = c.id
                WHERE pr.status='paid' AND {join_cond} = %s
            """, (entity_id,))
        else:
            cur.execute(f"""
                SELECT COALESCE(SUM({iqd_pr_col}),0) AS val
                FROM payment_requests
                WHERE status='paid' AND contract_id = %s
            """, (entity_id,))
        paid_iqd = cur.fetchone()["val"]
    else:
        paid_iqd = 0

    conn.close()
    return bud_usd, bud_iqd, paid_usd, paid_iqd

# choose entity
if entity_type == "Project":
    names = [p["name"] for p in projects]
    sel = st.selectbox("Pick project", names, key="ent_proj")
    ent_id = next(p["id"] for p in projects if p["name"] == sel)
elif entity_type == "Contractor":
    names = [c["name"] for c in contractors_list]
    sel = st.selectbox("Pick contractor", names, key="ent_cont")
    ent_id = next(c["id"] for c in contractors_list if c["name"] == sel)
else:
    titles = [c["title"] for c in contracts_list]
    sel = st.selectbox("Pick contract", titles, key="ent_con")
    ent_id = next(c["id"] for c in contracts_list if c["title"] == sel)

b_usd, b_iqd, p_usd, p_iqd = get_entity_financials(entity_type, ent_id)

ent_df = pd.DataFrame([
    {"Currency": "USD", "Type": "Budget", "Amount": b_usd},
    {"Currency": "USD", "Type": "Actual", "Amount": p_usd},
    {"Currency": "IQD", "Type": "Budget", "Amount": b_iqd},
    {"Currency": "IQD", "Type": "Actual", "Amount": p_iqd},
])
ent_fig = px.bar(
    ent_df, x="Currency", y="Amount", color="Type", barmode="group", text="Amount",
    title=f"{entity_type} “{sel}” Budget vs Actual"
)
ent_fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
ent_fig.update_layout(yaxis_title="Amount", xaxis_title="")
st.plotly_chart(ent_fig, use_container_width=True)

# ─── Finally: your status‐breakdown chart, recent‐requests table & activity log…──
