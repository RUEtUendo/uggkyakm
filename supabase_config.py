import requests

SUPABASE_URL = "https://cnqwbgjfsbseispmzywc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNucXdiZ2pmc2JzZWlzcG16eXdjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMjQwNjQsImV4cCI6MjA5NTkwMDA2NH0.2_Gj-6z_Gewwb0ypCvVV4YislaYdOj3Mm8Y0d_317L8"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def db_select(table, filters=None):
    params = filters or {}
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        params=params
    )
    return res.json()

def db_insert(table, data):
    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        json=data
    )
    return res.json()