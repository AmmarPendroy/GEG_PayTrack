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
                user_id = str(uuid.uuid4())

                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO users (id, username, full_name, role, hashed_password)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, username, full_name, role, hashed_password))

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

# === Export Users ===
st.subheader("📤 Export Users")
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.username, u.full_name, u.role, array_to_string(array_agg(p.name), ', ') AS projects
        FROM users u
        LEFT JOIN user_projects up ON u.id = up.user_id
        LEFT JOIN projects p ON up.project_id = p.id
        GROUP BY u.id
        ORDER BY u.username
    """)
    df_users = pd.DataFrame(cur.fetchall())
    conn.close()
    csv = df_users.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Users as CSV", csv, "users.csv", "text/csv")
except Exception as e:
    st.error(f"Failed to export users: {e}")

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

    projects = load_projects()
    project_map = {p['name']: p['id'] for p in projects}
    project_names = list(project_map.keys())

    for u in users:
        with st.expander(f"👤 {u['username']} ({u['role']})"):
            st.markdown(f"**Full Name:** {u['full_name']}")
            current_role = st.selectbox("Role", ["Site PM", "Site Accountant", "HQ Accountant", "HQ Admin"], index=["Site PM", "Site Accountant", "HQ Accountant", "HQ Admin"].index(u['role']), key=f"role_{u['id']}")
            assigned_projects = st.multiselect("Projects", project_names, default=[p for p in u['projects'] if p], key=f"proj_{u['id']}")

            if st.button("💾 Save Changes", key=f"save_{u['id']}"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET role = %s WHERE id = %s", (current_role, u["id"]))
                    cur.execute("DELETE FROM user_projects WHERE user_id = %s", (u["id"],))
                    for proj in assigned_projects:
                        cur.execute("INSERT INTO user_projects (user_id, project_id) VALUES (%s, %s)", (u["id"], project_map[proj]))
                    conn.commit()
                    conn.close()
                    st.success("✅ User updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to update user: {e}")

            col1, col2 = st.columns(2)
            with col1:
                new_password = st.text_input(f"Reset Password for {u['username']}", type="password", key=f"pw_{u['id']}")
                if st.button("🔑 Reset Password", key=f"reset_{u['id']}"):
                    if new_password:
                        try:
                            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE users SET hashed_password = %s WHERE id = %s", (new_hash, u["id"]))
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
