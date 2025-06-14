import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager

# ─── COOKIE SETUP ────────────────────────────────────────────────────────────────
# This must run at import time so our app can hydrate before anything else.
cookie_pw = st.secrets["cookie_password"]
cookies   = EncryptedCookieManager(prefix="paytrack/", password=cookie_pw)
if not cookies.ready():
    # Wait until cookies are loaded
    st.stop()

# If there’s already a saved session in the cookie, restore it:
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Return SHA256 digest of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    """
    Verify credentials against the DB, then load assigned_projects
    and persist the entire user dict to an encrypted cookie.
    """
    db_url = st.secrets["db_url"]  # this is your single-line DSN string

    try:
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

        # 2️⃣ Check password
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
    """Clear both session + cookie, then rerun to show the login form."""
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
def login_form():
    """
    If already in session_state, show a logout button.
    Otherwise render the login form.
    """
    # — If logged in already, show a Logout button:
    if st.session_state.get("user"):
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    # — Not logged in → render the form
    st.subheader("🔐 Login to GEG PayTrack")
    with st.form("login_form"):
        uname = st.text_input("Username")
        pwd   = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if authenticate_user(uname, pwd):
                st.success("✅ Login successful")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid username or password")
