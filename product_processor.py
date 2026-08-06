import requests
import csv
import sqlite3
import time
from token_manager import fetch_janaushadhi_token

# --- CONFIG ---
API_URL = "https://janaushadhi.gov.in:8443/api/v1/website/getAllProductForWeb"
CSV_FILE = "data/product_data.csv"
DB_FILE = "data/products.db"

def main():
    start_time = time.time()
    try:
        print("🚀 Fetching Product Portfolio...")
        token = fetch_janaushadhi_token()
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "pageIndex": 0,
            "pageSize":  1000000,
            "searchText": "",
            "orderBy": "asc",
            "columnName": "drug_code"
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        product_list = response_data.get("responseBody", {}).get("newProductResponsesList", [])

        print("📄 Parsing Product JSON...")
        extracted_data = []
        for item in product_list:
            sr_no = item.get("serialNo") or item.get("productId")
            drug_code = item.get("drugCode", "")
            generic_name = item.get("genericName", "")
            unit_size = item.get("unitSize", "")
            mrp = item.get("mrp", 0)

            if sr_no is None or drug_code == "":
                continue

            extracted_data.append([
                int(sr_no),
                str(drug_code),
                str(generic_name).strip(),
                str(unit_size).strip(),
                mrp,
            ])

        # Save to CSV
        headers_csv = ["Sr.No", "Drug_Code", "Generic_Name", "Unit_Size", "MRP"]
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers_csv)
            writer.writerows(extracted_data)

        # Build SQLite DB
        print("📦 Building Products DB...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("""
            CREATE TABLE products (
                sr_no INTEGER, 
                drug_code TEXT PRIMARY KEY, 
                generic_name TEXT,
                unit_size TEXT, 
                mrp REAL
            )
        """)
        cursor.executemany("INSERT INTO products VALUES (?,?,?,?,?)", extracted_data)
        
        # Create Index for faster searching by drug name
        cursor.execute("CREATE INDEX idx_generic_name ON products(generic_name)")
        
        conn.commit()
        conn.close()

        duration = round(time.time() - start_time, 2)
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