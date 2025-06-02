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
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False

    if page == "payment_requests":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role == "Site Accountant":
            can_view = can_add = True
        elif role == "HQ Accountant":
            can_view = can_edit = True

    return can_view, can_add, can_edit, can_delete

# === Get user & access rights ===
user = st.session_state.get("user", {})
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

# === Helper functions to load data ===
@st.cache_data
def load_contracts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            c.id, c.title AS contract_title,
            p.id AS project_id, p.name AS project_name,
            co.id AS contractor_id, co.name AS contractor_name
        FROM contracts c
        LEFT JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        ORDER BY p.name, c.title
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data
def load_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, location FROM projects ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data
def load_contractors():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM contractors ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

# === Add New Payment Request Form ===
if can_add:
    with st.expander("➕ New Payment Request", expanded=False):
        with st.form("add_payment_request_form"):
            # Load selections
            projects = load_projects()
            project_map = {f"{p['name']} ({p['location']})": p['id'] for p in projects}
            project_labels = list(project_map.keys())

            contractors = load_contractors()
            contractor_map = {c['name']: c['id'] for c in contractors}
            contractor_labels = list(contractor_map.keys())

            contracts = load_contracts()
            # Build mapping of "Contract Title (Contractor Name)"
            contract_map = {
                f"{c['contract_title']} ({c['contractor_name']})": c['id']
                for c in contracts
            }
            contract_labels_all = list(contract_map.keys())

            # Select Project (optional)
            selected_project_label = st.selectbox(
                "Select Project (optional)", ["All"] + sorted(project_labels)
            )
            selected_project_id = None
            if selected_project_label != "All":
                selected_project_id = project_map[selected_project_label]

            # Filter contracts by selected_project_id if given
            if selected_project_id:
                filtered_contracts = [
                    c for c in contracts if c["project_id"] == selected_project_id
                ]
            else:
                filtered_contracts = contracts

            # Build filtered contract map
            contract_map_filtered = {
                f"{c['contract_title']} ({c['contractor_name']})": c['id']
                for c in filtered_contracts
            }
            contract_labels = list(contract_map_filtered.keys())

            # Select Contractor (optional)
            selected_contractor_label = st.selectbox(
                "Select Contractor (optional)", ["All"] + sorted(contractor_labels)
            )
            selected_contractor_id = None
            if selected_contractor_label != "All":
                selected_contractor_id = contractor_map[selected_contractor_label]

            # If a contractor is chosen, further filter contracts
            if selected_contractor_id:
                filtered_contracts = [
                    c for c in filtered_contracts if c["contractor_id"] == selected_contractor_id
                ]
                contract_map_filtered = {
                    f"{c['contract_title']} ({c['contractor_name']})": c['id']
                    for c in filtered_contracts
                }
                contract_labels = list(contract_map_filtered.keys())

            # Select Contract
            selected_contract_label = st.selectbox(
                "Select Contract", [""] + sorted(contract_labels)
            )
            selected_contract_id = None
            if selected_contract_label:
                selected_contract_id = contract_map_filtered[selected_contract_label]

            # Amounts
            amount_usd = st.number_input("Amount (USD)", min_value=0.0, format="%.2f")
            amount_iqd = st.number_input("Amount (IQD)", min_value=0.0, format="%.2f")
            # Dates
            requested_date = st.date_input("Requested Date", value=date.today())
            paid_date = st.date_input("Paid Date (optional)", value=None)

            # Status - use lowercase values matching DB enum
            status_options = {"Submitted": "submitted", "Pending": "pending", "Paid": "paid"}
            status_label = st.selectbox("Status", list(status_options.keys()), index=0)
            status_value = status_options[status_label]

            # Note / Description
            note = st.text_area("Note / Description")

            # File uploader for multiple attachments
            attachments = st.file_uploader(
                "📎 Upload Attachments (PDF, DOCX, JPG, PNG)", 
                accept_multiple_files=True, 
                type=["pdf", "docx", "jpg", "jpeg", "png"]
            )

            if st.form_submit_button("Submit Request"):
                # Validation
                if not selected_contract_id:
                    st.warning("Please select a contract.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        # Insert into payment_requests (uses `requested_by` instead of requested_by_user_id)
                        cur.execute(
                            """
                            INSERT INTO payment_requests
                            (id, contract_id, requested_by, requested_date, paid_date, amount_usd, amount_iqd, note, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                str(uuid.uuid4()),
                                selected_contract_id,
                                user.get("id"),
                                requested_date,
                                paid_date if paid_date else None,
                                amount_usd if amount_usd > 0 else None,
                                amount_iqd if amount_iqd > 0 else None,
                                note,
                                status_value,
                                datetime.utcnow()
                            ),
                        )
                        new_request_id = cur.fetchone()["id"]
                        # Insert attachments
                        for file in attachments or []:
                            file_id = str(uuid.uuid4())
                            file_bytes = file.getvalue()
                            mime_type = file.type
                            filename = file.name
                            cur.execute(
                                """
                                INSERT INTO payment_request_attachments
                                (id, payment_request_id, filename, content, mime_type, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    file_id,
                                    new_request_id,
                                    filename,
                                    psycopg2.Binary(file_bytes),
                                    mime_type,
                                    datetime.utcnow()
                                ),
                            )
                        conn.commit()
                        conn.close()
                        st.success("✅ Payment request submitted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to submit request: {e}")

        st.markdown("---")


# === Filter & List Payment Requests ===
st.markdown("### 🔎 Filter Payment Requests")

# Status filter
status_filter = st.selectbox("Filter by Status", ["All", "submitted", "pending", "paid"])
# Show after date filter
show_after_date = st.date_input("Show requests after", value=None)

st.markdown("### 📄 Payment Request List")

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pr.id,
            pr.requested_date,
            pr.paid_date,
            pr.amount_usd,
            pr.amount_iqd,
            pr.note,
            pr.status,
            pr.requested_by,
            pr.created_at,
            c.title AS contract_title,
            p.name AS project_name,
            co.name AS contractor_name,
            u.username AS requested_by_name
        FROM payment_requests pr
        LEFT JOIN contracts c ON pr.contract_id = c.id
        LEFT JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        LEFT JOIN users u ON pr.requested_by = u.id
        ORDER BY pr.requested_date DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    # Apply filters
    filtered_rows = []
    for r in rows:
        # status_filter is lowercase, r["status"] is lowercase
        if status_filter != "All" and r["status"] != status_filter:
            continue
        if show_after_date and r["requested_date"].date() < show_after_date:
            continue
        filtered_rows.append(r)

    if not filtered_rows:
        st.info("No payment requests found.")
    else:
        for req in filtered_rows:
            # Expand label shows contract / project / contractor / status
            expander_label = (
                f"{req['contract_title']} ({req['project_name']}) - {req['contractor_name']} | "
                f"{req['status'].capitalize()}"
            )
            with st.expander(expander_label):
                # Display main details
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Project:** {req['project_name']}")
                    st.markdown(f"**Contract:** {req['contract_title']}")
                    st.markdown(f"**Contractor:** {req['contractor_name']}")
                    st.markdown(f"**Requested By:** {req['requested_by_name'] or '—'}")
                    st.markdown(f"**Requested Date:** {req['requested_date'].strftime('%Y-%m-%d')}")
                    if req["paid_date"]:
                        st.markdown(f"**Paid Date:** {req['paid_date'].strftime('%Y-%m-%d')}")
                    st.markdown(f"**Amount (USD):** {req['amount_usd'] or '—'}")
                    st.markdown(f"**Amount (IQD):** {req['amount_iqd'] or '—'}")
                    st.markdown(f"**Note:** {req['note'] or '—'}")
                    st.markdown(f"**Status:** {req['status'].capitalize()}")
                with col2:
                    # Delete button (only if can_delete)
                    if can_delete:
                        if st.button("🗑️ Delete Request", key=f"del_req_{req['id']}"):
                            try:
                                conn2 = get_connection()
                                cur2 = conn2.cursor()
                                # First delete attachments
                                cur2.execute(
                                    "DELETE FROM payment_request_attachments WHERE payment_request_id = %s",
                                    (req["id"],),
                                )
                                # Then delete the request row
                                cur2.execute(
                                    "DELETE FROM payment_requests WHERE id = %s",
                                    (req["id"],),
                                )
                                conn2.commit()
                                conn2.close()
                                st.success("🗑️ Request deleted successfully")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to delete request: {e}")

                    # Mark as Paid (only if can_edit and status == 'submitted')
                    if can_edit and req["status"] == "submitted":
                        if st.button("✅ Mark as Paid", key=f"mark_paid_{req['id']}"):
                            try:
                                conn3 = get_connection()
                                cur3 = conn3.cursor()
                                cur3.execute(
                                    """
                                    UPDATE payment_requests
                                    SET status = %s, paid_date = %s
                                    WHERE id = %s
                                    """,
                                    ("paid", datetime.utcnow(), req["id"]),
                                )
                                conn3.commit()
                                conn3.close()
                                st.success("✅ Request marked as paid")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to mark as paid: {e}")

                st.markdown("---")
                st.markdown("📎 **Attachments:**")

                # List attachments for this request
                try:
                    conn4 = get_connection()
                    cur4 = conn4.cursor()
                    cur4.execute(
                        """
                        SELECT id, filename, mime_type, created_at
                        FROM payment_request_attachments
                        WHERE payment_request_id = %s
                        ORDER BY created_at DESC
                        """,
                        (req["id"],),
                    )
                    attachments_rows = cur4.fetchall()
                    conn4.close()

                    if not attachments_rows:
                        st.info("No attachments.")
                    else:
                        for att in attachments_rows:
                            colA, colB = st.columns([5, 1])
                            with colA:
                                st.write(f"📄 {att['filename']} ({att['created_at'].strftime('%Y-%m-%d %H:%M')})")
                                # Download button
                                try:
                                    conn5 = get_connection()
                                    cur5 = conn5.cursor()
                                    cur5.execute(
                                        "SELECT content FROM payment_request_attachments WHERE id = %s",
                                        (att["id"],),
                                    )
                                    data_row = cur5.fetchone()
                                    conn5.close()
                                    if data_row:
                                        file_bytes = data_row["content"].tobytes()
                                        st.download_button(
                                            label="Download",
                                            data=file_bytes,
                                            file_name=att["filename"],
                                            mime=att["mime_type"],
                                            key=f"download_{att['id']}"
                                        )
                                except Exception:
                                    pass
                            with colB:
                                if can_delete:
                                    if st.button("🗑️", key=f"del_att_{att['id']}"):
                                        try:
                                            conn6 = get_connection()
                                            cur6 = conn6.cursor()
                                            cur6.execute(
                                                "DELETE FROM payment_request_attachments WHERE id = %s",
                                                (att["id"],),
                                            )
                                            conn6.commit()
                                            conn6.close()
                                            st.success("Attachment deleted")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Failed to delete attachment: {e}")
                except Exception:
                    st.error("Failed to load attachments.")

                # Allow uploading additional attachments if user can edit
                if can_edit:
                    st.markdown("➕ Add More Attachments:")
                    more_files = st.file_uploader(
                        f"Upload more files for {req['contract_title']}", 
                        accept_multiple_files=True, 
                        type=["pdf", "docx", "jpg", "jpeg", "png"], 
                        key=f"more_upload_{req['id']}"
                    )
                    if st.button("Upload", key=f"upload_more_{req['id']}"):
                        if more_files:
                            try:
                                conn7 = get_connection()
                                cur7 = conn7.cursor()
                                for f in more_files:
                                    file_id2 = str(uuid.uuid4())
                                    file_bytes2 = f.getvalue()
                                    mime2 = f.type
                                    fname2 = f.name
                                    cur7.execute(
                                        """
                                        INSERT INTO payment_request_attachments
                                        (id, payment_request_id, filename, content, mime_type, created_at)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        """,
                                        (
                                            file_id2,
                                            req["id"],
                                            fname2,
                                            psycopg2.Binary(file_bytes2),
                                            mime2,
                                            datetime.utcnow()
                                        ),
                                    )
                                conn7.commit()
                                conn7.close()
                                st.success("Attachments uploaded successfully")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to upload attachments: {e}")
                        else:
                            st.warning("Please select files to upload.")

                st.markdown("---")

except Exception as e:
    st.error(f"Failed to load payment requests: {e}")
