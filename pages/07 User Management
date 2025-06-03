import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import hashlib

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

# === Add New User ===
st.subheader("➕ Add New User")
with st.form("add_user_form"):
    username = st.text_input("Username")
    full_name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Site PM", "Site Accountant", "HQ Accountant", "HQ Admin"])

    projects = load_projects()
    project_map = {f"{p['name']}": p["id"] for p in projects}
    assign_projects = st.multiselect("Assign Projects", list(project_map.keys())) if role in ["Site PM", "Site Accountant"] else []

    submitted = st.form_submit_button("Create User")
    if submitted:
        if not username or not password:
            st.warning("Username and password are required.")
        else:
            try:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                conn = get_connection()
                cur = conn.cursor()
                user_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO users (id, username, full_name, password, role)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, username, full_name, hashed_password, role))

                for p in assign_projects:
                    cur.execute("""
                        INSERT INTO user_projects (user_id, project_id)
                        VALUES (%s, %s)
                    """, (user_id, project_map[p]))

                conn.commit()
                conn.close()
                st.success("✅ User created successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create user: {e}")

# === List Users ===
st.subheader("📋 All Users")
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.full_name, u.role, array_agg(p.name) AS projects
        FROM users u
        LEFT JOIN user_projects up ON u.id = up.user_id
        LEFT JOIN projects p ON up.project_id = p.id
        GROUP BY u.id
        ORDER BY u.username
    """)
    users = cur.fetchall()
    conn.close()

    for u in users:
        with st.expander(f"👤 {u['username']} ({u['role']})"):
            st.markdown(f"**Full Name:** {u['full_name']}")
            st.markdown(f"**Role:** {u['role']}")
            st.markdown(f"**Projects:** {', '.join([p for p in u['projects'] if p]) or '—'}")

            col1, col2 = st.columns(2)
            with col1:
                new_password = st.text_input(f"Reset Password for {u['username']}", type="password", key=f"pw_{u['id']}")
                if st.button("🔑 Reset Password", key=f"reset_{u['id']}"):
                    if new_password:
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
                            cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, u["id"]))
                            conn.commit()
                            conn.close()
                            st.success("✅ Password updated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update password: {e}")
                    else:
                        st.warning("Please enter a new password.")

            with col2:
                if st.button("🗑️ Delete User", key=f"del_{u['id']}") and user.get("role") == "Superadmin":
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM user_projects WHERE user_id = %s", (u["id"],))
                        cur.execute("DELETE FROM users WHERE id = %s", (u["id"],))
                        conn.commit()
                        conn.close()
                        st.success("✅ User deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to delete user: {e}")
except Exception as e:
    st.error(f"❌ Failed to load users: {e}")
