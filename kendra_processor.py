import requests
import sqlite3
import os
import time
from token_manager import fetch_janaushadhi_token #[cite: 1]

# --- CONFIG ---
API_URL = "https://janaushadhi.gov.in:8443/api/v1/admin/addKendra/getAllKendraByStateDistrict"
DB_FILE = "data/kendra.db" #[cite: 1]

def safe_float(val):
    """Safely convert coordinate strings to floats, handling nulls."""
    if val in (None, "", "null"):
        return None
    try:
        return float(val)
    except ValueError:
        return None

def main():
    start_time = time.time() #[cite: 1]
    try:
        print("🚀 Fetching Kendra data via JSON API...")
        token = fetch_janaushadhi_token() #[cite: 1]
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://janaushadhi.gov.in",
            "Referer": "https://janaushadhi.gov.in/locate-kendra"
        }
        
        payload = {
            "pageIndex": 0, 
            "pageSize": 25000, 
            "stateId": 0, 
            "districtId": 0, 
            "pinCode": 0, 
            "storeCode": ""
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() #[cite: 1]
        json_data = response.json()

        kendra_list = json_data.get("responseBody", {}).get("addKendraResponseList", [])
        
        if not kendra_list:
            print("⚠️ No data found in the response.")
            return False, 0, 0

        print(f"📄 Parsing {len(kendra_list)} records...")
        
        extracted_data = []
        for k in kendra_list:
            extracted_data.append((
                k.get("storeCode"),
                k.get("contactPerson"),
                str(k.get("contactNumber")) if k.get("contactNumber") else None,
                k.get("stateName"),
                k.get("districtName"),
                str(k.get("pinCode")) if k.get("pinCode") else None,
                k.get("kendraAddress"),
                safe_float(k.get("latitude")),
                safe_float(k.get("longitude"))
            ))

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

        # 2. BUILD SQLITE DB
        print("📦 Building SQLite DB...")
        conn = sqlite3.connect(DB_FILE) #[cite: 1]
        cursor = conn.cursor() #[cite: 1]
        
        cursor.execute("DROP TABLE IF EXISTS kendras") #[cite: 1]
        
        # Create flat table schema
        cursor.execute("""
            CREATE TABLE kendras (
                kendra_code TEXT PRIMARY KEY,
                contact_person TEXT,
                contact_number TEXT,
                state_name TEXT,
                district_name TEXT,
                pin_code TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL
            )
        """)
        
        # Insert all records
        cursor.executemany(
            "INSERT OR REPLACE INTO kendras VALUES (?,?,?,?,?,?,?,?,?)", 
            extracted_data
        )
        
        # Create Indexes for API performance
        print("⚡ Generating search indexes...")
        cursor.execute("CREATE INDEX idx_pincode ON kendras(pin_code)") #[cite: 1]
        cursor.execute("CREATE INDEX idx_state_district ON kendras(state_name, district_name)")
        
        conn.commit() #[cite: 1]
        conn.close() #[cite: 1]

        duration = round(time.time() - start_time, 2) #[cite: 1]
        print(f"✅ Successfully processed {len(extracted_data)} records in {duration}s.")
        return True, len(extracted_data), duration

    except Exception as e:
        print(f"❌ Error: {e}") #[cite: 1]
        return False, 0, 0 #[cite: 1]

if __name__ == "__main__":
    success, count, duration = main() #[cite: 1]
    # Output for GitHub Actions to pick up
    print(f"RESULT_SUCCESS={success}") #[cite: 1]
    print(f"RESULT_COUNT={count}") #[cite: 1]
    print(f"RESULT_DURATION={duration}s") #[cite: 1]