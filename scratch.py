import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    print("Categories:", supabase.table("categories").select("*").limit(1).execute().data)
except Exception as e:
    print("Categories error:", e)

try:
    print("Locations:", supabase.table("locations").select("*").limit(1).execute().data)
except Exception as e:
    print("Locations error:", e)

try:
    print("Depreciation:", supabase.table("depreciation_rates").select("*").limit(1).execute().data)
except Exception as e:
    print("Depreciation error:", e)
