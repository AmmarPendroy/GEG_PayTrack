import streamlit as st
from utils.auth import check_role
from utils.data_handler import add_contractor, get_all_contractors
import pandas as pd

# ---------------------------------------
# Access Control
# ---------------------------------------
def page_visible():
    return check_role(["Superadmin", "HQ Admin", "Site PM"])

# ---------------------------------------
# Contractor Form
# ---------------------------------------
def contractor_form():
    st.subheader("➕ Add New Contractor")
    with st.form("add_contractor_form", clear_on_submit=True):
        name = st.text_input("Contractor Name", max_chars=255)
        person = st.text_input("Contact Person")
        email = st.text_input("Contact Email")
        phone = st.text_input("Contact Phone")
        address = st.text_area("Address")

        submitted = st.form_submit_button("Submit")
        if submitted:
            if name.strip() == "":
                st.warning("Contractor name is required.")
            else:
                success = add_contractor(name, person, email, phone, address)
                if success:
                    st.success("Contractor added successfully.")
                    st.experimental_rerun()

# ---------------------------------------
# Contractor List
# ---------------------------------------
def contractor_table():
    st.subheader("📋 Contractor List")
    data = get_all_contractors()
    if data:
        df = pd.DataFrame(data, columns=["Name", "Contact Person", "Email", "Phone", "Address", "Created"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No contractors found.")

# ---------------------------------------
# Page Renderer
# ---------------------------------------
def run():
    if not page_visible():
        st.error("🚫 You do not have access to this page.")
        return

    st.title("🧱 Contractor Management")
    contractor_form()
    st.markdown("---")
    contractor_table()

# Run when loaded by Streamlit
run()
