import streamlit as st
import requests
from supabase_config import SUPABASE_URL, HEADERS

def parent_dashboard():
    st.title(f"Parent Dashboard")
    st.markdown(f"Logged in as: {st.session_state.name}")
    st.markdown("---")

    # Get linked children
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/parent_child",
        headers=HEADERS,
        params={"parent_id": f"eq.{st.session_state.uid}"}
    )
    links = res.json()

    if not links:
        st.warning("No children linked to your account. Contact admin.")
        return

    for link in links:
        child_id = link["child_id"]

        # Get child profile
        profile_res = requests.get(
            f"{SUPABASE_URL}/rest/v1/Profiles",
            headers=HEADERS,
            params={"id": f"eq.{child_id}"}
        )
        profiles = profile_res.json()
        if not profiles:
            continue
        child = profiles[0]

        st.subheader(f"👦 {child['name']}")

        # Get submissions
        sub_res = requests.get(
            f"{SUPABASE_URL}/rest/v1/submissions",
            headers=HEADERS,
            params={"child_id": f"eq.{child_id}"}
        )
        submissions = sub_res.json()

        if not submissions:
            st.write("No submissions yet.")
        else:
            images = [s for s in submissions if s["file_type"] == "image"]
            voices = [s for s in submissions if s["file_type"] == "voice"]
            quizzes = [s for s in submissions if s["file_type"] == "quiz"]

            st.markdown(f"📷 **Images uploaded:** {len(images)}")
            for img in images:
                st.image(img["file_url"], width=200)

            st.markdown(f"🎤 **Voice notes uploaded:** {len(voices)}")
            for v in voices:
                st.markdown(f"[Listen to voice note]({v['file_url']})")

            st.markdown(f"📝 **Quiz answers submitted:** {len(quizzes)}")
            for q in quizzes:
                st.write(f"Answer: {q['content']}")
                if q.get('mark'):
                    st.success(f"Mark: {q['mark']}")
                else:
                    st.warning("Not marked yet")

        st.markdown("---")
