import uuid
import hashlib
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from streamlit_cookies_manager import EncryptedCookieManager

# —––––––– COOKIE SETUP –––––––—
cookies = EncryptedCookieManager(
    prefix="paytrack/",
    password=st.secrets["cookie_password"]
)
# must wait for cookies to hydrate before doing anything
if not cookies.ready():
    st.stop()

def _load_session_from_cookie():
    """If we have a stored user dict in the cookie, restore it."""
    stored = cookies.get("user_session")
    if stored:
        st.session_state.user = stored

_load_session_from_cookie()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username: str, password: str) -> bool:
    """Check credentials, then persist user info to session_state + cookie."""
    db_url = st.secrets["db_url"]
    try:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # 1) pull core user record
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

        if user and hash_password(password) == user["hashed_password"]:
            # 2) load assigned project IDs
            cur.execute(
                "SELECT project_id FROM user_projects WHERE user_id = %s",
                (user["id"],)
            )
            assigned = [r["project_id"] for r in cur.fetchall()]

            # 3) store in session_state
            st.session_state.user = {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "assigned_projects": assigned
            }

            # 4) persist the entire dict in an encrypted cookie
            cookies["user_session"] = st.session_state.user
            cookies.save()

            conn.close()
            return True

        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")

    return False


def logout():
    """Clear both session_state and cookie, then rerun to show login form."""
    if "user" in st.session_state:
        del st.session_state.user
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()


def login_form():
    """Render the login form (or a logout button if already signed in)."""
    if st.session_state.get("user"):
        # already logged in → show a Logout button
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    st.subheader("🔐 Login to GEG PayTrack")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate_user(username, password):
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
