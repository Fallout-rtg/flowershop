import os
from supabase import create_client, Client

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

print(f"Supabase URL: {supabase_url}")
print(f"Supabase key present: {bool(supabase_key)}")

if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(supabase_url, supabase_key)
