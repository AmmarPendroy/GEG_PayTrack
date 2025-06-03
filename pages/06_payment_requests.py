import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
import uuid
import pandas as pd
import io

st.set_page_config(page_title="💸 Payment Requests", layout="wide")
st.title("💸 Payment Requests")


# ────────────────────────────────────────────────────────────────────────────────
# 1) Database connection helper
# ────────────────────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)


# ────────────────────────────────────────────────────────────────────────────────
# 2) Inline role‐based access logic
# ────────────────────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────────────────────
# 3) Get user & access rights
# ────────────────────────────────────────────────────────────────────────────────
user = st.session_state.get("user", {})
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, page="payment_requests")

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
        .error-box h2 { color: #ff1a1a; font-size: 2rem; }
        .error-box p { font-size: 1.2rem; color: #660000; }
        </style>
        <div class="error-box">
            <h2>⛔ Access Denied</h2>
            <p>You do not have permission to access this page.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ────────────────────────────────────────────────────────────────────────────────
# 4) Helper functions to load “foreign‐key” data
# ────────────────────────────────────────────────────────────────────────────────
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


@st.cache_data
def load_contracts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            c.id,
            c.title AS contract_title,
            p.id AS project_id,
            p.name AS project_name,
            co.id AS contractor_id,
            co.name AS contractor_name
        FROM contracts c
        LEFT JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        ORDER BY p.name, c.title
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


@st.cache_data
def load_payment_requests(status_filter: str | None, start_date_filter: date | None):
    """
    Loads payment_requests along with joined fields from contracts/projects/contractors/users.
    Returns a list of dicts.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Base query (we'll filter in‐Python afterward)
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
            pr.comments,
            pr.created_at,
            u.username AS requested_by_name,
            c.title AS contract_title,
            p.name AS project_name,
            co.name AS contractor_name
        FROM payment_requests pr
        LEFT JOIN users u ON pr.requested_by = u.id
        LEFT JOIN contracts c ON pr.contract_id = c.id
        LEFT JOIN projects p ON c.project_id = p.id
        LEFT JOIN contractors co ON c.contractor_id = co.id
        ORDER BY pr.requested_date DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    # Filter in‐Python
    filtered = []
    for r in rows:
        if status_filter and status_filter != "All" and r["status"] != status_filter:
            continue
        if start_date_filter and r["requested_date"].date() < start_date_filter:
            continue
        filtered.append(r)

    return filtered


# ────────────────────────────────────────────────────────────────────────────────
# 5) Helper to insert a new payment_request (plus attachments)
# ────────────────────────────────────────────────────────────────────────────────
def insert_payment_request(
    request_id: str,
    contract_id: str,
    requested_by: str,
    amount_usd: float | None,
    amount_iqd: float | None,
    note: str | None,
    requested_date: date,
    paid_date: date | None,
    status: str,
    comments: str | None,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO payment_requests
          (id, contract_id, requested_by, requested_date, paid_date,
           amount_usd, amount_iqd, note, status, comments, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
            request_id,
            contract_id,
            requested_by,
            requested_date,
            paid_date if paid_date else None,
            amount_usd if amount_usd else None,
            amount_iqd if amount_iqd else None,
            note if note else None,
            status,
            comments if comments else None,
        ),
    )
    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# 6) Helper to update an existing payment_request
# ────────────────────────────────────────────────────────────────────────────────
def update_payment_request(
    request_id: str,
    amount_usd: float | None,
    amount_iqd: float | None,
    note: str | None,
    requested_date: date,
    paid_date: date | None,
    status: str,
    comments: str | None,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE payment_requests
        SET
          amount_usd = %s,
          amount_iqd = %s,
          note = %s,
          requested_date = %s,
          paid_date = %s,
          status = %s,
          comments = %s,
          updated_at = NOW()
        WHERE id = %s
        """,
        (
            amount_usd if amount_usd else None,
            amount_iqd if amount_iqd else None,
            note if note else None,
            requested_date,
            paid_date if paid_date else None,
            status,
            comments if comments else None,
            request_id,
        ),
    )
    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# 7) Helper to upload attachments for a given payment_request_id
# ────────────────────────────────────────────────────────────────────────────────
def upload_attachments(request_id: str, files):
    if not files:
        return
    conn = get_connection()
    cur = conn.cursor()
    for f in files:
        file_id = str(uuid.uuid4())
        file_bytes = f.getvalue()
        mime_type = f.type
        filename = f.name
        cur.execute(
            """
            INSERT INTO payment_request_attachments
              (id, payment_request_id, filename, content, mime_type, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (
                file_id,
                request_id,
                filename,
                psycopg2.Binary(file_bytes),
                mime_type,
            ),
        )
    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# 8) Helper to load attachments for a given request_id
# ────────────────────────────────────────────────────────────────────────────────
def load_request_attachments(request_id: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT
          id,
          filename,
          mime_type,
          created_at
        FROM payment_request_attachments
        WHERE payment_request_id = %s
        ORDER BY created_at DESC
        """,
        (request_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ────────────────────────────────────────────────────────────────────────────────
# 9) Helper to delete a single attachment by its ID
# ────────────────────────────────────────────────────────────────────────────────
def delete_attachment(attachment_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM payment_request_attachments WHERE id = %s",
        (attachment_id,),
    )
    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# 10) “Export Buttons” – CSV + Excel for ALL requests (ignoring filters)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 Export Payment Requests (All Records)")

all_requests = load_payment_requests(status_filter=None, start_date_filter=None)
df_all = pd.DataFrame(all_requests)

if not df_all.empty:
    # CSV buffer
    csv_buffer = io.StringIO()
    df_all.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📄 Download as CSV",
        data=csv_buffer.getvalue(),
        file_name="payment_requests.csv",
        mime="text/csv",
    )

    # Excel buffer (wrapped in try/except to catch missing engine)
    try:
        xlsx_buffer = io.BytesIO()
        with pd.ExcelWriter(xlsx_buffer, engine="xlsxwriter") as writer:
            df_all.to_excel(writer, index=False, sheet_name="PaymentRequests")
            writer.save()
        st.download_button(
            label="💾 Download as Excel",
            data=xlsx_buffer.getvalue(),
            file_name="payment_requests.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ModuleNotFoundError:
        st.warning(
            "⚠️ Excel export is unavailable because the "
            "`xlsxwriter` engine is not installed. CSV download is still available."
        )
else:
    st.info("No payment requests available for export.")


# ────────────────────────────────────────────────────────────────────────────────
# 11) Filter Section + Real‐Time Summary Chart
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 Filter Payment Requests")
status_filter = st.selectbox("Filter by Status", ["All", "submitted", "pending", "paid", "rejected"])
start_date_filter = st.date_input("Show requests after", value=None)

# Reload all, then apply Python‐side filtering
requests_df = load_payment_requests(status_filter=None, start_date_filter=None)
df = pd.DataFrame(requests_df)

if not df.empty:
    # Convert requested_date column to actual date
    df["requested_date"] = pd.to_datetime(df["requested_date"]).dt.date

    # Filter by status
    if status_filter != "All":
        df = df[df["status"] == status_filter]

    # Filter by start_date
    if start_date_filter:
        df = df[df["requested_date"] >= start_date_filter]

    st.markdown("### 📊 Summary by Status (Filtered)")
    if df.empty:
        st.info("No payment requests match the current filters.")
    else:
        # Count per status, preserve order
        status_counts = df["status"].value_counts().reindex(
            ["submitted", "pending", "paid", "rejected"], fill_value=0
        )
        # Use Streamlit’s bar_chart
        st.bar_chart(
            status_counts.rename_axis("status").reset_index(name="count"),
            x="status",
            y="count",
        )
else:
    st.info("No payment requests found in the database.")


# ────────────────────────────────────────────────────────────────────────────────
# 12) “New Payment Request” Expander (if can_add)
# ────────────────────────────────────────────────────────────────────────────────
if can_add:
    with st.expander("➕ New Payment Request", expanded=False):
        with st.form("add_payment_request_form"):
            # Load Projects, Contractors, Contracts
            projects = load_projects()
            project_map = {f"{p['name']} ({p['location']})": p["id"] for p in projects}
            project_labels = sorted(project_map.keys())

            contractors = load_contractors()
            contractor_map = {c["name"]: c["id"] for c in contractors}
            contractor_labels = sorted(contractor_map.keys())

            contracts = load_contracts()
            contract_map = {
                f"{c['contract_title']} ({c['project_name']}) — {c['contractor_name']}": c["id"]
                for c in contracts
            }

            # Select Project (optional)
            selected_project_label = st.selectbox(
                "Select Project (optional)", ["All"] + project_labels
            )
            selected_project_id = None
            if selected_project_label != "All":
                selected_project_id = project_map[selected_project_label]

            # Filter contracts by project (if chosen)
            if selected_project_id:
                filtered_contracts = [
                    c for c in contracts if c["project_id"] == selected_project_id
                ]
            else:
                filtered_contracts = contracts

            # Build filtered map
            contract_map_filtered = {
                f"{c['contract_title']} ({c['project_name']}) — {c['contractor_name']}": c["id"]
                for c in filtered_contracts
            }

            # Select Contractor (optional)
            selected_contractor_label = st.selectbox(
                "Select Contractor (optional)", ["All"] + contractor_labels
            )
            selected_contractor_id = None
            if selected_contractor_label != "All":
                selected_contractor_id = contractor_map[selected_contractor_label]

            # Further filter by contractor
            if selected_contractor_id:
                filtered_contracts = [
                    c for c in filtered_contracts if c["contractor_id"] == selected_contractor_id
                ]
                contract_map_filtered = {
                    f"{c['contract_title']} ({c['project_name']}) — {c['contractor_name']}": c["id"]
                    for c in filtered_contracts
                }

            # Final “Select Contract” dropdown
            final_contract_labels = sorted(contract_map_filtered.keys())
            selected_contract_label = st.selectbox(
                "Select Contract", [""] + final_contract_labels
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

            # Status
            status_options = {
                "submitted": "submitted",
                "pending": "pending",
                "paid": "paid",
                "rejected": "rejected",
            }
            status_label = st.selectbox("Status", list(status_options.keys()), index=0)
            status_value = status_options[status_label]

            # HQ comments (only if can_edit)
            comments = ""
            if can_edit:
                comments = st.text_area("Comment for HQ (optional)")

            # File uploader
            attachments = st.file_uploader(
                "📎 Upload Attachments (PDF, JPG, PNG, DOCX)",
                accept_multiple_files=True,
                type=["pdf", "jpg", "jpeg", "png", "docx"],
            )

            if st.form_submit_button("Submit Request"):
                if not selected_contract_id:
                    st.warning("Please select a contract before submitting.")
                else:
                    try:
                        new_request_id = str(uuid.uuid4())
                        insert_payment_request(
                            request_id=new_request_id,
                            contract_id=selected_contract_id,
                            requested_by=user.get("id"),
                            amount_usd=amount_usd if amount_usd > 0 else None,
                            amount_iqd=amount_iqd if amount_iqd > 0 else None,
                            note=None,
                            requested_date=requested_date,
                            paid_date=paid_date if paid_date else None,
                            status=status_value,
                            comments=comments if comments else None,
                        )

                        upload_attachments(new_request_id, attachments)
                        st.success("✅ Payment request submitted successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to submit request: {e}")

        st.markdown("---")


# ────────────────────────────────────────────────────────────────────────────────
# 13) “Payment Request List” with Inline Editing & Attachments
# ────────────────────────────────────────────────────────────────────────────────
st.markdown("### 📄 Payment Request List")

if df.empty:
    st.info("No payment requests found for the selected filters.")
else:
    for idx, req in df.iterrows():
        header = (
            f"{req['contract_title']} — {req['status'].capitalize()} — "
            f"{pd.to_datetime(req['created_at']).strftime('%Y-%m-%d')}"
        )
        with st.expander(header, expanded=False):
            col1, col2 = st.columns([2, 1])

            # ──────────────────────────────────
            # Left column: Details + Inline Edit
            # ──────────────────────────────────
            with col1:
                st.markdown(f"**Contract:** {req['contract_title']}")
                st.markdown(f"**Project:** {req['project_name']}")
                st.markdown(f"**Contractor:** {req['contractor_name']}")
                st.markdown(f"**Requested By:** {req['requested_by_name'] or '—'}")
                st.markdown(
                    f"**Requested Date:** {pd.to_datetime(req['requested_date']).strftime('%Y-%m-%d')}"
                )
                paid_date_display = (
                    pd.to_datetime(req["paid_date"]).strftime("%Y-%m-%d")
                    if req["paid_date"] else "—"
                )
                st.markdown(f"**Paid Date:** {paid_date_display}")
                st.markdown(f"**Amount (USD):** {req['amount_usd'] or '—'}")
                st.markdown(f"**Amount (IQD):** {req['amount_iqd'] or '—'}")
                st.markdown(f"**Note:** {req['note'] or '—'}")
                st.markdown(f"**Comments:** {req['comments'] or '—'}")
                st.markdown(f"**Status:** {req['status'].capitalize()}")

                # Inline Edit Form (only if can_edit)
                if can_edit:
                    with st.form(f"edit_form_{req['id']}"):
                        st.markdown("### ✏️ Edit This Request")
                        new_amount_usd = st.number_input(
                            "Amount (USD)",
                            min_value=0.0,
                            value=float(req["amount_usd"] or 0.0),
                            step=0.01,
                            key=f"usd_edit_{req['id']}",
                        )
                        new_amount_iqd = st.number_input(
                            "Amount (IQD)",
                            min_value=0.0,
                            value=float(req["amount_iqd"] or 0.0),
                            step=1.0,
                            key=f"iqd_edit_{req['id']}",
                        )
                        new_note = st.text_area(
                            "Note / Description",
                            value=req["note"] or "",
                            key=f"note_edit_{req['id']}",
                        )
                        new_requested_date = st.date_input(
                            "Requested Date",
                            value=pd.to_datetime(req["requested_date"]).date(),
                            key=f"req_date_edit_{req['id']}",
                        )
                        new_paid_date = st.date_input(
                            "Paid Date (optional)",
                            value=(
                                pd.to_datetime(req["paid_date"]).date()
                                if req["paid_date"] else None
                            ),
                            key=f"paid_date_edit_{req['id']}",
                        )
                        new_status = st.selectbox(
                            "Status",
                            options=["submitted", "pending", "paid", "rejected"],
                            index=["submitted", "pending", "paid", "rejected"].index(
                                req["status"]
                            ),
                            key=f"status_edit_{req['id']}",
                        )
                        new_comments = st.text_area(
                            "Comment for HQ",
                            value=req["comments"] or "",
                            key=f"comments_edit_{req['id']}",
                        )

                        if st.form_submit_button("💾 Save Changes"):
                            try:
                                update_payment_request(
                                    request_id=req["id"],
                                    amount_usd=(
                                        new_amount_usd if new_amount_usd > 0 else None
                                    ),
                                    amount_iqd=(
                                        new_amount_iqd if new_amount_iqd > 0 else None
                                    ),
                                    note=new_note if new_note else None,
                                    requested_date=new_requested_date,
                                    paid_date=(
                                        new_paid_date if new_paid_date else None
                                    ),
                                    status=new_status,
                                    comments=new_comments if new_comments else None,
                                )
                                st.success("✅ Changes saved successfully.")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to save changes: {e}")

            # ──────────────────────────────────
            # Right column: Attachments + Actions
            # ──────────────────────────────────
            with col2:
                st.markdown("### 📎 Attachments")
                attachments = load_request_attachments(req["id"])
                if not attachments:
                    st.info("No attachments.")
                else:
                    for att in attachments:
                        a_col1, a_col2 = st.columns([5, 1])
                        with a_col1:
                            st.write(f"📄 {att['filename']} ({att['created_at'].strftime('%Y-%m-%d %H:%M')})")
                            # Fetch content for download
                            try:
                                conn = get_connection()
                                cur = conn.cursor(cursor_factory=RealDictCursor)
                                cur.execute(
                                    "SELECT content FROM payment_request_attachments WHERE id = %s",
                                    (att["id"],),
                                )
                                data_row = cur.fetchone()
                                conn.close()
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

                        with a_col2:
                            if can_delete:
                                if st.button("🗑️", key=f"del_att_{att['id']}"):
                                    try:
                                        delete_attachment(att["id"])
                                        st.success("Attachment deleted.")
                                        st.experimental_rerun()
                                    except Exception as e:
                                        st.error(f"❌ Could not delete attachment: {e}")

                # Upload more attachments if can_edit
                if can_edit:
                    st.markdown("➕ Add More Attachments")
                    more_files = st.file_uploader(
                        "Upload more files",
                        accept_multiple_files=True,
                        type=["pdf", "jpg", "jpeg", "png", "docx"],
                        key=f"more_upload_{req['id']}",
                    )
                    if st.button("Upload", key=f"upload_more_{req['id']}"):
                        if more_files:
                            try:
                                upload_attachments(req["id"], more_files)
                                st.success("New attachments uploaded!")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to upload attachments: {e}")
                        else:
                            st.warning("Please select files to upload.")

                st.markdown("---")

                # Mark as Paid (only if can_edit and status == 'submitted')
                if can_edit and req["status"] == "submitted":
                    if st.button("✅ Mark as Paid", key=f"mark_paid_{req['id']}"):
                        try:
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            cur3.execute(
                                """
                                UPDATE payment_requests
                                SET status = %s, paid_date = %s, updated_at = NOW()
                                WHERE id = %s
                                """,
                                ("paid", datetime.utcnow(), req["id"]),
                            )
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Request marked as paid.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to mark as paid: {e}")

                # Delete entire request (only if can_delete)
                if can_delete:
                    if st.button("🗑️ Delete Entire Request", key=f"del_req_{req['id']}"):
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            # Delete attachments first
                            cur2.execute(
                                "DELETE FROM payment_request_attachments WHERE payment_request_id = %s",
                                (req["id"],),
                            )
                            # Delete the request
                            cur2.execute(
                                "DELETE FROM payment_requests WHERE id = %s",
                                (req["id"],),
                            )
                            conn2.commit()
                            conn2.close()
                            st.success("✅ Payment request deleted.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"❌ Could not delete request: {e}")

            st.markdown("---")
