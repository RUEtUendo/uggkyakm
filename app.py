import re
import random
import string
import streamlit as st
import requests
from datetime import datetime, date, time, timedelta
from audio_recorder_streamlit import audio_recorder

# ── CONFIG ─────────────────────────────────────────────
SUPABASE_URL = "https://cnqwbgjfsbseispmzywc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNucXdiZ2pmc2JzZWlzcG16eXdjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMjQwNjQsImV4cCI6MjA5NTkwMDA2NH0.2_Gj-6z_Gewwb0ypCvVV4YislaYdOj3Mm8Y0d_317L8"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNucXdiZ2pmc2JzZWlzcG16eXdjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDMyNDA2NCwiZXhwIjoyMDk1OTAwMDY0fQ.modpFZjoMOMjHyOgnecYg7gzzZeoCphfYb7FA8jGbgk"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ── DB HELPERS ─────────────────────────────────────────
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

def db_delete(table, match_field, match_value):
    res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/{table}?{match_field}=eq.{match_value}",
        headers=HEADERS
    )
    return res.status_code in [200, 204]

def upload_file(file_bytes, filename, content_type):
    res = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/Uploads/{filename}",
        headers={"apikey": SUPABASE_KEY,
                 "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": content_type,
                 "x-upsert": "true"},
        data=file_bytes
    )
    if res.status_code in [200, 201]:
        return f"{SUPABASE_URL}/storage/v1/object/public/Uploads/{filename}"
    print(f"UPLOAD ERROR: {res.status_code} {res.text}")
    return None

# ── SESSION PERSISTENCE — survives page refresh ─────────
def restore_session():
    if "uid" not in st.session_state:
        params = st.query_params
        if "uid" in params:
            uid = params["uid"]
            profile = db_select("Profiles", {"id": f"eq.{uid}"})
            if profile:
                st.session_state.uid  = uid
                st.session_state.role = profile[0]["role"]
                st.session_state.name = profile[0]["name"]

restore_session()

# ── ACCOUNT CREATION HELPERS ─────────────────────────────
def create_auth_user(email, password):
    if "PASTE_YOUR" in SUPABASE_SERVICE_KEY or not SUPABASE_SERVICE_KEY:
        return {"error": "Service role key is missing in app.py — go to Supabase → Project Settings → API → reveal service_role key and paste it in."}
    try:
        res = requests.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"email": email, "password": password, "email_confirm": True},
            timeout=20
        )
    except Exception as e:
        return {"error": f"Connection failed: {e}"}
    if res.status_code in [200, 201]:
        return res.json()
    print(f"CREATE USER ERROR: {res.status_code} {res.text}")
    return {"error": res.text, "status": res.status_code}

def generate_child_email(name):
    slug   = re.sub(r'[^a-z0-9]', '', name.lower()) or "child"
    suffix = ''.join(random.choices(string.digits, k=6))
    return f"{slug}{suffix}@gmail.com"

# ── BRANDING / LOGO ──────────────────────────────────────
def get_app_logo_url():
    rows = db_select("content", {"type": "eq.app_logo", "limit": "1"})
    if rows and rows[0].get("media_url"):
        return rows[0]["media_url"]
    return None

