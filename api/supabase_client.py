import os
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_init import supabase
except ImportError as e:
    print(f"Supabase init error: {e}")
    supabase = None
