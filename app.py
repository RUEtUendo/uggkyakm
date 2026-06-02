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
        res = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers=HEADERS,
            json={"email": email, "password": password}
        )
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

def child_dashboard():
    st.title(f"Welcome, {st.session_state.name} 👋")
    menu = st.selectbox("What would you like to do?", [
        "🏠 Home", "🎤 Upload Voice Note", "🖼️ Upload Image", "📝 Take Quiz"
    ])
    if menu == "🏠 Home":
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
    elif menu == "🎤 Upload Voice Note":
        st.subheader("🎤 Upload a Voice Note")
        file = st.file_uploader("Choose an audio file", type=["mp3","wav","m4a"])
        if file and st.button("Submit Voice Note"):
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
                st.success("Voice note uploaded!")
            else:
                st.error("Upload failed. Try again.")
    elif menu == "🖼️ Upload Image":
        st.subheader("🖼️ Upload an Image")
        file = st.file_uploader("Choose an image", type=["jpg","jpeg","png"])
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
                    st.success("Image uploaded!")
                else:
                    st.error("Upload failed. Try again.")
    elif menu == "📝 Take Quiz":
        st.subheader("📝 Quiz Time!")
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/content",
            headers=HEADERS,
            params={"type": "eq.quiz"}
        )
        quizzes = res.json()
        if not quizzes:
            st.write("No quizzes available yet.")
        for quiz in quizzes:
            st.markdown(f"**{quiz['title']}**")
            answer = st.text_area(quiz["body"], key=quiz["id"])
            if st.button("Submit Answer", key=f"btn_{quiz['id']}"):
                db_insert("submissions", {
                    "child_id": st.session_state.uid,
                    "content": answer,
                    "file_type": "quiz"
                })
                st.success("Answer submitted!")

def parent_dashboard():
    st.title("Parent Dashboard")
    st.markdown(f"Logged in as: {st.session_state.name}")
    st.info("Parent view coming shortly.")

def admin_dashboard():
    st.title("⚙️ Admin Dashboard")
    st.markdown(f"Welcome, {st.session_state.name}")
    st.markdown("---")

    menu = st.selectbox("Choose a section", [
        "📊 Overview",
        "📖 Bible Verses",
        "📝 Quizzes",
        "📢 Announcements",
        "✅ Mark Submissions"
    ])

    if menu == "📊 Overview":
        admin_overview()
    elif menu == "📖 Bible Verses":
        admin_verses()
    elif menu == "📝 Quizzes":
        admin_quizzes()
    elif menu == "📢 Announcements":
        admin_announcements()
    elif menu == "✅ Mark Submissions":
        admin_mark()

def admin_overview():
    st.subheader("📊 App Overview")

    # Count all children
    children = db_select("Profiles", {"role": "eq.child"})
    st.metric("Total Children", len(children))

    # Count all submissions
    all_subs = db_select("submissions", {})
    images = [s for s in all_subs if s.get("file_type") == "image"]
    voices = [s for s in all_subs if s.get("file_type") == "voice"]
    quizzes = [s for s in all_subs if s.get("file_type") == "quiz"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Images", len(images))
    col2.metric("Voice Notes", len(voices))
    col3.metric("Quiz Answers", len(quizzes))

    st.markdown("---")
    st.subheader("👦 All Children")
    for child in children:
        subs = db_select("submissions", {"child_id": f"eq.{child['id']}"})
        st.markdown(f"**{child['name']}** — {child['email']} — {len(subs)} submissions")

def admin_verses():
    st.subheader("📖 Bible Verses")

    # Show existing verses
    verses = db_select("content", {"type": "eq.bible_verse"})
    if verses:
        for v in verses:
            st.info(f"**{v.get('title','')}** — {v.get('body','')}")
    else:
        st.write("No verses yet.")

    st.markdown("---")
    st.subheader("Add New Verse")
    title = st.text_input("Verse title (e.g. John 3:16)")
    body = st.text_area("Full verse text")
    if st.button("Post Verse"):
        if title and body:
            db_insert("content", {
                "type": "bible_verse",
                "title": title,
                "body": body
            })
            st.success("Verse posted!")
            st.rerun()
        else:
            st.warning("Please fill in both fields.")

def admin_quizzes():
    st.subheader("📝 Quizzes")

    # Show existing quizzes
    quizzes = db_select("content", {"type": "eq.quiz"})
    if quizzes:
        for q in quizzes:
            st.warning(f"**{q.get('title','')}** — {q.get('body','')}")
    else:
        st.write("No quizzes yet.")

    st.markdown("---")
    st.subheader("Add New Quiz Question")
    title = st.text_input("Quiz title (e.g. Week 1 Quiz)")
    body = st.text_area("Question (e.g. Who built the ark? A) Moses B) Noah C) David)")
    if st.button("Post Quiz"):
        if title and body:
            db_insert("content", {
                "type": "quiz",
                "title": title,
                "body": body
            })
            st.success("Quiz posted!")
            st.rerun()
        else:
            st.warning("Please fill in both fields.")

def admin_announcements():
    st.subheader("📢 Announcements")

    # Show existing
    announcements = db_select("content", {"type": "eq.announcement"})
    if announcements:
        for a in announcements:
            st.success(f"**{a.get('title','')}** — {a.get('body','')}")
    else:
        st.write("No announcements yet.")

    st.markdown("---")
    st.subheader("Post New Announcement")
    title = st.text_input("Announcement title")
    body = st.text_area("Announcement message")
    if st.button("Post Announcement"):
        if title and body:
            db_insert("content", {
                "type": "announcement",
                "title": title,
                "body": body
            })
            st.success("Announcement posted!")
            st.rerun()
        else:
            st.warning("Please fill in both fields.")

def admin_mark():
    st.subheader("✅ Mark Quiz Submissions")

    # Get all quiz submissions
    subs = db_select("submissions", {"file_type": "eq.quiz"})

    if not subs:
        st.write("No quiz submissions yet.")
        return

    for sub in subs:
        # Get child name
        profile = db_select("Profiles", {"id": f"eq.{sub['child_id']}"})
        child_name = profile[0]["name"] if profile else "Unknown"

        st.markdown(f"**{child_name}** answered:")
        st.write(sub.get("content", "No answer text"))

        current_mark = sub.get("mark", "")
        if current_mark:
            st.success(f"Current mark: {current_mark}")

        new_mark = st.text_input(
            "Enter mark (e.g. 8/10 or Well done!)",
            key=f"mark_{sub['id']}",
            value=current_mark or ""
        )

        if st.button("Save Mark", key=f"save_{sub['id']}"):
            update_headers = {**HEADERS, "Prefer": "return=representation"}
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/submissions?id=eq.{sub['id']}",
                headers=update_headers,
                json={"mark": new_mark}
            )
            st.success("Mark saved!")
            st.rerun()

        st.markdown("---")

# ── MAIN ROUTER ──
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
