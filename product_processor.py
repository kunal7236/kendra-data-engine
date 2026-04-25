import requests
import pdfplumber
import csv
import io
import sqlite3
import os
import time

# --- CONFIG ---
TOKEN = os.getenv("JANAUSHADHI_TOKEN")
API_URL = "https://janaushadhi.gov.in:8443/api/v1/admin/pdf/productPdfDownload"
CSV_FILE = "data/product_data.csv"
DB_FILE = "data/products.db"

def main():
    start_time = time.time()
    try:
        print("🚀 Fetching Product Portfolio...")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "pageIndex": 0,
            "pageSize": 1000000,
            "searchText": "",
            "orderBy": "asc",
            "columnName": "drug_code"
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)

        print("📄 Parsing Product PDF...")
        extracted_data = []
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                # Using the successful 'lines' strategy
                table = page.extract_table(table_settings={
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "lines"
                })
                
                # Fallback to default if line detection is patchy on certain pages
                if not table:
                    table = page.extract_table()

                if table:
                    for row in table:
                        # Validation: Sr.No, Drug Code, Generic Name, Unit Size, MRP (5 columns)
                        # Ensure Sr.No is a digit to skip headers/extra text
                        if row and len(row) >= 5:
                            sr_no = str(row[0]).strip()
                            if sr_no.isdigit():
                                # Clean row and limit to first 5 columns
                                clean_row = [str(col).strip().replace('\n', ' ') if col else "" for col in row[:5]]
                                extracted_data.append(clean_row)
                
                # Memory management for large PDFs
                if i % 100 == 0:
                    print(f"   Processed {i}/{total_pages} pages...")
                    page.flush_cache()

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