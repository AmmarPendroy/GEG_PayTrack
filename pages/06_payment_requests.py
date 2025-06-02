import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime, date

st.set_page_config(
    page_title="💸 Payment Requests",
    layout="wide",
)

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Inline role-based access logic ===
def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False

    if page == "payment_requests":
        # Allow all roles who can view payment requests
        if role in ["Superadmin", "HQ Admin", "Site PM", "Site Accountant", "HQ Accountant"]:
            can_view = True
        # Only Superadmin and HQ Admin can add new requests
        if role in ["Superadmin", "HQ Admin", "Site PM", "Site Accountant"]:
            can_add = True
        # Only HQ Accountant can mark as paid (edit)
        if role == "HQ Accountant":
            can_edit = True
        # Only Superadmin and HQ Admin can delete
        if role in ["Superadmin", "HQ Admin"]:
            can_delete = True

    return can_view, can_add, can_edit, can_delete

# === Get user & access rights ===
user = st.session_state.get("user", {})

# Protect against NoneType user
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, page="payment_requests")

# === Permission check ===
if not can_view:
    st.markdown(
        """
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

        .error-box h2 {
            color: #ff1a1a;
            font-size: 2rem;
        }

        .error-box p {
            font-size: 1.2rem;
            color: #660000;
        }
        </style>

        <div class="error-box">
            <h2>⛔ Access Denied</h2>
            <p>You do not have permission to access this page.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

st.title("💸 Payment Requests")

# === Helper: Load Contracts (with joined project & contractor info) ===
@st.cache_data(show_spinner=False)
def load_contracts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.id,
            c.title,
            p.name AS project_name,
            ctr.name AS contractor_name
        FROM contracts c
        JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors ctr ON c.contractor_id = ctr.id
        ORDER BY p.name, c.title;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

# === Helper: Load Contractors ===
@st.cache_data(show_spinner=False)
def load_contractors():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM contractors ORDER BY name ASC;")
    rows = cur.fetchall()
    conn.close()
    return rows

# === Helper: Load Payment Requests (excluding “Submitted”) ===
@st.cache_data(show_spinner=False)
def load_payment_requests():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            pr.*,
            c.title AS contract_title,
            u.username AS requested_by_name
        FROM payment_requests pr
        JOIN contracts c ON pr.contract_id = c.id
        JOIN users u ON pr.requested_by = u.id
        WHERE pr.status != 'Submitted'
        ORDER BY pr.created_at DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

# === Add New Payment Request Form ===
if can_add:
    with st.expander("➕ New Payment Request", expanded=False):
        # Load contracts & contractors once
        contracts = load_contracts()
        contractors = load_contractors()

        # Build maps for selection
        contract_map = {f"{c['contract_title']} ({c['project_name']})": c["id"] for c in contracts}
        contractor_map = {ctr["name"]: ctr["id"] for ctr in contractors}

        with st.form("add_payment_request"):
            # Optional filters (not strictly required for selection)
            project_names = sorted(set([c["project_name"] for c in contracts]))
            selected_project = st.selectbox("🧱 Filter by Project (optional)", ["All"] + project_names)

            contractor_names = sorted([ctr["name"] for ctr in contractors])
            selected_contractor = st.selectbox("👷 Contractor", ["All"] + contractor_names)

            # Now build the actual contract selector, potentially filtered
            filtered_contract_labels = []
            for c in contracts:
                if selected_project != "All" and c["project_name"] != selected_project:
                    continue
                if selected_contractor != "All" and c["contractor_name"] != selected_contractor:
                    continue
                filtered_contract_labels.append(f"{c['contract_title']} ({c['project_name']})")
            filtered_contract_labels = sorted(filtered_contract_labels)

            contract_label = st.selectbox(
                "Select Contract",
                filtered_contract_labels if filtered_contract_labels else ["No matching contracts"]
            )
            selected_contract_id = contract_map.get(contract_label)

            # Display selected contract’s project and contractor
            contract_info = next((c for c in contracts if c["id"] == selected_contract_id), None)
            if contract_info:
                st.markdown(f"**🧱 Project:** {contract_info['project_name']}")
                st.markdown(f"**👷 Contractor:** {contract_info.get('contractor_name', '—')}")

            # Date inputs
            start_date = st.date_input("📅 Start Date", value=date.today())
            end_date = st.date_input("📅 End Date", value=date.today())
            requested_date = st.date_input("📆 Requested Date", value=date.today())
            paid_date = st.date_input("💰 Paid Date (optional)", value=None)

            # Amount fields (allow zero / empty)
            amount_usd = st.number_input("Amount (USD)", min_value=0.0, format="%.2f", step=0.01)
            amount_iqd = st.number_input("Amount (IQD)", min_value=0.0, format="%.0f", step=1)

            note = st.text_area("Note / Description")
            uploaded_files = st.file_uploader(
                "📎 Upload Attachments",
                type=["pdf", "docx", "jpg", "png", "jpeg"],
                accept_multiple_files=True
            )

            if st.form_submit_button("Submit Request"):
                if not selected_contract_id:
                    st.error("⚠️ You must select a valid contract.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        payment_id = str(uuid.uuid4())

                        # Insert payment request
                        cur.execute("""
                            INSERT INTO payment_requests (
                                id,
                                contract_id,
                                requested_by,
                                amount_usd,
                                amount_iqd,
                                note,
                                status,
                                start_date,
                                end_date,
                                requested_date,
                                paid_date,
                                created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            payment_id,
                            selected_contract_id,
                            user.get("id"),
                            amount_usd if amount_usd > 0 else None,
                            amount_iqd if amount_iqd > 0 else None,
                            note,
                            "Submitted",
                            start_date,
                            end_date,
                            requested_date,
                            paid_date if paid_date else None,
                            datetime.utcnow()
                        ))

                        # Insert each uploaded file into payment_request_attachments
                        for file in uploaded_files:
                            attachment_id = str(uuid.uuid4())
                            cur.execute("""
                                INSERT INTO payment_request_attachments (
                                    id,
                                    payment_request_id,
                                    file_name,
                                    file_type,
                                    file_data,
                                    uploaded_at
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                attachment_id,
                                payment_id,
                                file.name,
                                file.type,
                                file.getvalue(),
                                datetime.utcnow()
                            ))

                        conn.commit()
                        conn.close()
                        st.success("✅ Payment request submitted!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to submit request: {e}")

st.markdown("---")

# === Filter and Display Payment Requests List ===
st.markdown("## 🧾 Payment Request List")

# Filter controls
col1, col2 = st.columns(2)
with col1:
    status_filter = st.selectbox("Filter by Status", ["All", "Submitted", "Approved", "Paid", "Rejected"])
with col2:
    date_filter = st.date_input("Show after date", value=None)

# Load all payment requests from DB
try:
    requests = load_payment_requests()
except Exception as e:
    st.error(f"Failed to load payment requests: {e}")
    requests = []

# Apply filters
filtered_requests = []
for r in requests:
    # Status filter
    if status_filter != "All" and r.get("status") != status_filter:
        continue
    # Date filter (based on requested_date)
    if date_filter and r.get("requested_date") and r["requested_date"].date() < date_filter:
        continue
    filtered_requests.append(r)

if not filtered_requests:
    st.info("No payment requests found.")
else:
    for pr in filtered_requests:
        with st.expander(f"📄 {pr['contract_title']} — {pr['requested_by_name']}"):
            pr_col1, pr_col2 = st.columns([3, 1])

            with pr_col1:
                st.markdown(f"**👷 Contractor:** {pr.get('contractor_name','—') if 'contractor_name' in pr else '—'}")
                st.markdown(f"**🧱 Project:** {pr.get('project_name','—') if 'project_name' in pr else '—'}")
                st.markdown(f"**💲 Amount (USD):** {pr.get('amount_usd','—') or '—'}")
                st.markdown(f"**💲 Amount (IQD):** {pr.get('amount_iqd','—') or '—'}")
                st.markdown(f"**📅 Start Date:** {pr.get('start_date', '—')}")
                st.markdown(f"**📅 End Date:** {pr.get('end_date', '—')}")
                st.markdown(f"**📆 Requested Date:** {pr.get('requested_date','—')}")
                st.markdown(f"**💰 Paid Date:** {pr.get('paid_date','—') or '—'}")
                st.markdown(f"**📝 Note:** {pr.get('note','—')}")
                st.markdown(f"**📅 Created At:** {pr.get('created_at','—')}")
                st.markdown(f"**▶️ Status:** {pr.get('status','—')}")

                # === Download Attachments ===
                try:
                    conn2 = get_connection()
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        SELECT
                            id,
                            file_name,
                            file_type,
                            file_data,
                            uploaded_at
                        FROM payment_request_attachments
                        WHERE payment_request_id = %s
                        ORDER BY uploaded_at DESC;
                    """, (pr["id"],))
                    attachments = cur2.fetchall()
                    conn2.close()

                    if attachments:
                        st.markdown("**📁 Attachments:**")
                        for a in attachments:
                            st.download_button(
                                label=f"{a['file_name']} ({int(len(a['file_data']))/1024:.1f} KB)",
                                data=a["file_data"],
                                file_name=a["file_name"],
                                mime=a["file_type"]
                            )
                except Exception as e:
                    st.warning(f"⚠️ Cannot load attachments: {e}")

            with pr_col2:
                # Only HQ Accountant can mark as Paid or change status
                if can_edit:
                    new_status = st.selectbox("Update Status", ["Submitted", "Approved", "Paid", "Rejected"], index=["Submitted","Approved","Paid","Rejected"].index(pr.get("status", "Submitted")), key=f"status_{pr['id']}")
                    if st.button("💾 Save", key=f"save_{pr['id']}"):
                        try:
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            cur3.execute("""
                                UPDATE payment_requests
                                SET status = %s,
                                    paid_date = %s
                                WHERE id = %s
                            """, (
                                new_status,
                                pr["paid_date"] if new_status == "Paid" else None,
                                pr["id"]
                            ))
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Status updated")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update status: {e}")

                # Only Superadmin or HQ Admin can delete a payment request
                if can_delete and st.button("🗑️ Delete", key=f"del_pr_{pr['id']}"):
                    try:
                        conn4 = get_connection()
                        cur4 = conn4.cursor()
                        # Remove attachments first
                        cur4.execute("DELETE FROM payment_request_attachments WHERE payment_request_id = %s", (pr["id"],))
                        # Then remove the payment request
                        cur4.execute("DELETE FROM payment_requests WHERE id = %s", (pr["id"],))
                        conn4.commit()
                        conn4.close()
                        st.success("✅ Deleted successfully")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Deletion failed: {e}")
            st.markdown("---")
