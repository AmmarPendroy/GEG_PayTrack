# File: geg_paytrack/pages/06_payment_requests.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime, date

st.set_page_config(page_title="💸 Payment Requests", layout="wide")
st.title("💸 Payment Requests")

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Inline role-based access logic ===
def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    """
    Returns (can_view, can_add, can_mark_paid, can_delete_attachment) for this page.
    - Superadmin, HQ Admin can view/add/mark paid/delete attachments
    - Site PM can view/add
    - Site Accountant, HQ Accountant can view; only HQ Accountant can mark paid and delete attachments
    """
    role = user.get("role", "")
    can_view = can_add = can_mark_paid = can_delete_attachment = False

    if page == "payment_requests":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_mark_paid = can_delete_attachment = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role == "HQ Accountant":
            can_view = can_mark_paid = can_delete_attachment = True
        elif role == "Site Accountant":
            can_view = True

    return can_view, can_add, can_mark_paid, can_delete_attachment

# === Get user & access rights ===
user = st.session_state.get("user", {})
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_mark_paid, can_delete_attachment = get_access_flags(user, page="payment_requests")

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
        unsafe_allow_html=True,
    )
    st.stop()

# === Helper: load all contracts (with their project & contractor names) ===
@st.cache_data(show_spinner=False)
def load_contracts():
    """
    Returns a list of dicts: 
      [{'id': <contract_id>,
        'title': <contract_title>,
        'project_name': <project_name>,
        'contractor_name': <contractor_name>
       }, ... ]
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            c.id,
            c.title,
            p.name AS project_name,
            ctr.name AS contractor_name
        FROM contracts c
        JOIN projects p ON c.project_id = p.id
        JOIN contractors ctr ON c.contractor_id = ctr.id
        ORDER BY p.name, c.title;
        """
    )
    rows = cur.fetchall()
    conn.close()
    contracts = []
    for r in rows:
        contracts.append({
            "id": r["id"],
            "title": r["title"],
            "project_name": r["project_name"],
            "contractor_name": r["contractor_name"],
        })
    return contracts

# === Helper: load all payment requests (except those with status='Pending') ===
@st.cache_data(show_spinner=False)
def load_payment_requests():
    """
    Returns a list of dicts, each row from payment_requests joined with:
      - contract title, project_name, contractor_name
      - requested_by username
    Excludes those still Pending (so newly‐created ones will vanish from the list).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            pr.id,
            pr.contract_id,
            pr.requested_by_user_id,
            pr.requested_date,
            pr.paid_date,
            pr.amount_usd,
            pr.amount_iqd,
            pr.note,
            pr.status,
            pr.created_at,
            p.title           AS contract_title,
            p.project_name    AS project_name,
            p.contractor_name AS contractor_name,
            u.username        AS requested_by_username
        FROM payment_requests pr
        JOIN (
            SELECT 
                c.id,
                c.title,
                pj.name      AS project_name,
                ctr.name     AS contractor_name
            FROM contracts c
            JOIN projects pj ON c.project_id = pj.id
            JOIN contractors ctr ON c.contractor_id = ctr.id
        ) AS p ON pr.contract_id = p.id
        JOIN users u ON pr.requested_by_user_id = u.id
        WHERE pr.status != 'Pending'
        ORDER BY pr.created_at DESC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows

# === Helper: load contractors (for payment filtering) ===
@st.cache_data(show_spinner=False)
def load_contractor_list():
    """
    Return a sorted list of all contractor names.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM contractors ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


# === Helper: load project list (for payment filtering) ===
@st.cache_data(show_spinner=False)
def load_project_list():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


