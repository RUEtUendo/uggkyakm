import streamlit as st
import requests
from supabase_config import SUPABASE_URL, SUPABASE_KEY, HEADERS, db_insert

def child_dashboard():
    st.title(f"Welcome, {st.session_state.name} 👋")
    st.markdown("---")

    menu = st.selectbox("What would you like to do?", [
        "🏠 Home",
        "🎤 Upload Voice Note",
        "🖼️ Upload Image",
        "📝 Take Quiz"
    ])

    if menu == "🏠 Home":
        show_home()
    elif menu == "🎤 Upload Voice Note":
        upload_voice()
    elif menu == "🖼️ Upload Image":
        upload_image()
    elif menu == "📝 Take Quiz":
        show_quiz()

def show_home():
    st.subheader("📖 Verse of the Day")
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/content",
        headers=HEADERS,
        params={"type": "eq.bible_verse", "limit": "1"}
    )
    verses = res.json()
    if verses:
        st.info(verses[0]["body"])
    else:
        st.write("No verse posted yet.")

    st.subheader("📢 Announcements")
    res2 = requests.get(
        f"{SUPABASE_URL}/rest/v1/content",
        headers=HEADERS,
        params={"type": "eq.announcement"}
    )
    announcements = res2.json()
    for a in announcements:
        st.success(a["body"])

def upload_voice():
    st.subheader("🎤 Upload a Voice Note")
    file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a"])
    if file:
        if st.button("Submit Voice Note"):
            filename = f"{st.session_state.uid}_voice_{file.name}"
            upload_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": file.type,
                "x-upsert": "true"
            }
            res = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/uploads/{filename}",
                headers=upload_headers,
                data=file.getvalue()
            )
            if res.status_code in [200, 201]:
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/uploads/{filename}"
                db_insert("submissions", {
                    "child_id": st.session_state.uid,
                    "file_url": file_url,
                    "file_type": "voice"
                })
                st.success("Voice note uploaded successfully!")
            else:
                st.error("Upload failed. Try again.")

def upload_image():
    st.subheader("🖼️ Upload an Image")
    file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    if file:
        st.image(file, caption="Preview", use_column_width=True)
        if st.button("Submit Image"):
            filename = f"{st.session_state.uid}_image_{file.name}"
            upload_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": file.type,
                "x-upsert": "true"
            }
            res = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/uploads/{filename}",
                headers=upload_headers,
                data=file.getvalue()
            )
            if res.status_code in [200, 201]:
                file_url = f"{SUPABASE_URL}/storage/v1/object/public/uploads/{filename}"
                db_insert("submissions", {
                    "child_id": st.session_state.uid,
                    "file_url": file_url,
                    "file_type": "image"
                })
                st.success("Image uploaded successfully!")
            else:
                st.error("Upload failed. Try again.")

def show_quiz():
    st.subheader("📝 Quiz Time!")
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/content",
        headers=HEADERS,
        params={"type": "eq.quiz"}
    )
    quizzes = res.json()
    if not quizzes:
        st.write("No quizzes available yet.")
        return
    for quiz in quizzes:
        st.markdown(f"**{quiz['title']}**")
        answer = st.text_area(f"Your answer for: {quiz['body']}", key=quiz['id'])
        if st.button(f"Submit Answer", key=f"btn_{quiz['id']}"):
            db_insert("submissions", {
                "child_id": st.session_state.uid,
                "content": answer,
                "file_type": "quiz"
            })
            st.success("Answer submitted!")
