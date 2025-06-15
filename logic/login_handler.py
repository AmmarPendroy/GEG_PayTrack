import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager

# ─── COOKIE SETUP ────────────────────────────────────────────────────────────────
cookie_pw = st.secrets["cookie_password"]
cookies   = EncryptedCookieManager(prefix="paytrack/", password=cookie_pw)
if not cookies.ready():
    st.stop()

# Hydrate session_state from cookie (if present)
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    """
    Verify credentials against the DB, then save assigned_projects
    and persist the user dict in an encrypted cookie.
    """
    db_raw = st.secrets["db_url"]

    try:
        # — If secrets["db_url"] is a dict, unpack it; otherwise treat as DSN string:
        if isinstance(db_raw, dict):
            conn = psycopg2.connect(**db_raw, cursor_factory=RealDictCursor)
        else:
            conn = psycopg2.connect(db_raw, cursor_factory=RealDictCursor)

        cur = conn.cursor()

        # 1️⃣ Fetch the user record
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

        # 2️⃣ Verify password
        if user and hash_password(password) == user["hashed_password"]:
            # 3️⃣ Load this user’s assigned project IDs
            cur.execute(
                "SELECT project_id FROM user_projects WHERE user_id = %s",
                (user["id"],)
            )
            assigned = [r["project_id"] for r in cur.fetchall()]

            # 4️⃣ Persist in session_state
            st.session_state.user = {
                "id":                user["id"],
                "username":          user["username"],
                "role":              user["role"],
                "assigned_projects": assigned
            }

            # 5️⃣ Save to the encrypted cookie
            cookies["user_session"] = st.session_state.user
            cookies.save()

            conn.close()
            return True

        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")

    return False

# ─── LOGOUT ────────────────────────────────────────────────────────────────────────
def logout():
    """Clear session + cookie, then rerun to show the login form."""
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
def login_form():
    """
    If already logged in, show Logout.
    Otherwise render the login form.
    """
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