# ── WEEK HELPERS (Sunday → Saturday) ─────────────────────
def get_week_start():
    """Returns most recent Sunday at 00:00 UTC."""
    now = datetime.utcnow()
    days_since_sunday = (now.weekday() + 1) % 7  # Mon=0..Sun=6 -> Sun=0
    week_start = (now - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return week_start

def get_week_label():
    start = get_week_start()
    end = start + timedelta(days=6)
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"

def get_current_week_items(content_type):
    week_start_iso = get_week_start().isoformat()
    items = db_select("content", {
        "type": f"eq.{content_type}",
        "publish_at": f"gte.{week_start_iso}",
        "order": "publish_at.desc"
    })
    now_iso = datetime.utcnow().isoformat()
    return [c for c in items if c.get("publish_at","") <= now_iso and not c.get("is_pinned")]

def get_pinned_items(content_type):
    items = db_select("content", {"type": f"eq.{content_type}", "is_pinned": "eq.true"})
    now_iso = datetime.utcnow().isoformat()
    return [c for c in items if c.get("publish_at","") <= now_iso]

# ── PASTOR NOTE REACTIONS ─────────────────────────────────
def get_reaction_counts(content_id):
    reactions = db_select("note_reactions", {"content_id": f"eq.{content_id}"})
    likes    = len([r for r in reactions if r["reaction"] == "like"])
    dislikes = len([r for r in reactions if r["reaction"] == "dislike"])
    acks     = len([r for r in reactions if r["reaction"] == "ack"])
    return likes, dislikes, acks, reactions

def get_my_reactions(content_id, parent_id):
    return db_select("note_reactions", {
        "content_id": f"eq.{content_id}",
        "parent_id": f"eq.{parent_id}"
    })

def toggle_reaction(content_id, parent_id, reaction_type):
    existing_same = db_select("note_reactions", {
        "content_id": f"eq.{content_id}",
        "parent_id": f"eq.{parent_id}",
        "reaction": f"eq.{reaction_type}"
    })
    if existing_same:
        db_delete("note_reactions", "id", existing_same[0]["id"])
        return
    if reaction_type in ("like", "dislike"):
        opposite = "dislike" if reaction_type == "like" else "like"
        existing_opp = db_select("note_reactions", {
            "content_id": f"eq.{content_id}",
            "parent_id": f"eq.{parent_id}",
            "reaction": f"eq.{opposite}"
        })
        if existing_opp:
            db_delete("note_reactions", "id", existing_opp[0]["id"])
    db_insert("note_reactions", {
        "content_id": content_id,
        "parent_id": parent_id,
        "reaction": reaction_type
    })

# ── THEME (explicit Light / Dark selection) ───────────────
def apply_theme():
    choice = st.session_state.get("theme_choice", "Light")

    if choice == "Dark":
        bg_color    = "#0B1E33"
        bg_grad     = "linear-gradient(180deg, #0B1E33 0%, #0F2740 50%, #0B1E33 100%)"
        text_color  = "#FFFFFF"
        muted_color = "#A8C8E8"
        card_bg     = "#16283F"
        input_bg    = "#1E3450"
        accent      = "#5DADE2"
        accent_text = "#FFFFFF"
        border_col  = "#2C4258"
    else:
        bg_color    = "#2E7BB4"
        bg_grad     = "linear-gradient(180deg, #2E7BB4 0%, #3A8FCC 50%, #2E7BB4 100%)"
        text_color  = "#0A1628"
        muted_color = "#0A1628"
        card_bg     = "#EBF5FB"
        input_bg    = "#FFFFFF"
        accent      = "#1A5276"
        accent_text = "#FFFFFF"
        border_col  = "#1F6FAA"

    st.markdown(f"""
    <style>
      html, body {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        transition: background-color 0.4s ease, color 0.4s ease;
      }}
      .stApp, .stApp > div,
      [data-testid="stAppViewContainer"],
      [data-testid="stAppViewContainer"] > section,
      [data-testid="block-container"],
      .main, .main > div {{
        background: {bg_grad} !important;
        background-attachment: fixed !important;
        color: {text_color} !important;
        transition: background-color 0.4s ease, color 0.4s ease;
      }}
      .main .block-container {{
        max-width: 480px;
        margin: auto;
        padding: 1rem;
      }}
      h1, h2, h3, h4, h5, h6 {{ color: {text_color} !important; }}
      h1 {{ font-size: 1.8rem; color: {accent} !important; }}
      p, span, div, label,
      .stMarkdown, .stMarkdown p, .stMarkdown span,
      .stCaption, .stText,
      [data-testid="stMarkdownContainer"],
      [data-testid="stMarkdownContainer"] p,
      [data-testid="stMarkdownContainer"] span,
      [data-testid="stMarkdownContainer"] li,
      .stSelectbox label, .stTextInput label, .stTextArea label,
      .stNumberInput label, .stFileUploader label, .stCheckbox label,
      .stRadio label, .stDateInput label, .stTimeInput label {{
        color: {text_color} !important;
      }}
      [data-testid="stSidebar"] {{ background-color: {card_bg} !important; }}
      .stButton > button {{
        width: 100%; border-radius: 25px; padding: 0.6rem;
        font-weight: bold; font-size: 1rem;
        background-color: {accent} !important;
        color: {accent_text} !important;
        border: none !important; margin-top: 4px;
        transition: opacity 0.3s ease;
      }}
      .stButton > button:hover {{ opacity: 0.85 !important; }}
      .stButton > button * {{ color: {accent_text} !important; }}
      .stTextInput input, .stTextArea textarea,
      .stNumberInput input, .stSelectbox > div > div {{
        border-radius: 15px !important; padding: 0.5rem 1rem !important;
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_col} !important;
      }}
      .stSelectbox [data-baseweb="select"] span,
      .stSelectbox [data-baseweb="select"] div {{
        color: {text_color} !important;
        background-color: {input_bg} !important;
      }}
      div[data-testid="metric-container"] {{
        background-color: {card_bg} !important; border-radius: 15px !important;
        padding: 10px !important; border: 1px solid {border_col} !important;
      }}
      div[data-testid="metric-container"] * {{ color: {text_color} !important; }}
      div[data-testid="stExpander"] {{
        border-radius: 15px !important; border: 1px solid {border_col} !important;
        background-color: {card_bg} !important;
      }}
      div[data-testid="stExpander"] summary,
      div[data-testid="stExpander"] summary span,
      div[data-testid="stExpander"] p,
      div[data-testid="stExpander"] div {{ color: {text_color} !important; }}
      [data-testid="stAlert"] > div, [data-testid="stAlert"] p,
      [data-testid="stAlert"] span {{ color: {text_color} !important; }}
      .stTabs [data-baseweb="tab"] {{ color: {muted_color} !important; }}
      .stTabs [aria-selected="true"] {{
        color: {accent} !important; border-bottom-color: {accent} !important;
      }}
      .stCheckbox span, .stRadio span {{ color: {text_color} !important; }}
      [data-testid="stFileUploader"] {{
        background-color: {card_bg} !important; border-radius: 15px !important;
        border: 1px solid {border_col} !important;
      }}
      [data-testid="stFileUploader"] span,
      [data-testid="stFileUploader"] p,
      [data-testid="stFileUploader"] div {{ color: {text_color} !important; }}
      hr {{ border-color: {border_col} !important; }}
      #MainMenu {{visibility: hidden;}}
      footer {{visibility: hidden;}}
      header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

apply_theme()

# ── HEADER (with explicit theme dropdown) ─────────────────
def show_header(title="UGGK Bible App"):
    logo_url = get_app_logo_url()
    col1, col2, col3 = st.columns([1, 3, 1.3])
    with col1:
        if logo_url:
            st.image(logo_url, width=50)
        else:
            st.markdown("## ✝️")
    with col2:
        st.markdown(f"## {title}")
    with col3:
        current = st.session_state.get("theme_choice", "Light")
        choice = st.selectbox(
            "Theme", ["Light", "Dark"],
            index=0 if current == "Light" else 1,
            key="theme_choice_select",
            label_visibility="collapsed"
        )
        if choice != current:
            st.session_state.theme_choice = choice
            st.rerun()
    st.markdown("---")

# ── LOGIN ──────────────────────────────────────────────
def login():
    show_header("UGGK Bible App")
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
                    st.query_params["uid"] = uid
                    st.rerun()
                else:
                    st.error("Profile not found. Contact admin.")
            else:
                st.error("Login failed. Check your email and password.")
        except Exception as e:
            st.error(f"Connection error: {e}")

    st.markdown("---")
    if st.button("New here? Create an Account"):
        st.session_state.show_signup = True
        st.rerun()

# ── ACCOUNT DELETION ─────────────────────────────────────
def delete_auth_user(user_id):
    res = requests.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
        }
    )
    return res.status_code in [200, 204]

def delete_account_section():
    st.warning(
        "⚠️ This will permanently delete your account and login access. "
        "This cannot be undone."
    )
    reason = st.text_area(
        "Please tell us why you're leaving — this helps us improve",
        key="del_reason"
    )
    confirm_phrase = st.text_input(
        'Type exactly: I Love Jesus Christ!',
        key="del_confirm"
    )
    if st.button("Permanently Delete My Account"):
        if not reason.strip():
            st.warning("Please provide a reason.")
        elif confirm_phrase.strip() != "I Love Jesus Christ!":
            st.error('Confirmation phrase does not match. Please type exactly: I Love Jesus Christ!')
        else:
            db_insert("account_deletions", {
                "user_id": st.session_state.uid,
                "reason": reason.strip(),
                "status": "completed"
            })
            db_delete("Profiles", "id", st.session_state.uid)
            delete_auth_user(st.session_state.uid)
            st.success("Your account has been deleted. Goodbye and God bless you. 🙏")
            st.session_state.clear()
            st.query_params.clear()
            st.stop()

# ── PROFILE ────────────────────────────────────────────
def profile_section():
    st.subheader("👤 My Profile")
    profile = db_select("Profiles", {"id": f"eq.{st.session_state.uid}"})
    current = profile[0] if profile else {}

    st.write(f"**Role:** {st.session_state.role.capitalize()}")

    if current.get("avatar_url"):
        st.image(current["avatar_url"], width=120, caption="Your photo")

    st.markdown("---")
    st.write("**Real Name** (required)")
    real_name = st.text_input("Full name", value=current.get("name",""), key="profile_real_name")

    st.write("**Display Name / Alias** — shown on the leaderboard, change anytime")
    alias = st.text_input("Alias", value=current.get("alias","") or "", key="profile_alias")

    if st.button("Save Profile Details"):
        if not real_name.strip():
            st.error("Real name cannot be empty.")
        else:
            result = db_update("Profiles", "id", st.session_state.uid, {
                "name": real_name.strip(),
                "alias": alias.strip() or None
            })
            if result is not None:
                st.session_state.name = real_name.strip()
                st.success("Profile updated!")
                st.rerun()
            else:
                st.error("Failed to update.")

    st.markdown("---")
    st.write("Update your profile picture:")
    avatar = st.file_uploader("Choose a photo", type=["jpg","jpeg","png"], key="avatar_upload")
    if avatar:
        st.image(avatar, width=120, caption="Preview")
        if st.button("Save Profile Picture"):
            filename = f"avatar_{st.session_state.uid}.{avatar.name.split('.')[-1]}"
            file_url = upload_file(avatar.getvalue(), filename, avatar.type)
            if file_url:
                db_update("Profiles", "id", st.session_state.uid, {"avatar_url": file_url})
                st.success("Profile picture updated!")
                st.rerun()
            else:
                st.error("Upload failed. Try again.")

    if st.session_state.role in ["parent", "child"]:
        st.markdown("---")
        with st.expander("🗑️ Delete My Account (Danger Zone)"):
            delete_account_section()

# ── ABOUT / FAQ ──────────────────────────────────────────
def about_us_faq_section():
    tab1, tab2 = st.tabs(["ℹ️ About Us", "❓ FAQ"])

    with tab1:
        st.subheader("About UGGK Bible App")
        st.write(
            "UGGK Bible App is a safe, child-friendly space where children "
            "grow in their faith through daily Bible verses, weekly "
            "announcements, fun quizzes, voice notes, and creative "
            "submissions — while parents stay connected to their child's "
            "journey and administrators provide guidance, marking, and "
            "encouragement along the way."
        )
        st.write(
            "Our goal is simple: to make learning God's Word joyful, "
            "engaging, and easy for the whole family."
        )

    with tab2:
        st.subheader("Frequently Asked Questions")
        faqs = [
            ("How do I reset my password?",
             "Please ask your parent (for children) or contact the app "
             "administrator to reset your password."),
            ("Can I add more than one child account?",
             "Yes — when you sign up, or anytime after, you can add "
             "additional children under your parent account."),
            ("How are quizzes marked?",
             "Submitted quiz answers are reviewed by an administrator. "
             "You'll get a notification on your home screen as soon as "
             "your mark is ready."),
            ("Who can see what I submit?",
             "Your submissions can be seen by app administrators (for "
             "marking) and by your linked parent. Other children cannot "
             "see your individual submissions."),
            ("How does the leaderboard work?",
             "Points are earned for every submission, with bonus points "
             "for submissions that have been marked. The top 5 children "
             "appear on the leaderboard."),
            ("How often do announcements change?",
             "Announcements run for the current week (Sunday to "
             "Saturday) and reset every Sunday at midnight. A pinned "
             "Welcome message always stays visible. Older announcements "
             "can be found in the Calendar tab."),
            ("How do I change my display name?",
             "Go to My Profile and update your Alias — this can be "
             "changed as often as you like."),
            ("How do I delete my account?",
             "Go to My Profile, open the 'Delete My Account' section at "
             "the bottom, give a reason, and type the confirmation "
             "phrase exactly as shown."),
        ]
        for q, a in faqs:
            with st.expander(q):
                st.write(a)

# ── HISTORY / CALENDAR VIEW ────────────────────────────────
def render_history_section():
    st.subheader("📅 Calendar / History")
    st.caption("Browse past verses, announcements, devotionals, and quizzes.")

    now_iso = datetime.utcnow().isoformat()
    tab_v, tab_a, tab_d, tab_q = st.tabs(["📖 Verses", "📢 Announcements", "📜 Devotionals", "📝 Quizzes"])

    with tab_v:
        verses = db_select("content", {"type": "eq.bible_verse", "order": "publish_at.desc"})
        verses = [v for v in verses if v.get("publish_at","") <= now_iso]
        if not verses:
            st.info("No verses posted yet.")
        for v in verses:
            with st.expander(f"{v.get('publish_at','')[:10]} — {v.get('title','')}"):
                st.write(v.get("body",""))

    with tab_a:
        anns = db_select("content", {"type": "eq.announcement", "order": "publish_at.desc"})
        anns = [a for a in anns if a.get("publish_at","") <= now_iso]
        if not anns:
            st.info("No announcements posted yet.")
        for a in anns:
            tag = "📌 " if a.get("is_pinned") else ""
            with st.expander(f"{a.get('publish_at','')[:10]} — {tag}{a.get('title','')}"):
                st.write(a.get("body",""))

    with tab_d:
        devs = db_select("content", {"type": "eq.devotional", "order": "publish_at.desc"})
        devs = [d for d in devs if d.get("publish_at","") <= now_iso]
        if not devs:
            st.info("No devotionals posted yet.")
        for d in devs:
            with st.expander(f"{d.get('publish_at','')[:10]} — {d.get('title','')}"):
                st.write(d.get("body",""))
                if d.get("link_url"):
                    st.markdown(f"[🔗 Link]({d['link_url']})")
                if d.get("media_url"):
                    if d["media_url"].endswith(".wav"):
                        st.audio(d["media_url"])
                    else:
                        st.image(d["media_url"], width=200)

    with tab_q:
        quizzes = db_select("content", {"type": "eq.quiz", "order": "publish_at.desc"})
        quizzes = [q for q in quizzes if q.get("publish_at","") <= now_iso]
        groups = {}
        for q in quizzes:
            g = q.get("quiz_group") or "Ungrouped"
            groups.setdefault(g, []).append(q)
        if not groups:
            st.info("No quizzes posted yet.")
        for g, qs in groups.items():
            with st.expander(f"{qs[0].get('publish_at','')[:10]} — {g} ({len(qs)} question(s))"):
                for q in qs:
                    st.write(f"**Q:** {q.get('body','')}")

# ── TERMS & SIGNUP ───────────────────────────────────────
def terms_and_conditions_text():
    return """
**UGGK Bible App — Terms & Conditions for Parents/Guardians**

1. **Parental Responsibility** — By creating accounts for your child or
   children, you confirm you are their parent or legal guardian and consent
   to their use of this app.

2. **Age Confirmation** — You confirm that each child account you create is
   for a person under the age of 18.

3. **Content** — Your child may upload images, voice notes, and quiz answers
   as part of Bible-based learning activities. These submissions may be
   viewed by app administrators for marking and engagement purposes, and by
   you (the linked parent).

4. **Supervision** — You are responsible for supervising your child's use of
   this app and the content they submit.

5. **Data** — Basic information (name, age, email, submissions) is stored
   securely and used only to operate this app's learning features.

6. **Conduct** — Content that is inappropriate, harmful, or unrelated to the
   purpose of this app may be removed by administrators at their discretion.

7. **Account Management** — You may request deletion of your account or your
   child's account at any time through the app.

By checking the box below and continuing, you agree to these terms on behalf
of yourself and any child accounts you create.
"""

def signup_page():
    show_header("Create Your Account")

    with st.expander("🔧 Connection Test (tap if Sign Up isn't working)"):
        if st.button("Run Test"):
            test1 = db_select("Profiles", {"limit": "1"})
            if test1 is not None:
                st.success("Database read: ✅ OK")
            else:
                st.error("Database read: ❌ Failed")

            try:
                r = requests.get(
                    f"{SUPABASE_URL}/auth/v1/admin/users",
                    headers={
                        "apikey": SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
                    },
                    params={"per_page": 1},
                    timeout=15
                )
                if r.status_code == 200:
                    st.success(f"Account creation key: ✅ OK (status {r.status_code})")
                else:
                    st.error(f"Account creation key: ❌ status {r.status_code}")
                    st.code(r.text[:500])
            except Exception as e:
                st.error(f"Account creation key: ❌ {e}")

    if "signup_step" not in st.session_state:
        st.session_state.signup_step = 1
    if "signup_children" not in st.session_state:
        st.session_state.signup_children = []

    if st.session_state.signup_step == 1:
        st.subheader("👤 Your Details")
        name     = st.text_input("Your full name", key="su_name")
        email    = st.text_input("Your email", key="su_email")
        password = st.text_input("Choose a password", type="password", key="su_pw")
        confirm  = st.text_input("Confirm password", type="password", key="su_pw2")

        st.markdown("---")
        with st.expander("📜 Read Terms & Conditions"):
            st.markdown(terms_and_conditions_text())
        agree = st.checkbox("I have read and agree to the Terms & Conditions")

        if st.button("Continue"):
            if not (name and email and password and confirm):
                st.warning("Please fill in all fields.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif not agree:
                st.warning("You must agree to the Terms & Conditions to continue.")
            else:
                with st.spinner("Creating your account..."):
                    user = create_auth_user(email, password)
                if not user or "id" not in user:
                    err = user.get("error", "Unknown error") if user else "Unknown error"
                    st.error(f"Could not create account: {err}")
                else:
                    profile_result = db_insert("Profiles", {
                        "id": user["id"],
                        "name": name,
                        "email": email,
                        "role": "parent",
                        "accepted_terms": True,
                        "accepted_terms_at": datetime.utcnow().isoformat()
                    })
                    if profile_result is not None:
                        st.session_state.su_parent_id = user["id"]
                        st.session_state.su_parent_name = name
                        st.session_state.signup_step = 2
                        st.rerun()
                    else:
                        st.error("Account created but profile setup failed. Contact admin.")

        st.markdown("---")
        if st.button("Already have an account? Log in"):
            st.session_state.show_signup = False
            st.rerun()

    elif st.session_state.signup_step == 2:
        st.subheader("👦👧 Add Your Child(ren)")
        st.write("Add at least one child account. You can add more later from your profile.")

        with st.form("add_child_form", clear_on_submit=True):
            c_name = st.text_input("Child's full name")
            c_age  = st.number_input("Child's age", min_value=1, max_value=17, step=1)
            c_pw   = st.text_input("Set a password for this child", type="password")
            added  = st.form_submit_button("➕ Add This Child")

            if added:
                if not c_name or not c_pw:
                    st.warning("Please enter the child's name and a password.")
                elif len(c_pw) < 4:
                    st.error("Child's password must be at least 4 characters.")
                elif c_age >= 18:
                    st.error("Child accounts must be under 18. For accounts 18+, please contact admin.")
                else:
                    st.session_state.signup_children.append({
                        "name": c_name, "age": int(c_age), "password": c_pw
                    })
                    st.success(f"{c_name} added to the list below.")

        if st.session_state.signup_children:
            st.markdown("---")
            st.write("**Children to be added:**")
            for i, c in enumerate(st.session_state.signup_children):
                col1, col2 = st.columns([4,1])
                col1.write(f"👦 {c['name']} — age {c['age']}")
                if col2.button("Remove", key=f"rm_{i}"):
                    st.session_state.signup_children.pop(i)
                    st.rerun()

        st.markdown("---")
        if st.button("✅ Finish Sign Up"):
            if not st.session_state.signup_children:
                st.warning("Please add at least one child before finishing.")
            else:
                created_credentials = []
                with st.spinner("Creating child accounts..."):
                    for c in st.session_state.signup_children:
                        child_email = generate_child_email(c["name"])
                        user = create_auth_user(child_email, c["password"])
                        if user and "id" in user:
                            db_insert("Profiles", {
                                "id": user["id"],
                                "name": c["name"],
                                "email": child_email,
                                "role": "child",
                                "age": c["age"],
                                "created_by": st.session_state.su_parent_id,
                                "accepted_terms": True,
                                "accepted_terms_at": datetime.utcnow().isoformat()
                            })
                            db_insert("parent_child", {
                                "parent_id": st.session_state.su_parent_id,
                                "child_id": user["id"]
                            })
                            created_credentials.append({
                                "name": c["name"], "email": child_email, "password": c["password"]
                            })
                        else:
                            err = user.get("error","Unknown error") if user else "Unknown error"
                            st.error(f"Could not create account for {c['name']}: {err}")

                st.session_state.signup_step = 3
                st.session_state.created_credentials = created_credentials
                st.rerun()

    elif st.session_state.signup_step == 3:
        st.success("🎉 Your account and your child accounts are ready!")
        st.subheader("📋 Save These Login Details")
        st.warning("Write these down or screenshot this — your child will need them to log in.")

        for c in st.session_state.created_credentials:
            st.info(f"**{c['name']}**\n\nEmail: `{c['email']}`\n\nPassword: `{c['password']}`")

        if st.button("Continue to App"):
            st.session_state.uid  = st.session_state.su_parent_id
            st.session_state.role = "parent"
            st.session_state.name = st.session_state.su_parent_name
            st.query_params["uid"] = st.session_state.su_parent_id

            for key in ["signup_step","signup_children","su_parent_id",
                        "su_parent_name","created_credentials","show_signup"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# ── ROLE APPLICATIONS ────────────────────────────────────
def apply_for_role():
    st.subheader("📋 Apply for a Role")
    st.write("Request additional access — for example, Pastor access to post daily teachings.")

    requested_role = st.selectbox("Role you're applying for", ["pastor"], key="apply_role")
    reason = st.text_area(
        "Tell the admin who you are and why",
        placeholder="e.g. I am Pastor Jane from XYZ Church and would like to post daily devotionals.",
        key="apply_reason"
    )
    if st.button("Submit Application"):
        if not reason:
            st.warning("Please tell the admin a bit about your request.")
        else:
            result = db_insert("role_applications", {
                "user_id": st.session_state.uid,
                "requested_role": requested_role,
                "reason": reason
            })
            if result is not None:
                st.success("Application submitted! The admin will review it.")
                st.rerun()
            else:
                st.error("Failed to submit. Try again.")

    my_apps = db_select("role_applications", {
        "user_id": f"eq.{st.session_state.uid}",
        "order": "created_at.desc"
    })
    if my_apps:
        st.markdown("---")
        st.subheader("Your Applications")
        for a in my_apps:
            icon = "✅" if a["status"]=="approved" else "❌" if a["status"]=="rejected" else "⏳"
            st.write(f"{icon} **{a['requested_role']}** — {a['status']}")

def admin_role_applications():
    st.subheader("👥 Role Applications")

    pending = db_select("role_applications", {"status": "eq.pending", "order": "created_at.asc"})
    st.metric("Pending Applications", len(pending))
    st.markdown("---")

    if not pending:
        st.success("No pending applications.")

    for a in pending:
        applicant = db_select("Profiles", {"id": f"eq.{a['user_id']}"})
        info = applicant[0] if applicant else {"name":"Unknown","email":"unknown"}

        with st.expander(f"{info['name']} ({info.get('email','')}) — wants: {a['requested_role']}"):
            st.write(f"**Reason:** {a.get('reason','')}")
            new_role = st.selectbox(
                "Assign role",
                ["pastor", "admin", "parent", "child"],
                index=["pastor","admin","parent","child"].index(a["requested_role"])
                      if a["requested_role"] in ["pastor","admin","parent","child"] else 0,
                key=f"role_select_{a['id']}"
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve", key=f"approve_{a['id']}"):
                    db_update("Profiles", "id", a["user_id"], {"role": new_role})
                    db_update("role_applications", "id", a["id"], {"status": "approved"})
                    st.success(f"Approved — {info['name']} is now {new_role}.")
                    st.rerun()
            with col2:
                if st.button("❌ Reject", key=f"reject_{a['id']}"):
                    db_update("role_applications", "id", a["id"], {"status": "rejected"})
                    st.warning("Application rejected.")
                    st.rerun()

    history = db_select("role_applications", {"status": "neq.pending", "order": "created_at.desc"})
    if history:
        st.markdown("---")
        st.subheader("History")
        for a in history:
            applicant = db_select("Profiles", {"id": f"eq.{a['user_id']}"})
            name = applicant[0]["name"] if applicant else "Unknown"
            icon = "✅" if a["status"]=="approved" else "❌"
            st.write(f"{icon} {name} — {a['requested_role']} — {a['status']}")

# ── LEADERBOARD ──────────────────────────────────────────
def compute_leaderboard():
    children = db_select("Profiles", {"role": "eq.child"})
    board = []
    for child in children:
        subs   = db_select("submissions", {"child_id": f"eq.{child['id']}"})
        total  = len(subs)
        marked = len([s for s in subs if s.get("mark")])
        points = total + (marked * 2)
        board.append({
            "id": child["id"],
            "name": child.get("alias") or child.get("name") or "Unknown",
            "real_name": child.get("name",""),
            "email": child.get("email",""),
            "total": total,
            "marked": marked,
            "points": points
        })
    board.sort(key=lambda x: x["points"], reverse=True)
    for i, entry in enumerate(board):
        entry["rank"] = i + 1
    return board

def medal_for(rank):
    return {1:"🥇", 2:"🥈", 3:"🥉"}.get(rank, f"#{rank}")

def admin_leaderboard():
    st.subheader("🏆 Leaderboard")
    st.caption("Points = 1 per submission + 2 bonus per marked submission.")
    board = compute_leaderboard()
    if not board:
        st.info("No children registered yet.")
        return
    for entry in board:
        with st.expander(f"{medal_for(entry['rank'])} {entry['name']} — {entry['points']} points"):
            st.write(f"Real name: {entry['real_name']}")
            st.write(f"Email: {entry['email']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Points", entry["points"])
            c2.metric("Submissions", entry["total"])
            c3.metric("Marked", entry["marked"])

def parent_leaderboard(linked_child_ids):
    st.subheader("🏆 Your Child's Ranking")
    board = compute_leaderboard()
    if not board:
        st.info("Leaderboard is empty.")
        return
    for entry in board:
        if entry["id"] in linked_child_ids:
            st.success(
                f"{medal_for(entry['rank'])} **{entry['real_name']}** is ranked "
                f"#{entry['rank']} of {len(board)} with {entry['points']} points!"
            )
            c1, c2 = st.columns(2)
            c1.metric("Submissions", entry["total"])
            c2.metric("Marked", entry["marked"])
    st.markdown("---")
    st.caption("Top 5 Overall")
    for entry in board[:5]:
        st.write(f"{medal_for(entry['rank'])} {entry['name']} — {entry['points']} pts")

def child_leaderboard(my_id):
    st.subheader("🏆 Top 5 Champions")
    board = compute_leaderboard()
    if not board:
        st.info("No leaderboard yet — be the first to submit!")
        return
    for entry in board[:5]:
        highlight = " (You!)" if entry["id"] == my_id else ""
        st.write(f"{medal_for(entry['rank'])} **{entry['name']}**{highlight} — {entry['points']} pts")
    my_entry = next((e for e in board if e["id"] == my_id), None)
    if my_entry and my_entry["rank"] > 5:
        st.markdown("---")
        st.info(f"You're ranked #{my_entry['rank']} with {my_entry['points']} points. Keep going! 🙌")

# ── CHILD ──────────────────────────────────────────────
def child_dashboard():
    show_header(f"Hi, {st.session_state.name} 👋")

    all_my_subs = db_select("submissions", {"child_id": f"eq.{st.session_state.uid}"})
    new_marks   = [s for s in all_my_subs if s.get("mark") and not s.get("mark_seen")]
    if new_marks:
        st.success(f"🎉 You have {len(new_marks)} new mark(s)! Check **Results** to see them.")

    tabs = st.tabs([
        "🏠 Home", "📝 Quiz", "🎤 Voice", "🖼️ Image",
        "📊 Results", "🏆 Leaderboard", "👤 Profile", "ℹ️ About"
    ])

    # ── HOME ──
    with tabs[0]:
        now_iso = datetime.utcnow().isoformat()

        pinned = get_pinned_items("announcement")
        for p in pinned:
            st.info(f"📌 **{p.get('title','')}**\n\n{p.get('body','')}")

        st.subheader("📖 Verse of the Day")
        verses = db_select("content", {
            "type": "eq.bible_verse",
            "publish_at": f"lte.{now_iso}",
            "order": "publish_at.desc",
            "limit": "1"
        })
        if verses:
            st.success(f"**{verses[0].get('title','')}**\n\n{verses[0].get('body','')}")
        else:
            st.markdown("""
                <div style='text-align:center;padding:20px;
                background:rgba(46,134,171,0.12);border-radius:15px;'>
                <h3>📖 No verse today yet</h3>
                <p>Check back soon for today's Bible verse!</p>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📢 This Week's Announcements")
        st.caption(f"Week of {get_week_label()}")
        week_anns = get_current_week_items("announcement")
        if week_anns:
            for a in week_anns:
                st.success(f"**{a.get('title','')}**\n\n{a.get('body','')}")
        else:
            st.write("No new announcements this week.")

    # ── QUIZ ──
    with tabs[1]:
        st.subheader("📝 Quiz Time!")
        now_iso     = datetime.utcnow().isoformat()
        all_quizzes = db_select("content", {
            "type": "eq.quiz",
            "publish_at": f"lte.{now_iso}"
        })
        if not all_quizzes:
            st.info("No quizzes available yet. Check back soon!")
        else:
            groups = {}
            for q in all_quizzes:
                group = q.get("quiz_group") or q.get("title","General")
                groups.setdefault(group, []).append(q)
            selected_group = st.selectbox("Choose a quiz:", list(groups.keys()))
            st.markdown("---")
            questions = groups[selected_group]
            st.markdown(f"### {selected_group}")
            st.write(f"{len(questions)} question(s)")
            st.markdown("---")
            answers       = {}
            audio_answers = {}
            file_answers  = {}
            for i, quiz in enumerate(questions):
                st.markdown(f"**Question {i+1}: {quiz.get('body','')}**")

                if quiz.get("media_url"):
                    if quiz["media_url"].endswith(".wav"):
                        st.audio(quiz["media_url"])
                    else:
                        st.image(quiz["media_url"], width=250)
                if quiz.get("link_url"):
                    st.markdown(f"[🔗 Open Link]({quiz['link_url']})")

                q_type      = quiz.get("question_type","text")
                options_raw = quiz.get("options","")
                if q_type == "multiple_choice" and options_raw:
                    options = [o.strip() for o in options_raw.split("|")]
                    answers[quiz["id"]] = st.radio(
                        "Choose your answer:", options, key=f"radio_{quiz['id']}"
                    )
                elif q_type == "voice":
                    st.write("Record your answer:")
                    audio_bytes = audio_recorder(
                        text="", recording_color="#e74c3c",
                        neutral_color="#2ecc71", icon_size="2x",
                        key=f"audio_{quiz['id']}"
                    )
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/wav")
                        audio_answers[quiz["id"]] = audio_bytes
                elif q_type == "document":
                    uploaded = st.file_uploader(
                        "Upload your document:",
                        type=["pdf","doc","docx","txt","png","jpg"],
                        key=f"doc_{quiz['id']}"
                    )
                    if uploaded:
                        file_answers[quiz["id"]] = uploaded
                else:
                    answers[quiz["id"]] = st.text_area(
                        "Your answer:", key=f"text_{quiz['id']}"
                    )
                st.markdown("---")

            if st.button("Submit All Answers 🎉"):
                success_count = 0
                for quiz in questions:
                    qid      = quiz["id"]
                    file_url = None
                    content  = None
                    if qid in audio_answers:
                        filename = f"{st.session_state.uid}_quiz_audio_{qid}.wav"
                        file_url = upload_file(audio_answers[qid], filename, "audio/wav")
                        content  = "Voice answer"
                    elif qid in file_answers:
                        f        = file_answers[qid]
                        filename = f"{st.session_state.uid}_quiz_doc_{qid}_{f.name}"
                        file_url = upload_file(f.getvalue(), filename, f.type)
                        content  = f"Document: {f.name}"
                    elif qid in answers:
                        content = answers[qid]
                    result = db_insert("submissions", {
                        "child_id":  st.session_state.uid,
                        "content":   content,
                        "file_url":  file_url,
                        "file_type": "quiz"
                    })
                    if result is not None:
                        success_count += 1
                if success_count == len(questions):
                    st.success(f"All {success_count} answers submitted! Well done 🎉")
                    st.balloons()
                else:
                    st.warning(f"{success_count} of {len(questions)} submitted.")

    # ── VOICE ──
    with tabs[2]:
        st.subheader("🎤 Record Your Voice")
        st.write("Press the microphone to start. Press again to stop.")
        audio_bytes = audio_recorder(
            text="", recording_color="#e74c3c",
            neutral_color="#2ecc71", icon_size="3x"
        )
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            if st.button("Submit Recording"):
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                filename  = f"{st.session_state.uid}_voice_{timestamp}.wav"
                file_url  = upload_file(audio_bytes, filename, "audio/wav")
                if file_url:
                    db_insert("submissions", {
                        "child_id": st.session_state.uid,
                        "file_url": file_url,
                        "file_type": "voice"
                    })
                    st.success("Recording submitted!")
                else:
                    st.error("Upload failed. Try again.")

    # ── IMAGE ──
    with tabs[3]:
        st.subheader("🖼️ Upload an Image")
        file = st.file_uploader("Choose an image", type=["jpg","jpeg","png"])
        if file:
            st.image(file, caption="Preview", use_column_width=True)
            if st.button("Submit Image"):
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                filename  = f"{st.session_state.uid}_image_{timestamp}_{file.name}"
                file_url  = upload_file(file.getvalue(), filename, file.type)
                if file_url:
                    db_insert("submissions", {
                        "child_id": st.session_state.uid,
                        "file_url": file_url,
                        "file_type": "image"
                    })
                    st.success("Image uploaded!")
                else:
                    st.error("Upload failed. Try again.")

    # ── RESULTS ──
    with tabs[4]:
        st.subheader("📊 My Results")
        subs = db_select("submissions", {"child_id": f"eq.{st.session_state.uid}"})
        if not subs:
            st.info("You have not submitted anything yet.")
        else:
            quizzes = [s for s in subs if s.get("file_type") == "quiz"]
            images  = [s for s in subs if s.get("file_type") == "image"]
            voices  = [s for s in subs if s.get("file_type") == "voice"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Quiz Answers", len(quizzes))
            col2.metric("Images", len(images))
            col3.metric("Voice Notes", len(voices))
            st.markdown("---")

            if quizzes:
                st.subheader("📝 Quiz Results")
                marked   = [q for q in quizzes if q.get("mark")]
                unmarked = [q for q in quizzes if not q.get("mark")]
                if marked:
                    st.markdown(f"**✅ Marked ({len(marked)})**")
                    for q in marked:
                        if not q.get("mark_seen"):
                            db_update("submissions", "id", q["id"], {"mark_seen": True})
                        submitted = q.get("created_at","")[:10] if q.get("created_at") else ""
                        with st.expander(f"✅ Submitted {submitted} — Mark: {q['mark']}"):
                            if q.get("content"):
                                st.write(f"**Your answer:** {q['content']}")
                            if q.get("file_url"):
                                st.markdown(f"[View your submitted file]({q['file_url']})")
                            st.success(f"🏆 Mark: **{q['mark']}**")
                if unmarked:
                    st.markdown(f"**⏳ Waiting for marks ({len(unmarked)})**")
                    for q in unmarked:
                        submitted = q.get("created_at","")[:10] if q.get("created_at") else ""
                        with st.expander(f"⏳ Submitted {submitted} — Not marked yet"):
                            if q.get("content"):
                                st.write(f"**Your answer:** {q['content']}")
                            if q.get("file_url"):
                                st.markdown(f"[View your submitted file]({q['file_url']})")
                            st.warning("Your teacher has not marked this yet.")

            if images:
                st.markdown("---")
                st.subheader(f"🖼️ My Images ({len(images)})")
                for img in images:
                    if img.get("file_url"):
                        submitted = img.get("created_at","")[:10] if img.get("created_at") else ""
                        st.write(f"Submitted: {submitted}")
                        st.image(img["file_url"], width=250)

            if voices:
                st.markdown("---")
                st.subheader(f"🎤 My Voice Notes ({len(voices)})")
                for v in voices:
                    if v.get("file_url"):
                        submitted = v.get("created_at","")[:10] if v.get("created_at") else ""
                        st.write(f"Submitted: {submitted}")
                        st.audio(v["file_url"])

    # ── LEADERBOARD ──
    with tabs[5]:
        child_leaderboard(st.session_state.uid)

    # ── PROFILE ──
    with tabs[6]:
        profile_section()

    # ── ABOUT ──
    with tabs[7]:
        about_us_faq_section()

# ── PARENT ─────────────────────────────────────────────
def parent_dashboard():
    show_header("Parent Dashboard")
    tabs = st.tabs([
        "📖 Content", "👦 My Children", "📅 Calendar",
        "🏆 Leaderboard", "👤 Profile", "ℹ️ About", "📋 Apply for Role"
    ])

    # ── CONTENT ──
    with tabs[0]:
        now_iso = datetime.utcnow().isoformat()

        pinned = get_pinned_items("announcement")
        for p in pinned:
            st.info(f"📌 **{p.get('title','')}**\n\n{p.get('body','')}")

        st.subheader("📢 This Week's Announcements")
        st.caption(f"Week of {get_week_label()}")
        week_anns = get_current_week_items("announcement")
        if week_anns:
            for a in week_anns:
                st.success(f"**{a.get('title','')}**\n\n{a.get('body','')}")
        else:
            st.write("No new announcements this week.")

        st.markdown("---")
        st.subheader("📜 Pastor's Notes")
        devotionals = db_select("content", {"type": "eq.devotional", "order": "publish_at.desc"})
        devotionals = [d for d in devotionals if d.get("publish_at","") <= now_iso][:5]

        if not devotionals:
            st.write("No teachings posted yet.")

        for d in devotionals:
            st.markdown(f"**{d.get('title','')}** — {d.get('publish_at','')[:10]}")
            st.write(d.get("body",""))
            if d.get("link_url"):
                st.markdown(f"[🔗 Watch / Listen]({d['link_url']})")
            if d.get("media_url"):
                if d["media_url"].endswith(".wav"):
                    st.audio(d["media_url"])
                else:
                    st.image(d["media_url"], width=200)

            likes, dislikes, acks, _ = get_reaction_counts(d["id"])
            my_reactions = get_my_reactions(d["id"], st.session_state.uid)
            my_types = [r["reaction"] for r in my_reactions]

            c1, c2, c3 = st.columns(3)
            with c1:
                label = "👍 Liked" if "like" in my_types else "👍 Like"
                if st.button(label, key=f"like_{d['id']}"):
                    toggle_reaction(d["id"], st.session_state.uid, "like")
                    st.rerun()
            with c2:
                label = "👎 Disliked" if "dislike" in my_types else "👎 Dislike"
                if st.button(label, key=f"dislike_{d['id']}"):
                    toggle_reaction(d["id"], st.session_state.uid, "dislike")
                    st.rerun()
            with c3:
                label = "✅ Received" if "ack" in my_types else "✅ Mark as Received"
                if st.button(label, key=f"ack_{d['id']}"):
                    toggle_reaction(d["id"], st.session_state.uid, "ack")
                    st.rerun()

            st.caption(f"👍 {likes} · 👎 {dislikes} · ✅ {acks} acknowledged")
            st.markdown("---")

    # ── MY CHILDREN ──
    with tabs[1]:
        links = db_select("parent_child", {"parent_id": f"eq.{st.session_state.uid}"})
        if not links:
            st.warning("No children linked to your account. Contact admin.")
        else:
            for link in links:
                child_id = link["child_id"]
                profiles = db_select("Profiles", {"id": f"eq.{child_id}"})
                if not profiles:
                    continue
                child = profiles[0]
                st.subheader(f"👦 {child['name']}")
                subs = db_select("submissions", {"child_id": f"eq.{child_id}"})

                pending = [s for s in subs if s.get("file_type") == "quiz" and not s.get("mark")]
                if pending:
                    st.warning(f"⏳ {len(pending)} submission(s) pending review")
                else:
                    st.success("✅ All caught up — nothing pending")

                if not subs:
                    st.markdown("""
                        <div style='text-align:center;padding:20px;
                        background:rgba(46,134,171,0.08);border-radius:15px;'>
                        <h3>📭 No activity yet</h3>
                        <p>Your child has not submitted anything yet.</p>
                        </div>""", unsafe_allow_html=True)
                else:
                    images  = [s for s in subs if s.get("file_type") == "image"]
                    voices  = [s for s in subs if s.get("file_type") == "voice"]
                    quizzes = [s for s in subs if s.get("file_type") == "quiz"]
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Images", len(images))
                    col2.metric("Voice Notes", len(voices))
                    col3.metric("Quiz Answers", len(quizzes))
                    if images:
                        st.markdown("🖼️ **Images**")
                        for img in images:
                            if img.get("file_url"):
                                st.image(img["file_url"], width=200)
                    if voices:
                        st.markdown("🎤 **Voice Notes**")
                        for v in voices:
                            if v.get("file_url"):
                                st.audio(v["file_url"])
                    if quizzes:
                        st.markdown("📝 **Quiz Results**")
                        for q in quizzes:
                            with st.expander("View answer"):
                                if q.get("content"):
                                    st.write(q["content"])
                                if q.get("file_url"):
                                    st.markdown(f"[View submitted file]({q['file_url']})")
                                if q.get("mark"):
                                    st.success(f"✅ Mark: {q['mark']}")
                                else:
                                    st.warning("⏳ Not marked yet")
                st.markdown("---")

    # ── CALENDAR ──
    with tabs[2]:
        render_history_section()

    # ── LEADERBOARD ──
    with tabs[3]:
        links = db_select("parent_child", {"parent_id": f"eq.{st.session_state.uid}"})
        child_ids = [l["child_id"] for l in links]
        parent_leaderboard(child_ids)

    # ── PROFILE ──
    with tabs[4]:
        profile_section()

    # ── ABOUT ──
    with tabs[5]:
        about_us_faq_section()

    # ── APPLY FOR ROLE ──
    with tabs[6]:
        apply_for_role()

# ── PASTOR ─────────────────────────────────────────────
def pastor_dashboard():
    show_header("Pastor's Corner")
    tab1, tab2 = st.tabs(["✍️ Post Teaching", "📜 My Posts"])

    with tab1:
        st.subheader("✍️ New Teaching")
        title = st.text_input("Title", key="pastor_title")
        body  = st.text_area("Message / Teaching text", key="pastor_body")

        st.write("Optional — add a link (e.g. YouTube sermon):")
        link_url = st.text_input("Link URL", key="pastor_link", placeholder="https://...")

        st.write("Optional — attach an image or voice note:")
        media_type = st.selectbox("Attachment type", ["None", "Image", "Voice Recording"], key="pastor_media_type")

        if media_type == "Image":
            img = st.file_uploader("Choose an image", type=["jpg","jpeg","png"], key="pastor_img")
            if img:
                st.image(img, width=200)
                if st.button("Upload Image", key="pastor_img_upload_btn"):
                    fname = f"pastor_{st.session_state.uid}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{img.name}"
                    url = upload_file(img.getvalue(), fname, img.type)
                    if url:
                        st.session_state.pastor_media_url = url
                        st.success("Image uploaded — now click Post Teaching Now below.")

        elif media_type == "Voice Recording":
            audio_bytes = audio_recorder(
                text="", recording_color="#e74c3c",
                neutral_color="#2ecc71", icon_size="2x", key="pastor_audio"
            )
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if st.button("Upload Recording", key="pastor_audio_upload_btn"):
                    fname = f"pastor_{st.session_state.uid}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.wav"
                    url = upload_file(audio_bytes, fname, "audio/wav")
                    if url:
                        st.session_state.pastor_media_url = url
                        st.success("Recording uploaded — now click Post Teaching Now below.")

        if st.session_state.get("pastor_media_url"):
            st.success("✅ Media attached and ready to post.")

        st.markdown("---")
        if st.button("📤 Post Teaching Now"):
            if not title or not body:
                st.warning("Please add a title and message.")
            else:
                result = db_insert("content", {
                    "type": "devotional",
                    "title": title,
                    "body": body,
                    "link_url": link_url or None,
                    "media_url": st.session_state.get("pastor_media_url"),
                    "posted_by": st.session_state.uid,
                    "publish_at": datetime.utcnow().isoformat()
                })
                if result is not None:
                    st.success("Teaching posted! Parents can see it now.")
                    st.session_state.pop("pastor_media_url", None)
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to post. Check terminal.")

    with tab2:
        st.subheader("📜 My Posts")
        posts = db_select("content", {
            "type": "eq.devotional",
            "posted_by": f"eq.{st.session_state.uid}",
            "order": "publish_at.desc"
        })
        if not posts:
            st.info("You haven't posted any teachings yet.")
        for p in posts:
            likes, dislikes, acks, _ = get_reaction_counts(p["id"])
            with st.expander(f"{p.get('title','')} — {p.get('publish_at','')[:10]}"):
                st.write(p.get("body",""))
                if p.get("link_url"):
                    st.markdown(f"[🔗 Link]({p['link_url']})")
                if p.get("media_url"):
                    if p["media_url"].endswith(".wav"):
                        st.audio(p["media_url"])
                    else:
                        st.image(p["media_url"], width=200)
                st.caption(f"👍 {likes} · 👎 {dislikes} · ✅ {acks} parents acknowledged")
                if st.button("🗑️ Delete this post", key=f"del_{p['id']}"):
                    db_delete("content", "id", p["id"])
                    st.success("Deleted.")
                    st.rerun()

# ── ADMIN ──────────────────────────────────────────────
def admin_dashboard():
    show_header("Admin Dashboard")
    tabs = st.tabs([
        "📊 Overview", "📅 Calendar", "📖 Verses", "📝 Quizzes",
        "📢 Announcements", "✅ Mark", "👥 Roles", "🏆 Leaderboard", "🎨 Branding"
    ])
    with tabs[0]: admin_overview()
    with tabs[1]: admin_calendar()
    with tabs[2]: admin_verses()
    with tabs[3]: admin_quizzes()
    with tabs[4]: admin_announcements()
    with tabs[5]: admin_mark()
    with tabs[6]: admin_role_applications()
    with tabs[7]: admin_leaderboard()
    with tabs[8]: admin_branding()

def admin_overview():
    st.subheader("📊 Overview")
    with st.spinner("Loading data..."):
        children = db_select("Profiles", {"role": "eq.child"})
        all_subs = db_select("submissions", {})
    st.metric("Total Children Registered", len(children))
    col1, col2, col3 = st.columns(3)
    col1.metric("📷 Images",       len([s for s in all_subs if s.get("file_type")=="image"]))
    col2.metric("🎤 Voice Notes",  len([s for s in all_subs if s.get("file_type")=="voice"]))
    col3.metric("📝 Quiz Answers", len([s for s in all_subs if s.get("file_type")=="quiz"]))
    st.markdown("---")
    if not children:
        st.info("No children registered yet.")
        return
    st.subheader("Children Activity")
    for child in children:
        subs     = db_select("submissions", {"child_id": f"eq.{child['id']}"})
        marked   = len([s for s in subs if s.get("mark")])
        unmarked = len([s for s in subs if s.get("file_type")=="quiz" and not s.get("mark")])
        with st.expander(f"👦 {child['name']} — {len(subs)} submissions"):
            st.write(f"Email: {child.get('email','')}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(subs))
            c2.metric("Marked", marked)
            c3.metric("Needs Marking", unmarked)
            recent = sorted(subs, key=lambda x: x.get("created_at",""), reverse=True)[:3]
            if recent:
                st.write("Recent submissions:")
                for r in recent:
                    st.write(f"— {r.get('file_type','')} submitted {r.get('created_at','')[:10]}")

def admin_calendar():
    st.subheader("📅 Content Calendar")
    st.caption("See all scheduled content and track what has been published.")
    all_content = db_select("content", {"order": "publish_at.asc"})
    now         = datetime.utcnow()
    published   = [c for c in all_content if c.get("publish_at") and c["publish_at"] <= now.isoformat()]
    scheduled   = [c for c in all_content if c.get("publish_at") and c["publish_at"] > now.isoformat()]
    st.markdown(f"### ✅ Published ({len(published)})")
    if published:
        for c in published:
            icon = "📖" if c["type"]=="bible_verse" else "📝" if c["type"]=="quiz" else "📢"
            tag = "📌 " if c.get("is_pinned") else ""
            st.success(f"{icon} {tag}**{c.get('title','')}** — {c['type']} — {c.get('publish_at','')[:10]}")
    else:
        st.write("Nothing published yet.")
    st.markdown("---")
    st.markdown(f"### ⏳ Scheduled ({len(scheduled)})")
    if scheduled:
        for c in scheduled:
            icon = "📖" if c["type"]=="bible_verse" else "📝" if c["type"]=="quiz" else "📢"
            st.warning(f"{icon} **{c.get('title','')}** — {c['type']} — publishes {c.get('publish_at','')[:10]}")
    else:
        st.write("Nothing scheduled yet.")
    st.markdown("---")
    render_history_section()

def admin_verses():
    st.subheader("📖 Bible Verses")
    verses = db_select("content", {"type": "eq.bible_verse", "order": "publish_at.desc"})
    if verses:
        for v in verses:
            status = "✅ Live" if v.get("publish_at","") <= datetime.utcnow().isoformat() else "⏳ Scheduled"
            st.info(f"{status} | **{v.get('title','')}** — {v.get('body','')}")
    else:
        st.write("No verses yet.")
    st.markdown("---")
    st.subheader("Add New Verse")
    title      = st.text_input("Verse reference (e.g. John 3:16)", key="verse_title")
    body       = st.text_area("Full verse text", key="verse_body")
    pub_date   = st.date_input("Publish date", value=date.today(), key="verse_date")
    pub_time   = st.time_input("Publish time", value=time(8, 0), key="verse_time")
    publish_at = datetime.combine(pub_date, pub_time).isoformat()
    if st.button("Schedule Verse"):
        if title and body:
            result = db_insert("content", {
                "type": "bible_verse", "title": title,
                "body": body, "publish_at": publish_at
            })
            if result is not None:
                st.success(f"Verse scheduled for {pub_date}!")
                st.rerun()
            else:
                st.error("Failed to post. Check terminal.")
        else:
            st.warning("Fill in both fields.")

def admin_quizzes():
    st.subheader("📝 Quizzes")
    quizzes = db_select("content", {"type": "eq.quiz", "order": "publish_at.desc"})
    if quizzes:
        groups = {}
        for q in quizzes:
            g = q.get("quiz_group") or "Ungrouped"
            groups.setdefault(g, []).append(q)
        for group, qs in groups.items():
            status = "✅" if qs[0].get("publish_at","") <= datetime.utcnow().isoformat() else "⏳"
            with st.expander(f"{status} {group} — {len(qs)} question(s)"):
                for q in qs:
                    st.write(f"**Q:** {q.get('body','')}")
                    st.write(f"Type: {q.get('question_type','text')}")
                    if q.get("options"):
                        st.write(f"Options: {q.get('options','')}")
    else:
        st.write("No quizzes yet.")

    st.markdown("---")
    st.subheader("Add Quiz Question")
    quiz_group = st.text_input(
        "Quiz group name", placeholder="e.g. Week 1 Quiz", key="quiz_group"
    )
    body   = st.text_area("Question text", key="quiz_body")
    q_type = st.selectbox("Question type", [
        "text", "multiple_choice", "voice", "document"
    ], key="quiz_type")
    options = ""
    if q_type == "multiple_choice":
        options = st.text_input(
            "Options — separate with | symbol",
            placeholder="A) Moses|B) Noah|C) David",
            key="quiz_options"
        )

    st.write("Optional — attach media to this question:")
    q_media_type = st.selectbox("Question media", ["None","Image","Voice Recording","Link"], key="quiz_q_media_type")

    q_link_url = ""
    if q_media_type == "Image":
        qimg = st.file_uploader("Choose an image", type=["jpg","jpeg","png"], key="quiz_q_img")
        if qimg:
            st.image(qimg, width=200)
            if st.button("Upload Question Image", key="quiz_q_img_btn"):
                fname = f"quizmedia_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{qimg.name}"
                url = upload_file(qimg.getvalue(), fname, qimg.type)
                if url:
                    st.session_state.quiz_q_media_url = url
                    st.success("Image attached — now click Add Question below.")

    elif q_media_type == "Voice Recording":
        q_audio = audio_recorder(
            text="", recording_color="#e74c3c",
            neutral_color="#2ecc71", icon_size="2x", key="quiz_q_audio"
        )
        if q_audio:
            st.audio(q_audio, format="audio/wav")
            if st.button("Upload Question Audio", key="quiz_q_audio_btn"):
                fname = f"quizmedia_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.wav"
                url = upload_file(q_audio, fname, "audio/wav")
                if url:
                    st.session_state.quiz_q_media_url = url
                    st.success("Audio attached — now click Add Question below.")

    elif q_media_type == "Link":
        q_link_url = st.text_input("Link URL", key="quiz_q_link", placeholder="https://...")

    if st.session_state.get("quiz_q_media_url"):
        st.success("✅ Media attached and ready.")

    pub_date   = st.date_input("Publish date", value=date.today(), key="quiz_date")
    pub_time   = st.time_input("Publish time", value=time(8, 0), key="quiz_time")
    publish_at = datetime.combine(pub_date, pub_time).isoformat()

    if st.button("Add Question"):
        if quiz_group and body:
            result = db_insert("content", {
                "type": "quiz", "title": quiz_group,
                "quiz_group": quiz_group, "body": body,
                "question_type": q_type,
                "options": options or None,
                "media_url": st.session_state.get("quiz_q_media_url"),
                "link_url": q_link_url or None,
                "publish_at": publish_at
            })
            if result is not None:
                st.success("Question added!")
                st.session_state.pop("quiz_q_media_url", None)
                st.rerun()
            else:
                st.error("Failed to add. Check terminal.")
        else:
            st.warning("Fill in quiz group and question text.")

def admin_announcements():
    st.subheader("📢 Announcements")
    st.caption(f"Current week: {get_week_label()} (resets every Sunday)")

    pinned = get_pinned_items("announcement")
    if pinned:
        st.info(f"📌 Current Welcome Message: **{pinned[0].get('title','')}**")
        st.write(pinned[0].get("body",""))

    st.markdown("---")
    week_anns = get_current_week_items("announcement")
    if week_anns:
        st.write("**This week's announcements:**")
        for a in week_anns:
            st.success(f"**{a.get('title','')}** — {a.get('body','')}")
    else:
        st.write("No announcements posted for this week yet.")

    st.markdown("---")
    st.subheader("Post New Announcement")
    title    = st.text_input("Title", key="ann_title")
    body     = st.text_area("Message", key="ann_body")
    pin_this = st.checkbox(
        "📌 Make this the permanent Welcome message (shown to everyone, "
        "replaces any previous pinned message, doesn't expire)",
        key="ann_pin"
    )
    pub_date   = st.date_input("Publish date", value=date.today(), key="ann_date")
    pub_time   = st.time_input("Publish time", value=time(8, 0), key="ann_time")
    publish_at = datetime.combine(pub_date, pub_time).isoformat()

    if st.button("Post Announcement"):
        if title and body:
            if pin_this:
                existing_pinned = db_select("content", {"type": "eq.announcement", "is_pinned": "eq.true"})
                for ep in existing_pinned:
                    db_update("content", "id", ep["id"], {"is_pinned": False})
            result = db_insert("content", {
                "type": "announcement", "title": title,
                "body": body, "publish_at": publish_at,
                "is_pinned": pin_this
            })
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
    unmarked = [s for s in subs if not s.get("mark")]
    marked   = [s for s in subs if s.get("mark")]
    col1, col2 = st.columns(2)
    col1.metric("Needs Marking", len(unmarked))
    col2.metric("Already Marked", len(marked))
    st.markdown("---")
    st.subheader("Needs Marking")
    if not unmarked:
        st.success("All submissions are marked! 🎉")
    for sub in unmarked:
        profile    = db_select("Profiles", {"id": f"eq.{sub['child_id']}"})
        child_name = profile[0]["name"] if profile else "Unknown"
        with st.expander(f"👦 {child_name} — click to mark"):
            if sub.get("content"):
                st.write(f"Answer: {sub['content']}")
            if sub.get("file_url"):
                st.markdown(f"[View submitted file]({sub['file_url']})")
            new_mark = st.text_input(
                "Enter mark (e.g. 8/10 or Well done!)",
                key=f"mark_{sub['id']}"
            )
            if st.button("Save Mark", key=f"save_{sub['id']}"):
                result = db_update("submissions", "id", sub["id"], {"mark": new_mark})
                if result is not None:
                    st.success("Mark saved!")
                    st.rerun()
                else:
                    st.error("Failed to save mark.")
    if marked:
        st.markdown("---")
        st.subheader("Already Marked")
        for sub in marked:
            profile    = db_select("Profiles", {"id": f"eq.{sub['child_id']}"})
            child_name = profile[0]["name"] if profile else "Unknown"
            st.success(f"👦 {child_name} — Mark: {sub['mark']}")

def admin_branding():
    st.subheader("🎨 App Branding")
    st.write("Upload your organisation's logo — it replaces the ✝️ shown across the app header.")

    current = get_app_logo_url()
    if current:
        st.image(current, width=120, caption="Current logo")

    logo = st.file_uploader("Upload new logo", type=["png","jpg","jpeg"], key="app_logo_upload")
    if logo:
        st.image(logo, width=120, caption="Preview")
        if st.button("Save as App Logo"):
            fname = f"app_logo_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{logo.name}"
            url = upload_file(logo.getvalue(), fname, logo.type)
            if url:
                existing = db_select("content", {"type": "eq.app_logo"})
                if existing:
                    db_update("content", "id", existing[0]["id"], {"media_url": url})
                else:
                    db_insert("content", {
                        "type": "app_logo",
                        "title": "App Logo",
                        "body": "",
                        "media_url": url,
                        "publish_at": datetime.utcnow().isoformat()
                    })
                st.success("Logo updated! It will appear across the app.")
                st.rerun()
            else:
                st.error("Upload failed. Try again.")

# ── ROUTER ─────────────────────────────────────────────
if st.session_state.get("logged_out"):
    show_header("UGGK Bible App")
    st.success("✅ You have been logged out successfully. God bless you! 🙏")
    if st.button("Back to Login"):
        st.session_state.logged_out = False
        st.rerun()
    st.stop()

if "role" not in st.session_state:
    if st.session_state.get("show_signup"):
        signup_page()
    else:
        login()
else:
    role = (st.session_state.role or "").strip().lower()
    if role == "child":
        child_dashboard()
    elif role == "parent":
        parent_dashboard()
    elif role == "admin":
        admin_dashboard()
    elif role == "pastor":
        pastor_dashboard()
    else:
        st.error(f"Unknown role: '{st.session_state.role}'. Contact admin.")

    if st.button("Logout"):
        theme_choice = st.session_state.get("theme_choice", "Light")
        st.session_state.clear()
        st.query_params.clear()
        st.session_state.theme_choice = theme_choice
        st.session_state.logged_out = True
        st.rerun()
