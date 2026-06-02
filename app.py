import streamlit as st
from auth.login import login
from tiers.child import child_dashboard
from tiers.parent import parent_dashboard
from tiers.admin import admin_dashboard

st.markdown("""
<style>
  .main { max-width: 480px; margin: auto; }
  .stButton > button { width: 100%; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

if "role" not in st.session_state:
    login()
else:
    if st.session_state.role == "child":
        child_dashboard()
    elif st.session_state.role == "parent":
        parent_dashboard()
    elif st.session_state.role == "admin":
        admin_dashboard()

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
