import streamlit as st
from auth.login import login

if "role" not in st.session_state:
    login()
else:
    if st.session_state.role == "child":
        st.write("Child dashboard coming soon")
    elif st.session_state.role == "parent":
        st.write("Parent dashboard coming soon")
    elif st.session_state.role == "admin":
        st.write("Admin dashboard coming soon")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()