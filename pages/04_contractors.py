import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime

st.title("👷 Contractors")

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Inline role-based access logic ===
def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    role = user.get("role", "")
    can_view = can_add = can_edit = can_delete = False

    if page == "contractors":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role in ["Site Accountant", "HQ Accountant"]:
            can_view = True

    return can_view, can_add, can_edit, can_delete

# === Get user & access rights ===
user = st.session_state.get("user", {})
if not isinstance(user, dict):
    user = {}

can_view, can_add, can_edit, can_delete = get_access_flags(user, page="contractors")

# === Permission check ===
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

# === Add Contractor Form ===
if can_add:
    with st.expander("➕ Add New Contractor", expanded=True):
        with st.form("add_contractor_form"):
            name = st.text_input("Contractor Name", max_chars=100)
            contact_person = st.text_input("Contact Person")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            address = st.text_area("Address")

            if st.form_submit_button("Add Contractor"):
                if not name:
                    st.warning("Contractor name is required.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO contractors (id, name, contact_person, email, phone, address, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (str(uuid.uuid4()), name, contact_person, email, phone, address, datetime.utcnow())
                        )
                        conn.commit()
                        conn.close()
                        st.success("✅ Contractor added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")


# === Load contractors from DB ===
st.markdown("### 📋 Contractor List")

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contractors ORDER BY created_at DESC")
    contractors = cur.fetchall()
    conn.close()

    search_term = st.text_input("🔍 Search contractors by name, contact, or email").strip().lower()

    filtered = [
        c for c in contractors
        if search_term in (c["name"] or "").lower()
        or search_term in (c["contact_person"] or "").lower()
        or search_term in (c["email"] or "").lower()
    ]

    if not filtered:
        st.info("No matching contractors found.")
    else:
        # Enumerate so we can show a simple serial number
        for idx, contractor in enumerate(filtered, start=1):
            title = f"{idx}. {contractor['name']}"
            with st.expander(title):
                col1, col2 = st.columns([4, 1])

                with col1:
                    if can_edit:
                        with st.form(f"edit_{contractor['id']}"):
                            name = st.text_input("Name", contractor["name"], key=f"name_{contractor['id']}")
                            contact = st.text_input("Contact Person", contractor["contact_person"] or "", key=f"cp_{contractor['id']}")
                            email = st.text_input("Email", contractor["email"] or "", key=f"email_{contractor['id']}")
                            phone = st.text_input("Phone", contractor["phone"] or "", key=f"phone_{contractor['id']}")
                            address = st.text_area("Address", contractor["address"] or "", key=f"addr_{contractor['id']}")
                            if st.form_submit_button("💾 Save Changes"):
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    cur2.execute(
                                        """
                                        UPDATE contractors
                                        SET name=%s, contact_person=%s, email=%s, phone=%s, address=%s
                                        WHERE id=%s
                                        """,
                                        (name, contact, email, phone, address, contractor['id'])
                                    )
                                    conn2.commit()
                                    conn2.close()
                                    st.success("✅ Updated successfully")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Update failed: {e}")
                    else:
                        st.markdown(f"**Contact Person**: {contractor['contact_person'] or '—'}")
                        st.markdown(f"**Email**: {contractor['email'] or '—'}")
                        st.markdown(f"**Phone**: {contractor['phone'] or '—'}")
                        st.markdown(f"**Address**:\n{contractor['address'] or '—'}")

                with col2:
                    if can_delete and st.button("🗑️ Delete", key=f"del_{contractor['id']}"):
                        try:
                            conn2 = get_connection()
                            cur2 = conn2.cursor()
                            cur2.execute("DELETE FROM contractors WHERE id = %s", (contractor['id'],))
                            conn2.commit()
                            conn2.close()
                            st.success("✅ Deleted successfully")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}")

except Exception as e:
    st.error(f"Failed to load contractor data: {e}")
