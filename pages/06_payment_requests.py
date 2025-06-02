import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime

st.title("💸 Payment Requests")

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Permissions ===
def get_access_flags(user: dict, page: str):
    role = user.get("role", "")
    can_view = can_add = can_edit = can_approve = can_mark_paid = False
    if page == "payment_requests":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_approve = can_mark_paid = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role == "HQ Accountant":
            can_view = can_approve = can_mark_paid = True
    return can_view, can_add, can_edit, can_approve, can_mark_paid

# === Get session user ===
user = st.session_state.get("user", {})
can_view, can_add, can_edit, can_approve, can_mark_paid = get_access_flags(user, "payment_requests")

if not can_view:
    st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.6); }
        70% { box-shadow: 0 0 0 15px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    .error-box {
        text-align: center;
        background-color: #ffe6e6;
        padding: 2rem;
        border: 2px solid red;
        border-radius: 1.5rem;
        animation: fadeIn 1s ease-in-out, pulse 2s infinite;
        width: 70%;
        margin: 4rem auto;
    }
    .error-box h2 { color: #ff1a1a; font-size: 2rem; }
    .error-box p { font-size: 1.2rem; color: #660000; }
    </style>
    <div class="error-box">
        <h2>⛔ Access Denied</h2>
        <p>You do not have permission to access this page.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# === Helper: Load Contracts for user ===
@st.cache_data(ttl=120)
def load_contracts():
    conn = get_connection()
    cur = conn.cursor()
    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("""
            SELECT c.id, c.title, p.name AS project_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            ORDER BY c.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT c.id, c.title, p.name AS project_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY c.created_at DESC
        """, (user.get("id"),))
    rows = cur.fetchall()
    conn.close()
    return rows

contracts = load_contracts()
contract_map = {f"{c['title']} ({c['project_name']})": c['id'] for c in contracts}

# === Add Payment Request ===
if can_add:
    with st.expander("➕ New Payment Request", expanded=True):
        with st.form("add_payment_request"):
            # Display selected contract details
            selected_contract_id = contract_map[contract_label]
            contract_info = next((c for c in contracts if c['id'] == selected_contract_id), None)
            if contract_info:
                st.markdown(f"**🧱 Project:** {contract_info['project_name']}")
                st.markdown(f"**👷 Contractor:** {contract_info.get('contractor_name', '—')}")
            contract_label = st.selectbox("Select Contract", list(contract_map.keys()))
            amount_usd = st.number_input("Amount (USD)", min_value=0.0, step=100.0, format="%.2f")
            amount_iqd = st.number_input("Amount (IQD)", min_value=0.0, step=100000.0, format="%.0f")
            note = st.text_area("Note / Description")

            if st.form_submit_button("Submit Request"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO payment_requests (
                            id, contract_id, requested_by, amount_usd, amount_iqd, note, status, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(uuid.uuid4()), contract_map[contract_label], user.get("id"),
                        amount_usd if amount_usd > 0 else None,
                        amount_iqd if amount_iqd > 0 else None,
                        note, "Submitted", datetime.utcnow()
                    ))
                    conn.commit()
                    conn.close()
                    st.success("✅ Payment request submitted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to submit request: {e}")

# === Filter Section ===
st.markdown("### 🔍 Filter Payment Requests")
status_filter = st.selectbox("Filter by Status", ["All", "Submitted", "Approved", "Rejected", "Paid"])
date_filter = st.date_input("Show requests after", value=None, key="date_filter")

# === List All Payment Requests ===
st.markdown("### 📄 Payment Request List")

try:
    conn = get_connection()
    cur = conn.cursor()
    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("""
            SELECT pr.*, c.title AS contract_title, u.username AS requested_by_name
            FROM payment_requests pr
            JOIN contracts c ON pr.contract_id = c.id
            JOIN users u ON pr.requested_by = u.id
            ORDER BY pr.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT pr.*, c.title AS contract_title, u.username AS requested_by_name
            FROM payment_requests pr
            JOIN contracts c ON pr.contract_id = c.id
            JOIN users u ON pr.requested_by = u.id
            WHERE pr.requested_by = %s
            ORDER BY pr.created_at DESC
        """, (user.get("id"),))

    rows = cur.fetchall()
    conn.close()

    # Apply filters
    if status_filter != "All":
        rows = [r for r in rows if r["status"] == status_filter]
    if date_filter:
        rows = [r for r in rows if r["created_at"].date() >= date_filter]

    for r in rows:
        with st.expander(f"{r['contract_title']} • {r.get('amount_usd', '—')} USD / {r.get('amount_iqd', '—')} IQD • {r['status']}"):
            st.markdown(f"**Requested By:** {r['requested_by_name']}")
            st.markdown(f"**Note:** {r['note'] or '—'}")
            st.markdown(f"**Created At:** {r['created_at'].strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"**Status:** `{r['status']}`")

            # Upload Proof
            if can_mark_paid and r['status'] == "Approved":
                with st.form(f"upload_proof_{r['id']}"):
                    file = st.file_uploader("🧾 Upload proof of payment (PDF/JPG/PNG)", type=["pdf", "jpg", "png"], key=f"proof_{r['id']}")
                    if st.form_submit_button("Mark as Paid") and file:
                        conn2 = get_connection()
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            UPDATE payment_requests
                            SET status='Paid', updated_at=%s
                            WHERE id=%s
                        """, (datetime.utcnow(), r['id']))
                        conn2.commit()
                        conn2.close()
                        st.success("💸 Marked as Paid")
                        st.rerun()

            if can_approve and r['status'] == "Submitted":
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve", key=f"appr_{r['id']}"):
                        conn2 = get_connection()
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            UPDATE payment_requests SET status='Approved', updated_at=%s WHERE id=%s
                        """, (datetime.utcnow(), r['id']))
                        conn2.commit()
                        conn2.close()
                        st.success("✅ Approved")
                        st.rerun()
                with col2:
                    if st.button("❌ Reject", key=f"rej_{r['id']}"):
                        conn2 = get_connection()
                        cur2 = conn2.cursor()
                        cur2.execute("""
                            UPDATE payment_requests SET status='Rejected', updated_at=%s WHERE id=%s
                        """, (datetime.utcnow(), r['id']))
                        conn2.commit()
                        conn2.close()
                        st.warning("❌ Rejected")
                        st.rerun()
except Exception as e:
    st.error(f"Failed to load payment requests: {e}")
