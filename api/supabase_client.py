import os
from supabase import create_client
from health import log_error

try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")

    supabase = create_client(supabase_url, supabase_key)
    
except Exception as e:
    log_error("supabase_client", e, "", "Failed to initialize Supabase client")
    raise
