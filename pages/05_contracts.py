# 05_contracts.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import date, datetime

st.title("📄 Contracts")

# === DATABASE CONNECTION ===
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
            # Can view/add contracts for projects they manage; no delete, edit only if needed
            can_view = can_add = True
        elif role == "Site Accountant":
            # Only view contracts for projects they are assigned to
            can_view = True
        elif role == "HQ Accountant":
            # Can view all contracts, but no add/edit/delete
            can_view = True

    return can_view, can_add, can_edit, can_delete

# === FETCH CURRENT USER ===
user = st.session_state.get("user")
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, page="contracts")

# === SHOW ANIMATED “ACCESS DENIED” IF not can_view ===
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

# === LOAD “PROJECT” & “CONTRACTOR” LISTS FOR FORMS ===
@st.cache_data(ttl=120)
def load_projects_for_user(user_id: str, role: str):
    """
    Returns all projects if Super/HQ roles; 
    otherwise only projects assigned to this user.
    """
    conn = get_connection()
    cur = conn.cursor()
    if role in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("SELECT id, name FROM projects ORDER BY name;")
    else:
        # Site PM or Site Accountant: only show assigned projects
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
    """
    Returns a list of all contractors (id, name).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM contractors ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows

# Preload projects & contractors for the dropdowns
projects_list = load_projects_for_user(user.get("id"), user.get("role"))
contractors_list = load_contractors()

# === “ADD NEW CONTRACT” FORM ===
if can_add:
    with st.expander("➕ Add New Contract", expanded=True):
        with st.form("add_contract_form"):
            # Project dropdown
            project_options = {p["name"]: p["id"] for p in projects_list}
            selected_proj = st.selectbox("Project", list(project_options.keys()))

            # Contractor dropdown
            contractor_options = {c["name"]: c["id"] for c in contractors_list}
            selected_contractor = st.selectbox("Contractor", list(contractor_options.keys()))

            contract_value = st.number_input("Contract Value (e.g. 10000.00)", min_value=0.0, step=100.0, format="%.2f")
            start_date = st.date_input("Start Date", value=date.today())
            end_date = st.date_input("End Date", value=date.today())
            status = st.selectbox("Status", ["Pending", "Signed", "In Progress", "Completed", "On Hold"])
            scope = st.text_area("Scope / Description", help="Describe the main scope of work.")

            if st.form_submit_button("Add Contract"):
                if not selected_proj or not selected_contractor:
                    st.warning("Please select both a project and a contractor.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO contracts (
                                id, project_id, contractor_id, contract_value,
                                start_date, end_date, status, scope, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """, (
                            str(uuid.uuid4()),
                            project_options[selected_proj],
                            contractor_options[selected_contractor],
                            contract_value,
                            start_date,
                            end_date,
                            status,
                            scope,
                            datetime.utcnow()
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Contract added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

# === “SEARCH CONTRACTS” & LIST ===
st.markdown("### 📋 Contract List")
try:
    conn = get_connection()
    cur = conn.cursor()

    # Determine which contracts to fetch:
    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        # All contracts (Superadmin, HQ Admin, HQ Accountant)
        cur.execute("""
            SELECT 
                c.id, 
                p.name AS project_name, 
                t.name AS contractor_name, 
                c.contract_value, 
                c.start_date, 
                c.end_date, 
                c.status, 
                c.scope, 
                c.created_at
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            ORDER BY c.created_at DESC;
        """)
    else:
        # Site PM or Site Accountant: only contracts for their assigned projects
        cur.execute("""
            SELECT 
                c.id, 
                p.name AS project_name, 
                t.name AS contractor_name, 
                c.contract_value, 
                c.start_date, 
                c.end_date, 
                c.status, 
                c.scope, 
                c.created_at
            FROM contracts c
            JOIN projects p ON c.project_id = p.id
            JOIN contractors t ON c.contractor_id = t.id
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY c.created_at DESC;
        """, (user.get("id"),))
    contracts = cur.fetchall()
    conn.close()

    # === SEARCH BAR ===
    search_term = st.text_input("🔍 Search by project or contractor name").strip().lower()

    # === FILTER LOGIC ===
    filtered_list = [
        c for c in contracts
        if search_term in (c["project_name"] or "").lower()
        or search_term in (c["contractor_name"] or "").lower()
    ]

    if not filtered_list:
        st.info("No matching contracts found.")
    else:
        # Display each contract in an expander
        for c in filtered_list:
            header_label = f"{c['project_name']}  ➔  {c['contractor_name']}  ({c['status']})"
            with st.expander(header_label):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Scope / Description:**  {c['scope'] or '—'}")
                    st.markdown(f"**Value:**  {c['contract_value']:,}")
                    st.markdown(f"**Start Date:**  {c['start_date']}")
                    st.markdown(f"**End Date:**  {c['end_date']}")
                    st.markdown(f"**Created At:**  {c['created_at']}")

                    # Edit form if allowed
                    if can_edit:
                        with st.form(f"edit_contract_{c['id']}"):
                            new_status = st.selectbox(
                                "Status",
                                ["Pending", "Signed", "In Progress", "Completed", "On Hold"],
                                index=["Pending", "Signed", "In Progress", "Completed", "On Hold"].index(c["status"]),
                                key=f"status_{c['id']}"
                            )
                            new_scope = st.text_area(
                                "Scope / Description",
                                c["scope"],
                                key=f"scope_{c['id']}"
                            )
                            new_value = st.number_input(
                                "Contract Value",
                                value=float(c["contract_value"]),
                                min_value=0.0,
                                step=100.0,
                                format="%.2f",
                                key=f"value_{c['id']}"
                            )
                            new_start = st.date_input("Start Date", value=c["start_date"], key=f"sd_{c['id']}")
                            new_end = st.date_input("End Date", value=c["end_date"], key=f"ed_{c['id']}")

                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    cur2.execute("""
                                        UPDATE contracts
                                        SET status=%s, scope=%s, contract_value=%s, start_date=%s, end_date=%s
                                        WHERE id=%s;
                                    """, (
                                        new_status,
                                        new_scope,
                                        new_value,
                                        new_start,
                                        new_end,
                                        c["id"]
                                    ))
                                    conn2.commit()
                                    conn2.close()
                                    st.success("✅ Contract updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Update failed: {e}")
                    else:
                        # If read-only for this role, just display all fields
                        pass

                with col2:
                    # “Delete” button if allowed
                    if can_delete and st.button("🗑️ Delete", key=f"del_{c['id']}"):
                        try:
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            cur3.execute("DELETE FROM contracts WHERE id = %s;", (c["id"],))
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Contract deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")
except Exception as e:
    st.error(f"Failed to load contracts: {e}")
