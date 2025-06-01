import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from utils.auth import get_access_flags

st.title("👷 Contractors")

# === DB connection ===
def get_connection():
    return psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)

# === Access control ===
user = st.session_state.get("user", {})
can_view, can_add, can_edit, can_delete = get_access_flags(user, page="contractors")

# === Debug info (helpful for testing) ===
st.sidebar.markdown(f"🧪 Role: `{user.get('role')}`")
st.sidebar.markdown(f"🔐 Access → view: `{can_view}`, add: `{can_add}`, edit: `{can_edit}`, delete: `{can_delete}`")

if not can_view:
    st.error("⛔ You do not have permission to access this page.")
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

            submitted = st.form_submit_button("Add Contractor")

            if submitted:
                if not name:
                    st.warning("Contractor name is required.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO contractors (id, name, contact_person, email, phone, address, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            str(uuid.uuid4()), name, contact_person, email, phone, address, datetime.utcnow()
                        ))
                        conn.commit()
                        conn.close()
                        st.success("✅ Contractor added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

# === View/Edit/Delete Contractors ===
st.markdown("### 📋 Contractor List")

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contractors ORDER BY created_at DESC")
    contractors = cur.fetchall()
    conn.close()

    if not contractors:
        st.info("No contractors found.")
    else:
        for contractor in contractors:
            with st.expander(f"👷 {contractor['name']}"):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    if can_edit:
                        with st.form(f"edit_{contractor['id']}"):
                            name = st.text_input("Name", contractor["name"], key=f"name_{contractor['id']}")
                            contact = st.text_input("Contact Person", contractor["contact_person"] or "", key=f"cp_{contractor['id']}")
                            email = st.text_input("Email", contractor["email"] or "", key=f"email_{contractor['id']}")
                            phone = st.text_input("Phone", contractor["phone"] or "", key=f"phone_{contractor['id']}")
                            address = st.text_area("Address", contractor["address"] or "", key=f"addr_{contractor['id']}")
                            save = st.form_submit_button("💾 Save Changes")

                            if save:
                                try:
                                    conn2 = get_connection()
                                    cur2 = conn2.cursor()
                                    cur2.execute("""
                                        UPDATE contractors
                                        SET name=%s, contact_person=%s, email=%s, phone=%s, address=%s
                                        WHERE id=%s
                                    """, (name, contact, email, phone, address, contractor['id']))
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
