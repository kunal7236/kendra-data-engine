import requests
import csv
import sqlite3
import os
import time
from token_manager import fetch_janaushadhi_token

from requests.exceptions import ChunkedEncodingError

# --- CONFIG ---
API_URL = "https://janaushadhi.gov.in:8443/api/v1/website/getAllKendraByStateDistrict"
CSV_FILE = "data/kendra_data.csv"
DB_FILE = "data/kendra.db"
PAGE_SIZE = 1000

def safe_float(val):
    """Safely convert coordinate strings to floats, handling nulls."""
    if val in (None, "", "null"):
        return None
    try:
        return float(val)
    except ValueError:
        return None

def main():
    start_time = time.time()
    try:
        print("🚀 Fetching Kendra data...")
        token = fetch_janaushadhi_token()
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://janaushadhi.gov.in",
            "Referer": "https://janaushadhi.gov.in/locate-kendra"
        }
        
        extracted_data = []
        page_index = 0
        total_pages = None

        while True:
            payload = {
                "pageIndex": page_index,
                "pageSize": PAGE_SIZE,
                "stateId": 0,
                "districtId": 0,
                "pinCode": 0,
                "storeCode": ""
            }

            for attempt in range(3):
                try:
                    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
                    response.raise_for_status()
                    json_data = response.json()
                    break
                except ChunkedEncodingError:
                    if attempt == 2:
                        raise
                    print(f"⚠️ Retrying page {page_index + 1} after a broken transfer...")

            response_body = json_data.get("responseBody", {})
            kendra_list = response_body.get("addKendraResponseList", [])

            if total_pages is None:
                total_pages = response_body.get("totalPages")

            if not kendra_list:
                if page_index == 0:
                    print("⚠️ No data found in the response.")
                    return False, 0, 0
                break

            print(f"📄 Parsing page {page_index + 1}{f'/{total_pages}' if total_pages else ''} with {len(kendra_list)} records...")

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

            if response_body.get("isLastPage"):
                break

            page_index += 1

        # Save to CSV
        headers_csv = ["Kendra_Code", "Contact_Person", "Contact_Number", "State_Name", "District_Name", "Pin_Code", "Address", "Latitude", "Longitude"]
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers_csv)
            writer.writerows(extracted_data)

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

        # 2. BUILD SQLITE DB
        print("📦 Building SQLite DB...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS kendras")

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
        cursor.execute("CREATE INDEX idx_pincode ON kendras(pin_code)")
        cursor.execute("CREATE INDEX idx_state_district ON kendras(state_name, district_name)")
        
        conn.commit()
        conn.close()

        duration = round(time.time() - start_time, 2)
        print(f"✅ Successfully processed {len(extracted_data)} records in {duration}s.")
        return True, len(extracted_data), duration

    except Exception as e:
        print(f"❌ Error: {e}")
        return False, 0, 0

if __name__ == "__main__":
    success, count, duration = main()
    # Output for GitHub Actions to pick up
    print(f"RESULT_SUCCESS={success}")
    print(f"RESULT_COUNT={count}")
    print(f"RESULT_DURATION={duration}s")