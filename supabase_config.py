import requests

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
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        params=params
    )
    if res.status_code != 200:
        print(f"SELECT ERROR on {table}: {res.status_code} {res.text}")
        return []
    return res.json()

def db_insert(table, data):
    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        json=data
    )
    if res.status_code not in [200, 201]:
        print(f"INSERT ERROR on {table}: {res.status_code} {res.text}")
        return None
    return res.json()

def db_update(table, match_field, match_value, data):
    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}?{match_field}=eq.{match_value}",
        headers=HEADERS,
        json=data
    )
    if res.status_code not in [200, 204]:
        print(f"UPDATE ERROR on {table}: {res.status_code} {res.text}")
        return None
    return res.json()
