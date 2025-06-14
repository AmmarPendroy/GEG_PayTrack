import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import hashlib
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="👥 User Management", layout="wide")
st.title("👥 User Management")

# === Permissions ===
user = st.session_state.get("user", {})
role = user.get("role", "")
if role not in ["Superadmin", "HQ Admin"]:
    st.error("⛔ You do not have permission to view this page.")
    st.stop()

# === DB Connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Load Projects (always fresh) ===
def load_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

# === Load Users as DataFrame ===
@st.cache_data
def load_users_df():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id, u.username, u.full_name, u.role,
               COALESCE(string_agg(p.name, ', '), '') AS projects,
               u.created_at
        FROM users u
        LEFT JOIN user_projects up ON u.id = up.user_id
        LEFT JOIN projects p ON up.project_id = p.id
        GROUP BY u.id
        ORDER BY u.username
        """
    )
    rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["id", "username", "full_name", "role", "projects", "created_at"])

# === Role List ===
ALL_ROLES = ["Superadmin", "HQ Admin", "HQ Accountant", "Site Accountant", "Site PM"]

# === Add New User ===
st.subheader("➕ Add New User")
with st.form("add_user_form"):
    username = st.text_input("Username")
    full_name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")
    new_role = st.selectbox("Role", ALL_ROLES, index=ALL_ROLES.index("Site PM"))

    projects = load_projects()
    project_map = {p['name']: p['id'] for p in projects}
    assign_projects = []
    if new_role in ["Site PM", "Site Accountant"]:
        assign_projects = st.multiselect("Assign Projects", list(project_map.keys()))

    if st.form_submit_button("Create User"):
        if not username or not password:
            st.warning("Username and password are required.")
        else:
            try:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                user_id = str(uuid.uuid4())
                conn = get_connection()
                cur = conn.cursor()
                # Insert user
                cur.execute(
                    """
                    INSERT INTO users (id, username, full_name, hashed_password, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, username, full_name, hashed_password, new_role, datetime.utcnow())
                )
                # Assign projects
                for proj in assign_projects:
                    cur.execute(
                        "INSERT INTO user_projects (user_id, project_id) VALUES (%s, %s)",
                        (user_id, project_map[proj])
                    )
                conn.commit()
                conn.close()
                st.success("✅ User created successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create user: {e}")

# === Export Users ===
st.markdown("---")
st.subheader("📤 Export Users")
try:
    df = load_users_df()
    csv_data = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Users as CSV",
        data=csv_data,
        file_name="users_export.csv",
        mime="text/csv"
    )
except Exception as e:
    st.error(f"❌ Failed to export users: {e}")

# === List & Inline Edit Users ===
st.markdown("---")
st.subheader("📋 All Users")

projects = load_projects()
project_map = {p['name']: p['id'] for p in projects}

try:
    df_list = load_users_df()
    for row in df_list.itertuples(index=False):
        with st.expander(f"👤 {row.username} ({row.role})"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"edit_user_{row.id}"):
                    edit_full_name = st.text_input("Full Name", row.full_name)
                    edit_role = st.selectbox("Role", ALL_ROLES, index=ALL_ROLES.index(row.role))
                    edit_projects = st.multiselect(
                        "Projects", list(project_map.keys()),
                        default=row.projects.split(', ') if row.projects else []
                    )
                    if st.form_submit_button("💾 Save Changes"):
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute(
                                "UPDATE users SET full_name = %s, role = %s WHERE id = %s",
                                (edit_full_name, edit_role, row.id)
                            )
                            cur2.execute("DELETE FROM user_projects WHERE user_id = %s", (row.id,))
                            for proj in edit_projects:
                                cur2.execute(
                                    "INSERT INTO user_projects (user_id, project_id) VALUES (%s, %s)",
                                    (row.id, project_map[proj])
                                )
                            conn2.commit()
                            conn2.close()
                            st.success("✅ User updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update user: {e}")
            with col2:
                new_pw = st.text_input("Reset Password", type="password", key=f"pw_{row.id}")
                if st.button("🔑 Reset", key=f"reset_{row.id}"):
                    if new_pw:
                        try:
                            new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            cur3.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (new_hash, row.id))
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Password updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update password: {e}")
                    else:
                        st.warning("Enter a new password to reset.")
                if role == "Superadmin" and st.button("🗑️ Delete", key=f"del_{row.id}"):
                    try:
                        conn4 = get_connection()
                        cur4 = conn4.cursor()
                        cur4.execute("DELETE FROM user_projects WHERE user_id = %s", (row.id,))
                        cur4.execute("DELETE FROM users WHERE id = %s", (row.id,))
                        conn4.commit()
                        conn4.close()
                        st.success("✅ User deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete user: {e}")
except Exception as e:
    st.error(f"❌ Failed to load users: {e}")