# === Add New Payment Request Form ===
if can_add:
    with st.expander("➕ New Payment Request", expanded=False):
        with st.form("add_payment_request_form"):
            # Load current contracts
            contracts = load_contracts()
            contract_map = {
                f"{c['title']} ({c['project_name']}) — {c['contractor_name']}": c["id"]
                for c in contracts
            }
            contract_labels = list(contract_map.keys())
            contract_labels.sort()

            selected_contract_label = st.selectbox(
                "Select Contract", 
                ["-- Choose contract --"] + contract_labels,
                index=0
            )

            # If a valid contract is chosen, show its contractor & project as read‐only
            col1, col2 = st.columns(2)
            with col1:
                requested_date = st.date_input("Requested Date", date.today())
            with col2:
                paid_date = st.date_input("Paid Date (optional)", None)

            # Display the associated Project / Contractor if a contract is chosen
            contractor_display = ""
            project_display = ""
            if selected_contract_label != "-- Choose contract --":
                sel_id = contract_map[selected_contract_label]
                # find that dict in contracts
                for c in contracts:
                    if c["id"] == sel_id:
                        contractor_display = c["contractor_name"]
                        project_display = c["project_name"]
                        break

            st.markdown(f"**Contractor Name:** {contractor_display or '—'}")
            st.markdown(f"**Project Name:** {project_display or '—'}")

            # Amounts
            amount_usd = st.number_input("Amount (USD)", min_value=0.0, format="%.2f", step=1.0)
            amount_iqd = st.number_input("Amount (IQD)", min_value=0.0, step=1000.0)

            note = st.text_area("Note / Description")

            # Multi‐file uploader for attachments
            uploads = st.file_uploader(
                "📎 Upload Proof (You can select or drag multiple files)", 
                accept_multiple_files=True,
                type=["pdf", "docx", "jpg", "png", "jpeg"]
            )

            if st.form_submit_button("Submit Request"):
                if selected_contract_label == "-- Choose contract --":
                    st.warning("Please select a contract before submitting.")
                else:
                    new_id = str(uuid.uuid4())
                    req_by = user.get("id", None)
                    if not req_by:
                        st.error("Unable to identify current user (no user ID in session).")
                    else:
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            # Insert into payment_requests
                            cur.execute(
                                """
                                INSERT INTO payment_requests
                                  (id, contract_id, requested_by_user_id, requested_date, paid_date,
                                   amount_usd, amount_iqd, note, status, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending', %s)
                                """,
                                (
                                    new_id,
                                    contract_map[selected_contract_label],
                                    req_by,
                                    requested_date,
                                    paid_date if paid_date else None,
                                    amount_usd if amount_usd > 0 else None,
                                    amount_iqd if amount_iqd > 0 else None,
                                    note or None,
                                    datetime.utcnow(),
                                ),
                            )
                            # Insert any uploaded attachments
                            for f in uploads:
                                raw_bytes = f.read()
                                cur.execute(
                                    """
                                    INSERT INTO payment_request_attachments
                                      (id, payment_request_id, file_name, mime_type, data, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        str(uuid.uuid4()),
                                        new_id,
                                        f.name,
                                        f.type,
                                        psycopg2.Binary(raw_bytes),
                                        datetime.utcnow(),
                                    ),
                                )
                            conn.commit()
                            conn.close()
                            st.success("✅ Payment request submitted successfully!")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to submit request: {e}")

        st.write("---")


# === Filter Section ===
st.markdown("🔍 **Filter Payment Requests**")
colf1, colf2, colf3 = st.columns([2, 2, 2])
with colf1:
    statuses = ["All", "Pending", "Approved", "Paid", "Rejected"]
    selected_status = st.selectbox("Filter by Status", statuses, index=0)
with colf2:
    filter_date = st.date_input("Show requests after", None)
with colf3:
    contractor_names = load_contractor_list()
    selected_contractor = st.selectbox("Filter by Contractor", ["All"] + contractor_names)

st.write("---")


# === Load & Display All (non‐Pending) Payment Requests ===
try:
    rows = load_payment_requests()

    # Apply filters:
    filtered = []
    for r in rows:
        if selected_status != "All" and r["status"] != selected_status:
            continue
        if filter_date and r["requested_date"] < filter_date:
            continue
        if selected_contractor != "All" and r["contractor_name"] != selected_contractor:
            continue
        filtered.append(r)

    if not filtered:
        st.info("No payment requests match your filters.")
    else:
        for pr in filtered:
            pr_id = pr["id"]
            with st.expander(f"📄 Request by {pr['requested_by_username']} — {pr['contract_title']} ({pr['project_name']})", expanded=False):
                # Display all fields:
                colA, colB = st.columns([2, 2])
                with colA:
                    st.markdown(f"**Contract Title:** {pr['contract_title']}")
                    st.markdown(f"**Project Name:** {pr['project_name']}")
                    st.markdown(f"**Contractor Name:** {pr['contractor_name']}")
                    st.markdown(f"**Requested By:** {pr['requested_by_username']}")
                    st.markdown(f"**Requested On:** {pr['requested_date']}")
                    st.markdown(f"**Paid On:** {pr['paid_date'] or '—'}")
                with colB:
                    usd_display = f"${pr['amount_usd']:,.2f}" if pr["amount_usd"] else "—"
                    iqd_display = f"{pr['amount_iqd']:,.0f} IQD" if pr["amount_iqd"] else "—"
                    st.markdown(f"**Amount (USD):** {usd_display}")
                    st.markdown(f"**Amount (IQD):** {iqd_display}")
                    st.markdown(f"**Note:** {pr['note'] or '—'}")
                    st.markdown(f"**Status:** {pr['status']}")

                st.write("---")

                # If still Pending and user can mark paid:
                if pr["status"] == "Pending" and can_mark_paid:
                    if st.button(f"🟢 Mark as Paid", key=f"markpaid_{pr_id}"):
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute(
                                """
                                UPDATE payment_requests
                                SET status = 'Paid', paid_date = %s, updated_at = %s
                                WHERE id = %s
                                """,
                                (date.today(), datetime.utcnow(), pr_id),
                            )
                            conn.commit()
                            conn.close()
                            st.success("Status updated to Paid.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to mark as paid: {e}")

                # Multi‐file uploader to add attachments AFTER submission
                new_uploads = st.file_uploader(
                    "📎 Upload Additional Proof (multiple files)", 
                    accept_multiple_files=True,
                    key=f"upl_after_{pr_id}",
                    type=["pdf", "docx", "jpg", "png", "jpeg"]
                )
                if new_uploads:
                    if st.button(f"Upload Proof for {pr_id}", key=f"upl_btn_{pr_id}"):
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            for f in new_uploads:
                                raw_bytes = f.read()
                                cur.execute(
                                    """
                                    INSERT INTO payment_request_attachments
                                      (id, payment_request_id, file_name, mime_type, data, created_at)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        str(uuid.uuid4()),
                                        pr_id,
                                        f.name,
                                        f.type,
                                        psycopg2.Binary(raw_bytes),
                                        datetime.utcnow(),
                                    ),
                                )
                            conn.commit()
                            conn.close()
                            st.success("Attachment(s) uploaded.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to upload attachment(s): {e}")

                st.write("---")

                # List existing attachments for this payment request
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT id, file_name, mime_type, data, created_at
                        FROM payment_request_attachments
                        WHERE payment_request_id = %s
                        ORDER BY created_at DESC;
                        """,
                        (pr_id,),
                    )
                    atts = cur.fetchall()
                    conn.close()
                except Exception as e:
                    st.error(f"Failed to load attachments: {e}")
                    atts = []

                if atts:
                    st.markdown("**📂 Attachments:**")
                    for att in atts:
                        att_id = att["id"]
                        file_display = f"{att['file_name']} ({round(len(att['data'])/1024, 1)} KB)"
                        colX, colY = st.columns([5, 1])
                        with colX:
                            st.download_button(
                                label=f"📥 {file_display}",
                                data=att["data"],
                                file_name=att["file_name"],
                                mime=att["mime_type"],
                                key=f"dl_{att_id}"
                            )
                        with colY:
                            if can_delete_attachment:
                                if st.button("🗑️", key=f"del_att_{att_id}"):
                                    try:
                                        conn = get_connection()
                                        cur = conn.cursor()
                                        cur.execute(
                                            "DELETE FROM payment_request_attachments WHERE id = %s", 
                                            (att_id,)
                                        )
                                        conn.commit()
                                        conn.close()
                                        st.success("Attachment deleted.")
                                        st.experimental_rerun()
                                    except Exception as e:
                                        st.error(f"❌ Failed to delete attachment: {e}")
                    st.write("---")

                # End of expander for this single payment request

except Exception as e:
    st.error(f"Failed to load payment requests: {e}")
