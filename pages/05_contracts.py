# 05_contracts.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import Binary
import uuid
from datetime import date, datetime

st.title("📄 Contracts")

# ===  DATABASE CONNECTION ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === ROLE-BASED ACCESS FLAGS ===
def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False

    if page == "contracts":
        if role in ["Superadmin", "HQ Admin"]:
            # Full rights
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            # Can view/add contracts (but no delete)
            can_view = can_add = True
        elif role in ["Site Accountant", "HQ Accountant"]:
            # Only view contracts
            can_view = True

    return can_view, can_add, can_edit, can_delete

# === LOAD CURRENT USER ===
user = st.session_state.get("user")
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, "contracts")

# === ACCESS DENIED ANIMATION IF NO PERMISSION ===
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
        unsafe_allow_html=True
    )
    st.stop()

# === HELPER FUNCTIONS TO LOAD DROPDOWNS ===
@st.cache_data(ttl=120)
def load_projects_for_user(user_id: str, role: str):
    """
    Returns (id, name) of all projects if Super/HQ roles;
    otherwise only projects assigned to this user.
    """
    conn = get_connection()
    cur = conn.cursor()
    if role in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("SELECT id, name FROM projects ORDER BY name;")
    else:
        cur.execute(
            """
            SELECT p.id, p.name
            FROM projects p
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY p.name;
            """,
            (user_id,)
        )
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=120)
def load_contractors():
    """
    Returns (id, name) of all contractors.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM contractors ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows

projects_list = load_projects_for_user(user.get("id"), user.get("role"))
contractors_list = load_contractors()

# === ADD NEW CONTRACT FORM ===
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
                        cur.execute(
                            """
                            INSERT INTO contracts (
                                id, title, project_id, contractor_id,
                                contract_value_usd, contract_value_iqd,
                                start_date, end_date, status, scope, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                str(uuid.uuid4()),            # id
                                title,                        # title
                                project_map[selected_proj],   # project_id
                                contractor_map[selected_contractor],  # contractor_id
                                value_usd if value_usd else None,
                                value_iqd if value_iqd else None,
                                start_date,
                                end_date,
                                status,
                                scope,
                                datetime.utcnow()
                            )
                        )
                        conn.commit()
                        conn.close()
                        st.success("✅ Contract added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

# === CONTRACT LIST ===
st.markdown("### 📋 Contract List")
try:
    conn = get_connection()
    cur = conn.cursor()

    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute(
            """
            SELECT c.*, p.name AS project_name, t.name AS contractor_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            ORDER BY c.created_at DESC;
            """
        )
    else:
        cur.execute(
            """
            SELECT c.*, p.name AS project_name, t.name AS contractor_name
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY c.created_at DESC;
            """,
            (user.get("id"),)
        )

    contracts = cur.fetchall()
    conn.close()

    search_term = st.text_input("🔍 Search by title, project, or contractor").strip().lower()

    filtered = [
        c for c in contracts
        if search_term in (c["title"] or "").lower()
        or search_term in (c["project_name"] or "").lower()
        or search_term in (c["contractor_name"] or "").lower()
    ]

    if not filtered:
        st.info("No matching contracts found.")
    else:
        for c in filtered:
            label = f"{c['title']}  ({c['project_name']} ➔ {c['contractor_name']})"
            with st.expander(label):
                col1, col2 = st.columns([4, 1])

                # --- Left Column: Show Contract Details & Edit Form ---
                with col1:
                    st.markdown(f"**Scope / Description:**  {c['scope'] or '—'}")
                    st.markdown(f"**Status:**  {c['status']}")
                    st.markdown(f"**Start Date:**  {c['start_date']}")
                    st.markdown(f"**End Date:**  {c['end_date']}")
                    usd_display = f"${c['contract_value_usd']:,.2f}" if c["contract_value_usd"] else "—"
                    iqd_display = f"{int(c['contract_value_iqd']):,} IQD" if c["contract_value_iqd"] else "—"
                    st.markdown(f"**Value (USD):**  {usd_display}")
                    st.markdown(f"**Value (IQD):**  {iqd_display}")
                    st.markdown(f"**Created At:**  {c['created_at']}")

                    # --- Edit Form (if allowed) ---
                    if can_edit:
                        st.markdown("---")
                        with st.form(f"edit_contract_{c['id']}"):
                            new_title = st.text_input("Contract Title", c["title"], key=f"title_{c['id']}")
                            new_status = st.selectbox(
                                "Status",
                                ["Pending", "Signed", "In Progress", "Completed", "On Hold"],
                                index=["Pending", "Signed", "In Progress", "Completed", "On Hold"].index(c["status"]),
                                key=f"status_{c['id']}"
                            )
                            new_scope = st.text_area("Scope / Description", c["scope"] or "", key=f"scope_{c['id']}")
                            new_value_usd = st.number_input(
                                "Value in USD ($)",
                                value=float(c["contract_value_usd"] or 0.0),
                                min_value=0.0,
                                step=100.0,
                                format="%.2f",
                                key=f"usd_{c['id']}"
                            )
                            new_value_iqd = st.number_input(
                                "Value in IQD (ع.د)",
                                value=float(c["contract_value_iqd"] or 0.0),
                                min_value=0.0,
                                step=100000.0,
                                format="%.0f",
                                key=f"iqd_{c['id']}"
                            )
                            new_start = st.date_input("Start Date", value=c["start_date"], key=f"sd_{c['id']}")
                            new_end = st.date_input("End Date", value=c["end_date"], key=f"ed_{c['id']}")

                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    cur2.execute(
                                        """
                                        UPDATE contracts
                                        SET title = %s,
                                            status = %s,
                                            scope = %s,
                                            contract_value_usd = %s,
                                            contract_value_iqd = %s,
                                            start_date = %s,
                                            end_date = %s
                                        WHERE id = %s;
                                        """,
                                        (
                                            new_title,
                                            new_status,
                                            new_scope,
                                            new_value_usd or None,
                                            new_value_iqd or None,
                                            new_start,
                                            new_end,
                                            c["id"]
                                        )
                                    )
                                    conn2.commit()
                                    conn2.close()
                                    st.success("✅ Contract updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Update failed: {e}")

                # --- Right Column: Delete Button & Attachments Section ---
                with col2:
                    # Delete Contract
                    if can_delete and st.button("🗑️ Delete Contract", key=f"del_{c['id']}"):
                        try:
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            cur3.execute("DELETE FROM contracts WHERE id = %s;", (c["id"],))
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Contract deleted successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")

                    # --- UPLOAD ATTACHMENT (if allowed) ---
                    if can_add or can_edit:
                        st.markdown("---")
                        st.write("#### 📎 Attachments")
                        uploaded_file = st.file_uploader(
                            "Upload a file (PDF, DOCX, image, etc.)",
                            type=None,
                            key=f"upload_{c['id']}"
                        )
                        if uploaded_file is not None:
                            file_bytes = uploaded_file.read()
                            file_name = uploaded_file.name
                            file_type = uploaded_file.type

                            try:
                                conn4 = get_connection()
                                cur4 = conn4.cursor()
                                cur4.execute(
                                    """
                                    INSERT INTO contract_attachments (
                                        id, contract_id, file_name, file_type, file_data, uploaded_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s);
                                    """,
                                    (
                                        str(uuid.uuid4()),
                                        c["id"],
                                        file_name,
                                        file_type,
                                        Binary(file_bytes),
                                        datetime.utcnow()
                                    )
                                )
                                conn4.commit()
                                conn4.close()
                                st.success("📎 Attachment uploaded successfully")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Failed to upload attachment: {e}")

                        # --- LIST EXISTING ATTACHMENTS ---
                        try:
                            conn5 = get_connection()
                            cur5 = conn5.cursor()
                            cur5.execute(
                                """
                                SELECT id, file_name, file_type, file_data
                                FROM contract_attachments
                                WHERE contract_id = %s
                                ORDER BY uploaded_at DESC;
                                """,
                                (c["id"],)
                            )
                            attachments = cur5.fetchall()
                            conn5.close()

                            for att in attachments:
                                att_name = att["file_name"]
                                att_data = att["file_data"]
                                att_type = att["file_type"] or "application/octet-stream"

                                # Download button for each attachment
                                st.download_button(
                                    label=f"⬇️ {att_name}",
                                    data=att_data,
                                    file_name=att_name,
                                    mime=att_type,
                                    key=f"download_{att['id']}"
                                )

                        except Exception as e:
                            st.error(f"Failed to load attachments: {e}")

except Exception as e:
    st.error(f"Failed to load contracts: {e}")
