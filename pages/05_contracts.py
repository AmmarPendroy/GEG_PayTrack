# 05_contracts.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import date, datetime

st.title("📄 Contracts")

# === DB Connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Access Flags ===
def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False
    if page == "contracts":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role in ["Site Accountant", "HQ Accountant"]:
            can_view = True
    return can_view, can_add, can_edit, can_delete

# === Load user ===
user = st.session_state.get("user")
if not isinstance(user, dict): user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, "contracts")

# === Access Denied ===
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

# === Helper: Load Projects and Contractors ===
@st.cache_data(ttl=120)
def load_projects_for_user(user_id: str, role: str):
    conn = get_connection()
    cur = conn.cursor()
    if role in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("SELECT id, name FROM projects ORDER BY name;")
    else:
        cur.execute("""
            SELECT p.id, p.name
            FROM projects p
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY p.name;
        """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=120)
def load_contractors():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM contractors ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows

projects_list = load_projects_for_user(user.get("id"), user.get("role"))
contractors_list = load_contractors()

# === Add New Contract Form ===
if can_add:
    with st.expander("➕ Add New Contract", expanded=True):
        with st.form("add_contract_form"):
            title = st.text_input("Contract Title", max_chars=100)
            project_map = {p["name"]: p["id"] for p in projects_list}
            contractor_map = {c["name"]: c["id"] for c in contractors_list}
            selected_proj = st.selectbox("Project", list(project_map.keys()))
            selected_contractor = st.selectbox("Contractor", list(contractor_map.keys()))
            value_usd = st.number_input("Value in USD ($)", min_value=0.0, step=100.0, format="%.2f")
            value_iqd = st.number_input("Value in IQD (ع.د)", min_value=0.0, step=100000.0, format="%.0f")
            start_date = st.date_input("Start Date", value=date.today())
            end_date = st.date_input("End Date", value=date.today())
            status = st.selectbox("Status", ["Pending", "Signed", "In Progress", "Completed", "On Hold"])
            scope = st.text_area("Scope / Description")

            if st.form_submit_button("Add Contract"):
                if not title or not selected_proj or not selected_contractor:
                    st.warning("Title, Project, and Contractor are required.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO contracts (
                                id, title, project_id, contractor_id,
                                contract_value_usd, contract_value_iqd,
                                start_date, end_date, status, scope, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            str(uuid.uuid4()), title,
                            project_map[selected_proj],
                            contractor_map[selected_contractor],
                            value_usd or None, value_iqd or None,
                            start_date, end_date, status, scope, datetime.utcnow()
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Contract added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

# === Contract List ===
st.markdown("### 📋 Contract List")
try:
    conn = get_connection()
    cur = conn.cursor()
    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("""
            SELECT c.*, p.name AS project_name, t.name AS contractor_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            ORDER BY c.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT c.*, p.name AS project_name, t.name AS contractor_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY c.created_at DESC
        """, (user.get("id"),))
    contracts = cur.fetchall()
    conn.close()

    search_term = st.text_input("🔍 Search by project, contractor, or title").strip().lower()
    filtered = [
        c for c in contracts if
        search_term in (c["title"] or "").lower()
        or search_term in (c["project_name"] or "").lower()
        or search_term in (c["contractor_name"] or "").lower()
    ]

    if not filtered:
        st.info("No matching contracts found.")
    else:
        for c in filtered:
            label = f"{c['title']} ({c['project_name']} ➔ {c['contractor_name']})"
            with st.expander(label):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**Scope:** {c['scope'] or '—'}")
                    st.markdown(f"**Status:** {c['status']}")
                    st.markdown(f"**Start Date:** {c['start_date']}")
                    st.markdown(f"**End Date:** {c['end_date']}")
                    usd = f"${c['contract_value_usd']:,.2f}" if c["contract_value_usd"] else "—"
                    iqd = f"{int(c['contract_value_iqd']):,} IQD" if c["contract_value_iqd"] else "—"
                    st.markdown(f"**Value (USD):** {usd}")
                    st.markdown(f"**Value (IQD):** {iqd}")

                    # === Upload Attachments ===
                    if can_edit or can_add:
                        with st.form(f"upload_file_{c['id']}"):
                            uploaded_files = st.file_uploader(
                                "📎 Upload Attachments",
                                type=["pdf", "docx", "jpg", "png"],
                                accept_multiple_files=True,
                                key=f"file_{c['id']}"
                            )
                            if st.form_submit_button("Upload") and uploaded_files:
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    for uploaded_file in uploaded_files:
                                        cur2.execute("""
                                            INSERT INTO contract_attachments (
                                                id, contract_id, file_name, file_type, file_data
                                            ) VALUES (%s, %s, %s, %s, %s)
                                        """, (
                                            str(uuid.uuid4()),
                                            c["id"],
                                            uploaded_file.name,
                                            uploaded_file.type,
                                            uploaded_file.read()
                                        ))
                                    conn2.commit()
                                    conn2.close()
                                    st.success("✅ File(s) uploaded successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Upload failed: {e}")

                    # === List Existing Attachments (no nested expanders) ===
                    try:
                        conn3 = get_connection()
                        cur3 = conn3.cursor()
                        cur3.execute("""
                            SELECT id, file_name, file_type, uploaded_at
                            FROM contract_attachments
                            WHERE contract_id = %s
                            ORDER BY uploaded_at DESC
                        """, (c["id"],))
                        attachments = cur3.fetchall()
                        conn3.close()

                        if attachments:
                            st.markdown("**📁 Attachments:**")
                            for file in attachments:
                                # Retrieve binary data
                                conn4 = get_connection()
                                cur4 = conn4.cursor()
                                cur4.execute(
                                    "SELECT file_data FROM contract_attachments WHERE id = %s",
                                    (file["id"],)
                                )
                                file_data = cur4.fetchone()["file_data"]
                                conn4.close()

                                st.markdown(
                                    f"📄 **{file['file_name']}** "
                                    f"({file['file_type']}) — "
                                    f"{file['uploaded_at'].strftime('%Y-%m-%d %H:%M')}"
                                )
                                st.download_button(
                                    label="⬇️ Download File",
                                    data=file_data,
                                    file_name=file["file_name"],
                                    mime=file["file_type"],
                                    key=f"dl_{file['id']}"
                                )
                                # Delete attachment button
                                if can_delete and st.button(
                                    "🗑️ Delete Attachment", key=f"del_att_{file['id']}"
                                ):
                                    try:
                                        conn5 = get_connection()
                                        cur5 = conn5.cursor()
                                        cur5.execute(
                                            "DELETE FROM contract_attachments WHERE id = %s",
                                            (file["id"],)
                                        )
                                        conn5.commit()
                                        conn5.close()
                                        st.success("🗑️ Attachment deleted")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to delete attachment: {e}")

                                # Divider between attachments
                                st.divider()
                    except Exception as e:
                        st.error(f"Failed to load attachments: {e}")

                with col2:
                    if can_delete and st.button("🗑️ Delete Contract", key=f"del_{c['id']}"):
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute("DELETE FROM contracts WHERE id = %s", (c["id"],))
                            conn2.commit()
                            conn2.close()
                            st.success("✅ Contract deleted successfully") 
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")
except Exception as e:
    st.error(f"Failed to load contracts: {e}")
