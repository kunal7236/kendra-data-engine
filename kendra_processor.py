import requests
import pdfplumber
import csv
import io
import sqlite3
import os
import time
import re

# --- CONFIG ---
TOKEN = os.getenv("JANAUSHADHI_TOKEN") # Securely loaded from GitHub Secrets
API_URL = "https://janaushadhi.gov.in:8443/api/v1/admin/pdf/KendraPdfDownload"
CSV_FILE = "data/janaushadhi_data.csv"
DB_FILE = "data/kendra.db"

def main():
    start_time = time.time()
    try:
        print("🚀 Fetching data...")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"pageIndex": 0, "pageSize": 1000000, "stateId": 0, "districtId": 0, "pinCode": 0, "storeCode": ""}
        
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)

        # 1. SCRAPE TO CSV
        print("📄 Parsing PDF...")
        extracted_data = []
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                table = page.extract_table(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                if not table: table = page.extract_table()
                if table:
                    for row in table:
                        if row and len(row) >= 7 and str(row[0]).strip().isdigit():
                            clean_row = [str(col).strip().replace('\n', ' ') if col else "" for col in row[:7]]
                            extracted_data.append(clean_row)
                if i % 100 == 0: page.flush_cache()

        # Save to CSV
        headers_csv = ["Sr.No", "Kendra Code", "Name", "State", "District", "Pin", "Address"]
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers_csv)
            writer.writerows(extracted_data)

        # 2. BUILD SQLITE DB
        print("📦 Building DB...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS kendras")
        cursor.execute("""
            CREATE TABLE kendras (
                sr_no INTEGER, kendra_code TEXT PRIMARY KEY, name TEXT,
                state_name TEXT, district_name TEXT, pin_code TEXT, address TEXT
            )
        """)
        cursor.executemany("INSERT INTO kendras VALUES (?,?,?,?,?,?,?)", extracted_data)
        cursor.execute("CREATE INDEX idx_pincode ON kendras(pin_code)")
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