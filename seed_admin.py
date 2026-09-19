"""
Run this ONCE after setting up your Supabase tables
to create the admin account with a properly hashed password.

Usage:
  python seed_admin.py
"""
from werkzeug.security import generate_password_hash
from supabase import create_client

# ── Paste your credentials here ──────────────────────
SUPABASE_URL = "https://xndvlkiyguwzwnuiolza.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhuZHZsa2l5Z3V3endudWlvbHphIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk4MzcyMzgsImV4cCI6MjEwNTQxMzIzOH0.Myi9qyS1WTOCnwA6ZdFfenDMqC10Hb8nIBRD0u96VM4"
# ─────────────────────────────────────────────────────

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

hashed = generate_password_hash('admin123')

# Remove the placeholder admin row from SQL schema first
supabase.table('users').delete().eq('email', 'admin@advisor.com').execute()

# Insert with proper hash
supabase.table('users').insert({
    'name':       'Admin',
    'email':      'admin@advisor.com',
    'username':   'admin',
    'password':   hashed,
    'is_admin':   True,
    'mobile':     '',
    'qualification': '',
    'age':        25,
    'income':     0,
    'savings':    0,
    'expenses':   0,
    'investments': 0,
}).execute()

print("✅ Admin user created successfully!")
print("   Email:    admin@advisor.com")
print("   Password: admin123")
print("   Login at: http://localhost:5000/login")
