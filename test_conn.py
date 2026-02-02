import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_DATABASE_URL")
print(f"Testing connection to: {url.split('@')[-1] if url else 'None'}")

try:
    with psycopg.connect(url) as conn:
        print("Connection successful!")
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database()")
            print(f"Logged in as: {cur.fetchone()}")
except Exception as e:
    print(f"Connection failed: {e}")
