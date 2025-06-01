import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import date, datetime

st.title("🏗️ Projects")

def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False
    if page == "projects":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role in ["Site Accountant", "HQ Accountant"]:
            can_view = True
    return can_view, can_add, can_edit, can_delete

# === Load user ===
user = st.session_state.get("user")
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, page="projects")

# === Show access denied if not allowed ===
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

# === Add Project ===
if can_add:
    with st.expander("➕ Add New Project", expanded=True):
        with st.form("add_project_form"):
            name = st.text_input("Project Name", max_chars=100)
            location = st.text_input("Location")
            start_date = st.date_input("Start Date", value=date.today())
            end_date = st.date_input("End Date", value=date.today())
            status = st.selectbox("Status", ["Planned", "Ongoing", "Completed", "On Hold"])

            if st.form_submit_button("Add Project"):
                if not name:
                    st.warning("Project name is required.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO projects (id, name, location, start_date, end_date, status, created_by, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            str(uuid.uuid4()), name, location, start_date, end_date, status,
                            user.get("username", "unknown"), datetime.utcnow()
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Project added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

# === Load Projects ===
st.markdown("### 📋 Project List")
try:
    conn = get_connection()
    cur = conn.cursor()

    if user.get("role") in ["Superadmin", "HQ Admin", "HQ Accountant"]:
        cur.execute("SELECT * FROM projects ORDER BY created_at DESC")
        projects = cur.fetchall()
    else:
        # Show only assigned projects
        cur.execute("""
            SELECT p.*
            FROM projects p
            JOIN project_assignments pa ON p.id = pa.project_id
            WHERE pa.user_id = %s
            ORDER BY p.created_at DESC
        """, (user.get("id"),))
        projects = cur.fetchall()

    conn.close()

    search_term = st.text_input("🔍 Search projects by name or location").strip().lower()
    filtered = [
        p for p in projects if
        search_term in (p["name"] or "").lower()
        or search_term in (p["location"] or "").lower()
    ]

    if not filtered:
        st.info("No matching projects found.")
    else:
        for p in filtered:
            with st.expander(f"🏗️ {p['name']} ({p['status']})"):
                col1, col2 = st.columns([4, 1])

                with col1:
                    if can_edit:
                        with st.form(f"edit_{p['id']}"):
                            name = st.text_input("Name", p["name"], key=f"name_{p['id']}")
                            loc = st.text_input("Location", p["location"] or "", key=f"loc_{p['id']}")
                            s_date = st.date_input("Start Date", value=p["start_date"], key=f"sd_{p['id']}")
                            e_date = st.date_input("End Date", value=p["end_date"], key=f"ed_{p['id']}")
                            stat = st.selectbox("Status", ["Planned", "Ongoing", "Completed", "On Hold"],
                                                index=["Planned", "Ongoing", "Completed", "On Hold"].index(p["status"]),
                                                key=f"st_{p['id']}")
                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    cur2.execute("""
                                        UPDATE projects
                                        SET name=%s, location=%s, start_date=%s, end_date=%s, status=%s
                                        WHERE id=%s
                                    """, (name, loc, s_date, e_date, stat, p['id']))
                                    conn2.commit()
                                    conn2.close()
                                    st.success("✅ Project updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Update failed: {e}")
                    else:
                        st.markdown(f"**Location**: {p['location'] or '—'}")
                        st.markdown(f"**Start Date**: {p['start_date']}")
                        st.markdown(f"**End Date**: {p['end_date']}")
                        st.markdown(f"**Status**: {p['status']}")

                with col2:
                    if can_delete and st.button("🗑️ Delete", key=f"del_{p['id']}"):
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute("DELETE FROM projects WHERE id = %s", (p['id'],))
                            conn2.commit()
                            conn2.close()
                            st.success("✅ Deleted successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")
except Exception as e:
    st.error(f"Failed to load projects: {e}")
