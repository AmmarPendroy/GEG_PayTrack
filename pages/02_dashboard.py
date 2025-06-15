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
# DB helper
# ────────────────────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# ────────────────────────────────────────────────────────────────────────────────
# Detect USD/IQD columns once
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def detect_money_cols():
    conn = get_connection(); cur = conn.cursor()
    # contracts table columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='contracts'")
    c_cols = {r["column_name"] for r in cur.fetchall()}
    usd_c = next((c for c in ["value_usd","contract_value_usd","budget_usd"] if c in c_cols), None)
    iqd_c = next((c for c in ["value_iqd","contract_value_iqd","budget_iqd"] if c in c_cols), None)
    # payment_requests table columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='payment_requests'")
    pr_cols = {r["column_name"] for r in cur.fetchall()}
    usd_pr = next((c for c in ["amount_usd","paid_amount_usd"] if c in pr_cols), None)
    iqd_pr = next((c for c in ["amount_iqd","paid_amount_iqd"] if c in pr_cols), None)
    conn.close()
    return usd_c, iqd_c, usd_pr, iqd_pr

usd_contract_col, iqd_contract_col, usd_pr_col, iqd_pr_col = detect_money_cols()

# ────────────────────────────────────────────────────────────────────────────────
# Load reference lists
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_reference_data():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id,name FROM projects ORDER BY name");    projects = cur.fetchall()
    cur.execute("SELECT id,name FROM contractors ORDER BY name"); contractors = cur.fetchall()
    cur.execute("SELECT id,title FROM contracts ORDER BY title"); contracts = cur.fetchall()
    conn.close()
    return projects, contractors, contracts

projects, contractors_list, contracts_list = load_reference_data()

# ────────────────────────────────────────────────────────────────────────────────
# Sidebar: Refresh button
# ────────────────────────────────────────────────────────────────────────────────
if st.sidebar.button("🔄 Refresh Data"):
    st.experimental_rerun()

# ────────────────────────────────────────────────────────────────────────────────
# Load summary metrics
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_summary_data():
    conn = get_connection(); cur = conn.cursor()

    # basic counts
    def cnt(table):
        cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
        return cur.fetchone()["c"]

    total_projects    = cnt("projects")
    total_contracts   = cnt("contracts")
    total_contractors = cnt("contractors")
    total_requests    = cnt("payment_requests")

    # status breakdown (lowercasing for safety)
    cur.execute("""
        SELECT lower(status) AS status, COUNT(*) AS c
        FROM payment_requests
        GROUP BY lower(status)
    """)
    rows = cur.fetchall()
    status = {r["status"]: r["c"] for r in rows}
    pending   = status.get("pending",   0)
    approved  = status.get("approved",  0)
    rejected  = status.get("rejected",  0)
    paid_cnt  = status.get("paid",      0)

    # budgets sums
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

    # paid sums
    if usd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({usd_pr_col}),0) AS s
            FROM payment_requests WHERE lower(status)='paid'
        """)
        total_paid_usd = cur.fetchone()["s"]
    else:
        total_paid_usd = 0
    if iqd_pr_col:
        cur.execute(f"""
            SELECT COALESCE(SUM({iqd_pr_col}),0) AS s
            FROM payment_requests WHERE lower(status)='paid'
        """)
        total_paid_iqd = cur.fetchone()["s"]
    else:
        total_paid_iqd = 0

    # avg approval time
    cur.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (paid_date - requested_date))/86400) AS avg_days
        FROM payment_requests
        WHERE paid_date IS NOT NULL
    """)
    avg_days = cur.fetchone()["avg_days"] or 0

    # recent activity
    cur.execute("""
        SELECT timestamp, performed_by, action_type, target_table, target_id, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 20
    """)
    activity_log = cur.fetchall()

    conn.close()
    return {
        "projects":     total_projects,
        "contracts":    total_contracts,
        "contractors":  total_contractors,
        "requests":     total_requests,
        "pending":      pending,
        "approved":     approved,
        "rejected":     rejected,
        "paid_cnt":     paid_cnt,
        "budget_usd":   total_budget_usd,
        "budget_iqd":   total_budget_iqd,
        "paid_usd":     total_paid_usd,
        "paid_iqd":     total_paid_iqd,
        "avg_days":     avg_days,
        "activity_log": activity_log
    }

data = load_summary_data()

# ────────────────────────────────────────────────────────────────────────────────
# Top‐line metrics
# ────────────────────────────────────────────────────────────────────────────────
r1 = st.columns(4)
r1[0].metric("🏗️ Total Projects",    data["projects"])
r1[1].metric("📄 Total Contracts",   data["contracts"])
r1[2].metric("👷 Total Contractors", data["contractors"])
r1[3].metric("💳 All Requests",      data["requests"])

r2 = st.columns(4)
r2[0].metric("⏳ Pending",    data["pending"])
r2[1].metric("✅ Approved",   data["approved"])
r2[2].metric("❌ Rejected",   data["rejected"])
r2[3].metric("💰 Paid Count", data["paid_cnt"])

c1, c2, c3 = st.columns(3)
c1.metric("💵 Budget (USD)", f"{data['budget_usd']:,.2f}")
c2.metric("💴 Budget (IQD)", f"{data['budget_iqd']:,.0f}")
c3.metric("⏱️ Avg Approval", f"{data['avg_days']:.1f} days")

