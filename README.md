# UGGK Bible App 📖

A mobile-friendly children's Bible app built with Streamlit and Supabase. Designed for children to engage with Bible content through quizzes, voice notes, and image uploads — with full parent visibility and admin control.

---

## About The App

The UGGK Bible App is a three-tier web application that allows:

- **Children** to log in, upload voice notes and images, and participate in Bible quizzes
- **Parents** to monitor their child or children's activity and submissions in read-only mode
- **Admins** to manage all accounts, post Bible verses, mark quizzes, and post announcements

Built as a live deployable model within a 10-day sprint.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Database | Supabase (PostgreSQL) |
| Authentication | Supabase Auth |
| File Storage | Supabase Storage |
| Hosting | Streamlit Community Cloud |
| Version Control | GitHub |

---

## Features

### Children's Tier
- Secure login with email and password
- Personal dashboard with welcome message
- Upload voice notes (locked behind login)
- Upload images (locked behind login)
- Participate in Bible quizzes

### Parent Tier
- Secure login
- View linked child or children's profiles
- Read-only access to submissions and quiz results
- No ability to edit or upload

### Admin Tier
- Full dashboard overview
- Post and update Bible verses
- Create and mark quizzes
- Post announcements
- View all children's activity

---

## Project Structure

```
UGGK BIBLE APP/
├── app.py                  ← Main entry point and role router
├── supabase_config.py      ← Database connection (not committed to GitHub)
├── auth/
│   ├── __init__.py
│   └── login.py            ← Shared login page
├── tiers/
│   ├── __init__.py
│   ├── child.py            ← Children's dashboard
│   ├── parent.py           ← Parent dashboard
│   └── admin.py            ← Admin control panel
└── requirements.txt        ← Python dependencies
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| Profiles | Stores user name, role, and email |
| submissions | Stores child uploads and quiz answers |
| content | Stores Bible verses, quizzes, and announcements |

---

## Getting Started (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/RUEtUendo/uggkyakm.git
cd uggkyakm
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Add Your Supabase Credentials
Create a file called `supabase_config.py` in the root folder:
```python
import requests

SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-anon-key"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}
```

### 5. Run the App
```bash
streamlit run app.py
```

---

## Deployment

The app is deployed via Streamlit Community Cloud connected to this GitHub repository. Any push to the `main` branch automatically updates the live app.

Live URL: https://uggkyakm-sipgc5xs3vhucmefqkndo6.streamlit.app/?uid=3fb9197c-2ca8-4cb9-b9f7-c989bead6ba8

---

## Security Notes

- `supabase_config.py` is excluded from GitHub via `.gitignore`
- Row Level Security (RLS) will be enabled before final production deployment
- All file uploads are authenticated — only logged-in children can upload

---


## Author

RUEtUendo  
Built with guidance and support throughout the 10-day sprint.
