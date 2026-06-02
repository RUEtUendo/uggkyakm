import streamlit as st
import requests
from supabase_config import SUPABASE_URL, SUPABASE_KEY, HEADERS, db_select

def login():
    st.title("UGGK Bible App")
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Sign in via Supabase Auth REST API
        res = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=HEADERS,
            json={"email": email, "password": password}
        )
        data = res.json()

        if "access_token" in data:
            uid = data["user"]["id"]

            # Get role from profiles table
            profile = db_select("Profiles", {"id": f"eq.{uid}"})

            if profile and len(profile) > 0:
                st.session_state.uid = uid
                st.session_state.role = profile[0]["role"]
                st.session_state.name = profile[0]["name"]
                st.session_state.token = data["access_token"]
                st.rerun()
            else:
                st.error("Profile not found. Contact admin.")
        else:
            st.error("Login failed. Check your email and password.")