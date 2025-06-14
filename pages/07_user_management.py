import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import hashlib
import pandas as pd

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

# === Load Projects ===
@st.cache_data
def load_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

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
        assign_projects = st.multiselect(
            "Assign Projects", list(project_map.keys())
        )

    if st.form_submit_button("Create User"):
        if not username or not password:
            st.warning("Username and password are required.")
        else:
            try:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                conn = get_connection()
                cur = conn.cursor()
                user_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO users (id, username, full_name, hashed_password, role, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, username, full_name, hashed_password, new_role, datetime.utcnow())
                )
                # Assign projects
                cur.execute("DELETE FROM user_projects WHERE user_id = %s", (user_id,))
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
    df = pd.DataFrame(rows, columns=["id","username","full_name","role","projects","created_at"])
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

try:
    users = df.itertuples(index=False)
    for u in users:
        exp = st.expander(f"👤 {u.username} ({u.role})")
        with exp:
            col1, col2 = st.columns([3,1])
            with col1:
                # Inline edit form
                with st.form(f"edit_user_{u.id}"):
                    edit_full_name = st.text_input("Full Name", u.full_name)
                    edit_role = st.selectbox("Role", ALL_ROLES, index=ALL_ROLES.index(u.role))
                    edit_projects = st.multiselect(
                        "Projects",
                        list(project_map.keys()),
                        default=u.projects.split(', ') if u.projects else []
                    )
                    update_btn = st.form_submit_button("💾 Save Changes")
                    if update_btn:
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute(
                                "UPDATE users SET full_name = %s, role = %s WHERE id = %s",
                                (edit_full_name, edit_role, u.id)
                            )
                            cur2.execute("DELETE FROM user_projects WHERE user_id = %s", (u.id,))
                            for proj in edit_projects:
                                cur2.execute(
                                    "INSERT INTO user_projects (user_id, project_id) VALUES (%s, %s)",
                                    (u.id, project_map[proj])
                                )
                            conn2.commit()
                            conn2.close()
                            st.success("✅ User updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update user: {e}")
            with col2:
                # Reset password
                new_pw = st.text_input("Reset Password", type="password", key=f"pw_{u.id}")
                if st.button("🔑 Reset", key=f"reset_{u.id}"):
                    if new_pw:
                        try:
                            conn3 = get_connection()
                            cur3 = conn3.cursor()
                            new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
                            cur3.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (new_hash, u.id))
                            conn3.commit()
                            conn3.close()
                            st.success("✅ Password updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update password: {e}")
                    else:
                        st.warning("Enter a new password to reset.")
                # Delete user
                if role == "Superadmin" and st.button("🗑️ Delete", key=f"del_{u.id}"):
                    try:
                        conn4 = get_connection()
                        cur4 = conn4.cursor()
                        cur4.execute("DELETE FROM user_projects WHERE user_id = %s", (u.id,))
                        cur4.execute("DELETE FROM users WHERE id = %s", (u.id,))
                        conn4.commit()
                        conn4.close()
                        st.success("✅ User deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete user: {e}")
except Exception as e:
    st.error(f"❌ Failed to load users: {e}")
