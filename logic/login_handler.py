import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from datetime import timedelta, datetime
from streamlit_cookies_manager import EncryptedCookieManager

# ─── COOKIE SETUP ────────────────────────────────────────────────────────────────
cookie_pw = st.secrets["cookie_password"]
cookies   = EncryptedCookieManager(prefix="paytrack/", password=cookie_pw)
if not cookies.ready():
    st.stop()

# Hydrate session_state from cookie if it exists
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    """
    Verify credentials against the DB URI string, then save assigned_projects
    and persist the user dict in an encrypted, persistent cookie.
    """
    db_url = st.secrets["db_url"]  # single-line DSN string

    try:
        # Connect via DSN
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur  = conn.cursor()

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

            # 5️⃣ Save to the encrypted cookie _with_ a 30-day max_age
            max_age_seconds = 30 * 24 * 3600
            cookies.set(
                "user_session",
                st.session_state.user,
                max_age=max_age_seconds
            )
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
    cookies.delete("user_session")
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
