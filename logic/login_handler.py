import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_controller import CookieController

# ─── COOKIE CONTROLLER ────────────────────────────────────────────────────────────
controller = CookieController()
# must do before any UI:
controller.get_all()  # hydrate cookies from browser into controller._cookies

# If we already have a saved session, restore it:
if "user" not in st.session_state:
    sess = controller.get("user_session")
    if sess is not None:
        st.session_state.user = sess

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── AUTH ───────────────────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    db_dsn = st.secrets["db_url"]  # your single‐line DSN
    try:
        conn = psycopg2.connect(db_dsn, cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, username, role, hashed_password
            FROM users
            WHERE username = %s
              AND is_active = TRUE
            """,
            (username,)
        )
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

    if not user or hash_password(password) != user["hashed_password"]:
        return False

    # load assigned projects
    conn = psycopg2.connect(db_dsn, cursor_factory=RealDictCursor)
    cur  = conn.cursor()
    cur.execute("SELECT project_id FROM user_projects WHERE user_id = %s", (user["id"],))
    assigned = [r["project_id"] for r in cur.fetchall()]
    conn.close()

    st.session_state.user = {
        "id":                user["id"],
        "username":          user["username"],
        "role":              user["role"],
        "assigned_projects": assigned,
    }

    # persist into a cookie that *survives* browser restarts:
    controller.set("user_session", st.session_state.user)
    controller.save()
    return True

def logout():
    st.session_state.pop("user", None)
    controller.delete("user_session")
    controller.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
def login_form():
    # if already in session, just show logout
    if st.session_state.get("user"):
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    st.subheader("🔐 Login to GEG PayTrack")
    with st.form("login_form"):
        uname  = st.text_input("Username")
        pwd    = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            if authenticate_user(uname, pwd):
                st.success("✅ Login successful")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid username or password")
