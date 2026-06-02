import streamlit as st
import requests
from supabase_config import SUPABASE_URL, SUPABASE_KEY, HEADERS, db_insert, db_select

st.markdown("""
<style>
  .main { max-width: 480px; margin: auto; }
  .stButton > button { width: 100%; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

def login():
    st.title("UGGK Bible App")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Auth endpoint requires apikey header specifically
        auth_headers = {
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            res = requests.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers=auth_headers,
                json={"email": email, "password": password}
            )
            
            # Raise an error for bad status codes
            res.raise_for_status()
            data = res.json()
            
            if "access_token" in data:
                uid = data["user"]["id"]
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
                
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {e}")

# Application Main Logic
if "uid" not in st.session_state:
    login()
else:
    st.write(f"Welcome, {st.session_state.name}!")
    if st.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
