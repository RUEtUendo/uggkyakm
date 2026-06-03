import streamlit as st
import requests
from audio_recorder_streamlit import audio_recorder

# ── CONFIG ─────────────────────────────────────────────
SUPABASE_URL = "https://cnqwbgjfsbseispmzywc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNucXdiZ2pmc2JzZWlzcG16eXdjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMjQwNjQsImV4cCI6MjA5NTkwMDA2NH0.2_Gj-6z_Gewwb0ypCvVV4YislaYdOj3Mm8Y0d_317L8"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def db_select(table, filters=None):
    params = filters or {}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=params)
    if res.status_code != 200:
        print(f"SELECT ERROR {table}: {res.status_code} {res.text}")
        return []
    return res.json()

def db_insert(table, data):
    res = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    if res.status_code not in [200, 201]:
        print(f"INSERT ERROR {table}: {res.status_code} {res.text}")
        return None
    return res.json()

def db_update(table, match_field, match_value, data):
    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}?{match_field}=eq.{match_value}",
        headers=HEADERS, json=data
    )
    if res.status_code not in [200, 204]:
        print(f"UPDATE ERROR {table}: {res.status_code} {res.text}")
        return None
    return res.json()

st.markdown("""
<style>
  .main { max-width: 480px; margin: auto; }
  .stButton > button { width: 100%; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# ── LOGIN ──────────────────────────────────────────────
def login():
    st.title("UGGK Bible App")
    email    = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            res  = requests.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
                json={"email": email, "password": password}
            )
            data = res.json()
            if "access_token" in data:
                uid     = data["user"]["id"]
                profile = db_select("Profiles", {"id": f"eq.{uid}"})
                if profile:
                    st.session_state.uid   = uid
                    st.session_state.role  = profile[0]["role"]
                    st.session_state.name  = profile[0]["name"]
                    st.session_state.token = data["access_token"]
                    st.rerun()
                else:
                    st.error("Profile not found. Contact admin.")
            else:
                st.error("Login failed. Check your email and password.")
        except Exception as e:
            st.error(f"Connection error: {e}")

# ── CHILD ──────────────────────────────────────────────
def child_dashboard():
    st.title(f"Welcome, {st.session_state.name} 👋")
    menu = st.selectbox("What would you like to do?", [
        "🏠 Home",
        "🎤 Record Voice Note",
        "🖼️ Upload Image",
        "📝 Take Quiz"
    ])

    if menu == "🏠 Home":
        st.subheader("📖 Verse of the Day")
        verses = db_select("content", {"type": "eq.bible_verse", "limit": "1"})
        if verses:
            st.info(f"**{verses[0].get('title','')}**\n\n{verses[0].get('body','')}")
        else:
            st.write("No verse posted yet.")
        st.subheader("📢 Announcements")
        announcements = db_select("content", {"type": "eq.announcement"})
        if announcements:
            for a in announcements:
                st.success(f"**{a.get('title','')}** — {a.get('body','')}")
        else:
            st.write("No announcements yet.")

    elif menu == "🎤 Record Voice Note":
        st.subheader("🎤 Record Your Voice")
        st.write("Press the microphone to start. Press again to stop.")
        audio_bytes = audio_recorder(
            text="",
            recording_color="#e74c3c",
            neutral_color="#2ecc71",
            icon_size="3x"
        )
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            if st.button("Submit Recording"):
                filename = f"{st.session_state.uid}_voice_recording.wav"
                res = requests.post(
                    f"{SUPABASE_URL}/storage/v1/object/Uploads/{filename}",
                    headers={"apikey": SUPABASE_KEY,
                             "Authorization": f"Bearer {SUPABASE_KEY}",
                             "Content-Type": "audio/wav",
                             "x-upsert": "true"},
                    data=audio_bytes
                )
                if res.status_code in [200, 201]:
                    file_url = f"{SUPABASE_URL}/storage/v1/object/public/Uploads/{filename}"
                    db_insert("submissions", {
                        "child_id": st.session_state.uid,
                        "file_url": file_url,
                        "file_type": "voice"
                    })
                    st.success("Recording submitted!")
                else:
                    st.error(f"Upload failed: {res.text}")

    elif menu == "🖼️ Upload Image":
        st.subheader("🖼️ Upload an Image")
        file = st.file_uploader("Choose an image", type=["jpg","jpeg","png"])
        if file:
            st.image(file, caption="Preview", use_column_width=True)
            if st.button("Submit Image"):
                filename = f"{st.session_state.uid}_image_{file.name}"
                res = requests.post(
                    f"{SUPABASE_URL}/storage/v1/object/Uploads/{filename}",
                    headers={"apikey": SUPABASE_KEY,
                             "Authorization": f"Bearer {SUPABASE_KEY}",
                             "Content-Type": file.type,
                             "x-upsert": "true"},
                    data=file.getvalue()
                )
                if res.status_code in [200, 201]:
                    file_url = f"{SUPABASE_URL}/storage/v1/object/public/Uploads/{filename}"
                    db_insert("submissions", {
                        "child_id": st.session_state.uid,
                        "file_url": file_url,
                        "file_type": "image"
                    })
                    st.success("Image uploaded!")
                else:
                    st.error(f"Upload failed: {res.text}")

    elif menu == "📝 Take Quiz":
        st.subheader("📝 Quiz Time!")
        quizzes = db_select("content", {"type": "eq.quiz"})
        if not quizzes:
            st.info("No quizzes available yet. Check back soon!")
        for quiz in quizzes:
            st.markdown(f"### {quiz.get('title','')}")
            st.write(quiz.get("body",""))
            options_raw = quiz.get("options","")
            if options_raw:
                options = [o.strip() for o in options_raw.split("|")]
                answer = st.radio(
                    "Choose your answer:",
                    options,
                    key=f"radio_{quiz['id']}"
                )
            else:
                answer = st.text_area(
                    "Type your answer:",
                    key=f"text_{quiz['id']}"
                )
            if st.button("Submit Answer", key=f"btn_{quiz['id']}"):
                result = db_insert("submissions", {
                    "child_id": st.session_state.uid,
                    "content":  answer,
                    "file_type": "quiz"
                })
                if result is not None:
                    st.success("Answer submitted! Well done 🎉")
                else:
                    st.error("Failed to submit. Try again.")
            st.markdown("---")

# ── PARENT ─────────────────────────────────────────────
def parent_dashboard():
    st.title("👨‍👩‍👧 Parent Dashboard")
    st.markdown(f"Welcome, {st.session_state.name}")
    st.markdown("---")
    links = db_select("parent_child", {"parent_id": f"eq.{st.session_state.uid}"})
    if not links:
        st.warning("No children linked to your account. Contact admin.")
        return
    for link in links:
        child_id = link["child_id"]
        profiles = db_select("Profiles", {"id": f"eq.{child_id}"})
        if not profiles:
            continue
        child = profiles[0]
        st.subheader(f"👦 {child['name']}")
        subs = db_select("submissions", {"child_id": f"eq.{child_id}"})
        if not subs:
            st.write("No activity yet.")
        else:
            images  = [s for s in subs if s.get("file_type") == "image"]
            voices  = [s for s in subs if s.get("file_type") == "voice"]
            quizzes = [s for s in subs if s.get("file_type") == "quiz"]
            if images:
                st.markdown(f"🖼️ **Images: {len(images)}**")
                for img in images:
                    if img.get("file_url"):
                        st.image(img["file_url"], width=200)
            if voices:
                st.markdown(f"🎤 **Voice Notes: {len(voices)}**")
                for v in voices:
                    if v.get("file_url"):
                        st.markdown(f"[▶ Listen]({v['file_url']})")
            if quizzes:
                st.markdown(f"📝 **Quiz Answers: {len(quizzes)}**")
                for q in quizzes:
                    with st.expander("View answer"):
                        st.write(q.get("content","No answer"))
                        if q.get("mark"):
                            st.success(f"✅ Mark: {q['mark']}")
                        else:
                            st.warning("⏳ Not marked yet")
        st.markdown("---")

# ── ADMIN ──────────────────────────────────────────────
def admin_dashboard():
    st.title("⚙️ Admin Dashboard")
    st.markdown(f"Welcome, {st.session_state.name}")
    st.markdown("---")
    menu = st.selectbox("Choose a section", [
        "📊 Overview", "📖 Bible Verses", "📝 Quizzes",
        "📢 Announcements", "✅ Mark Submissions"
    ])
    if menu == "📊 Overview":           admin_overview()
    elif menu == "📖 Bible Verses":     admin_verses()
    elif menu == "📝 Quizzes":          admin_quizzes()
    elif menu == "📢 Announcements":    admin_announcements()
    elif menu == "✅ Mark Submissions": admin_mark()

def admin_overview():
    st.subheader("📊 Overview")
    children = db_select("Profiles", {"role": "eq.child"})
    all_subs = db_select("submissions", {})
    st.metric("Total Children", len(children))
    col1, col2, col3 = st.columns(3)
    col1.metric("Images",       len([s for s in all_subs if s.get("file_type")=="image"]))
    col2.metric("Voice Notes",  len([s for s in all_subs if s.get("file_type")=="voice"]))
    col3.metric("Quiz Answers", len([s for s in all_subs if s.get("file_type")=="quiz"]))
    st.markdown("---")
    for child in children:
        subs = db_select("submissions", {"child_id": f"eq.{child['id']}"})
        st.markdown(f"**{child['name']}** — {child.get('email','')} — {len(subs)} submissions")

def admin_verses():
    st.subheader("📖 Bible Verses")
    verses = db_select("content", {"type": "eq.bible_verse"})
    if verses:
        for v in verses:
            st.info(f"**{v.get('title','')}** — {v.get('body','')}")
    else:
        st.write("No verses yet.")
    st.markdown("---")
    title = st.text_input("Verse reference (e.g. John 3:16)", key="verse_title")
    body  = st.text_area("Full verse text", key="verse_body")
    if st.button("Post Verse"):
        if title and body:
            result = db_insert("content", {"type":"bible_verse","title":title,"body":body})
            if result is not None:
                st.success("Verse posted!")
                st.rerun()
            else:
                st.error("Failed to post. Check terminal.")
        else:
            st.warning("Fill in both fields.")

def admin_quizzes():
    st.subheader("📝 Quizzes")
    quizzes = db_select("content", {"type": "eq.quiz"})
    if quizzes:
        for q in quizzes:
            st.warning(f"**{q.get('title','')}** — {q.get('body','')}")
            if q.get("options"):
                st.write(f"Options: {q.get('options','')}")
    else:
        st.write("No quizzes yet.")
    st.markdown("---")
    st.subheader("Add New Quiz Question")
    title   = st.text_input("Quiz title", key="quiz_title")
    body    = st.text_area("Question text", key="quiz_body")
    options = st.text_input(
        "Answer options — separate with | symbol",
        placeholder="A) Moses|B) Noah|C) David",
        key="quiz_options"
    )
    st.caption("Leave options blank for a written answer question.")
    if st.button("Post Quiz"):
        if title and body:
            result = db_insert("content", {
                "type":    "quiz",
                "title":   title,
                "body":    body,
                "options": options or None
            })
            if result is not None:
                st.success("Quiz posted!")
                st.rerun()
            else:
                st.error("Failed to post. Check terminal.")
        else:
            st.warning("Fill in both fields.")

def admin_announcements():
    st.subheader("📢 Announcements")
    announcements = db_select("content", {"type": "eq.announcement"})
    if announcements:
        for a in announcements:
            st.success(f"**{a.get('title','')}** — {a.get('body','')}")
    else:
        st.write("No announcements yet.")
    st.markdown("---")
    title = st.text_input("Title", key="ann_title")
    body  = st.text_area("Message", key="ann_body")
    if st.button("Post Announcement"):
        if title and body:
            result = db_insert("content", {"type":"announcement","title":title,"body":body})
            if result is not None:
                st.success("Announcement posted!")
                st.rerun()
            else:
                st.error("Failed to post. Check terminal.")
        else:
            st.warning("Fill in both fields.")

def admin_mark():
    st.subheader("✅ Mark Quiz Submissions")
    subs = db_select("submissions", {"file_type": "eq.quiz"})
    if not subs:
        st.write("No quiz submissions yet.")
        return
    for sub in subs:
        profile    = db_select("Profiles", {"id": f"eq.{sub['child_id']}"})
        child_name = profile[0]["name"] if profile else "Unknown"
        st.markdown(f"**{child_name}** answered:")
        st.write(sub.get("content","No answer text"))
        current_mark = sub.get("mark","")
        if current_mark:
            st.success(f"Current mark: {current_mark}")
        new_mark = st.text_input(
            "Enter mark (e.g. 8/10)",
            key=f"mark_{sub['id']}",
            value=current_mark or ""
        )
        if st.button("Save Mark", key=f"save_{sub['id']}"):
            result = db_update("submissions", "id", sub["id"], {"mark": new_mark})
            if result is not None:
                st.success("Mark saved!")
                st.rerun()
            else:
                st.error("Failed to save mark.")
        st.markdown("---")

# ── ROUTER ─────────────────────────────────────────────
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
