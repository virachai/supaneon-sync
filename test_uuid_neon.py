import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

neon_url = os.environ.get("NEON_DATABASE_URL")
print("Testing UUID function in Neon...")

try:
    with psycopg.connect(neon_url) as conn:
        with conn.cursor() as cur:
            # Test 1: Check if extension exists
            cur.execute("""
                SELECT extname, nspname
                FROM pg_extension e
                JOIN pg_namespace n ON e.extnamespace = n.oid
                WHERE extname = 'uuid-ossp'
            """)
            ext_result = cur.fetchone()
            if ext_result:
                print(f"✓ Extension 'uuid-ossp' found in schema: {ext_result[1]}")
            else:
                print("✗ Extension 'uuid-ossp' NOT found")

            # Test 2: Check if function exists and in what schema
            cur.execute("""
                SELECT n.nspname, p.proname
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE p.proname = 'uuid_generate_v4'
            """)
            func_result = cur.fetchone()
            if func_result:
                print(
                    f"✓ Function 'uuid_generate_v4' found in schema: {func_result[0]}"
                )
            else:
                print("✗ Function 'uuid_generate_v4' NOT found")

            # Test 3: Try calling the function with different search paths
            print("\nTest 3: Calling function with default search_path:")
            try:
                cur.execute("SELECT uuid_generate_v4()")
                print(f"✓ Success: {cur.fetchone()[0]}")
            except Exception as e:
                print(f"✗ Failed: {e}")

            print("\nTest 4: Calling function with explicit public schema:")
            try:
                cur.execute("SELECT public.uuid_generate_v4()")
                print(f"✓ Success: {cur.fetchone()[0]}")
            except Exception as e:
                print(f"✗ Failed: {e}")

            # Test 5: Check current search_path
            cur.execute("SHOW search_path")
            print(f"\nCurrent search_path: {cur.fetchone()[0]}")

except Exception as e:
    print(f"Connection or query failed: {e}")