c4, c5 = st.columns(2)
c4.metric("💵 Paid (USD)", f"{data['paid_usd']:,.2f}")
c5.metric("💴 Paid (IQD)", f"{data['paid_iqd']:,.0f}")

# ────────────────────────────────────────────────────────────────────────────────
# Pending Payment Requests list
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_pending_requests():
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"""
        SELECT pr.*,
               c.title    AS contract_title,
               p.name     AS project_name,
               co.name    AS contractor_name,
               u.username AS requested_by
        FROM payment_requests pr
        LEFT JOIN contracts c ON pr.contract_id=c.id
        LEFT JOIN projects p ON c.project_id=p.id
        LEFT JOIN contractors co ON c.contractor_id=co.id
        LEFT JOIN users u ON pr.requested_by=u.id
        WHERE lower(pr.status)='pending'
        ORDER BY pr.created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

st.subheader("📝 Pending Payment Requests")
pending = load_pending_requests()
if pending:
    df_p = pd.DataFrame(pending)
    df_p["requested_date"] = pd.to_datetime(df_p["requested_date"]).dt.date
    df_p["created_at"]     = pd.to_datetime(df_p["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    short_ids = [
        f"{row['project_name']}-{row['contractor_name'][:3].upper() or 'UNK'}-{i+1}"
        for i, row in df_p.iterrows()
    ]
    df_p.insert(0, "Short ID", short_ids)
    df_p.drop(columns=["id","updated_at","paid_date"], inplace=True, errors="ignore")
    st.dataframe(df_p, use_container_width=True)
else:
    st.info("No pending payment requests.")

# ────────────────────────────────────────────────────────────────────────────────
# Budget vs Actual by Entity (multi-select)
# ────────────────────────────────────────────────────────────────────────────────
st.subheader("🔍 Budget vs Actual by Entity")
entity_type = st.selectbox("Entity type", ["Project","Contractor","Contract"], key="entity_type")

if entity_type=="Project":
    ref_list, label_field = projects, "name"
elif entity_type=="Contractor":
    ref_list, label_field = contractors_list, "name"
else:
    ref_list, label_field = contracts_list, "title"

id_map = {item[label_field]: item["id"] for item in ref_list}
names  = list(id_map.keys())
selected = st.multiselect(f"Select {entity_type}s", names, default=names[:1])

def get_entity_financials(entity, ent_id):
    conn = get_connection(); cur = conn.cursor()
    # budgets & paid sums logic (as before)...
    # [Use the same logic you already have here]
    conn.close()
    return b_usd, b_iqd, p_usd, p_iqd  # your computed values

if selected:
    rows = []
    for name in selected:
        ent_id = id_map[name]
        b_usd, b_iqd, p_usd, p_iqd = get_entity_financials(entity_type, ent_id)
        rows += [
            {"Entity": name, "Currency":"USD","Type":"Budget",     "Amount":b_usd},
            {"Entity": name, "Currency":"USD","Type":"Actual Paid","Amount":p_usd},
            {"Entity": name, "Currency":"IQD","Type":"Budget",     "Amount":b_iqd},
            {"Entity": name, "Currency":"IQD","Type":"Actual Paid","Amount":p_iqd},
        ]
    ent_df = pd.DataFrame(rows)
    fig = px.bar(
        ent_df, x="Entity", y="Amount", color="Type",
        barmode="group", facet_col="Currency", text="Amount",
        title=f"{entity_type} Budget vs Actual"
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(yaxis_title="Amount", xaxis_title="", legend_title="Type")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Please select one or more {entity_type.lower()}s.")

# ────────────────────────────────────────────────────────────────────────────────
# Recent Payment Requests
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_recent_payment_requests(limit=5):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT pr.*,
               c.title    AS contract_title,
               p.name     AS project_name,
               co.name    AS contractor_name,
               u.username AS requested_by
        FROM payment_requests pr
        LEFT JOIN contracts c ON pr.contract_id=c.id
        LEFT JOIN projects p ON c.project_id=p.id
        LEFT JOIN contractors co ON c.contractor_id=co.id
        LEFT JOIN users u ON pr.requested_by=u.id
        ORDER BY pr.created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

st.subheader("💸 Recent Payment Requests")
recent = load_recent_payment_requests()
if recent:
    df_r = pd.DataFrame(recent)
    df_r["requested_date"] = pd.to_datetime(df_r["requested_date"]).dt.date
    df_r["paid_date"]      = pd.to_datetime(df_r["paid_date"]).dt.date
    df_r["created_at"]     = pd.to_datetime(df_r["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df_r["updated_at"]     = pd.to_datetime(df_r["updated_at"]).dt.strftime("%Y-%m-%d %H:%M")
    short_ids = [
        f"{row['project_name']}-{row['contractor_name'][:3].upper() or 'UNK'}-{i+1}"
        for i, row in df_r.iterrows()
    ]
    df_r.insert(0, "Short ID", short_ids)
    df_r.drop(columns=["id"], inplace=True)
    st.dataframe(df_r, use_container_width=True)
else:
    st.info("No recent payment requests found.")

# ────────────────────────────────────────────────────────────────────────────────
# Recent Activity Log
# ────────────────────────────────────────────────────────────────────────────────
st.subheader("🕒 Recent Activity")
df_log = pd.DataFrame(data["activity_log"])
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
