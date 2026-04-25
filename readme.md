# ⚙️ JanAushadhi Data Engine

This repository is an automated data pipeline designed to fetch, parse, and structure official JanAushadhi pharmaceutical data. It functions as a "headless" engine that provides updated datasets for external APIs and local servers.

## 🎯 Purpose
The engine automates the collection of critical healthcare data from government portals, eliminating the need for manual PDF downloads. It tracks two primary datasets:

1.  **Kendra Locations:** A comprehensive directory of JanAushadhi stores across India, including addresses, district data, pincodes, and contact information.
2.  **Product Portfolio:** The full list of generic medicines, including drug codes, unit sizes, and current Maximum Retail Prices (MRP).

## 🛠️ How it Works
The engine is powered by a scheduled **GitHub Actions** workflow that executes a full synchronization every Sunday.

![JanAushadhi Data Engine Architecture Diagram](./kendra-data-engine-architecture.png)

### The Pipeline:
* **Extraction:** The engine authenticates with the official API to retrieve data as a raw binary PDF stream, processed entirely in-memory.
* **Parsing:** Using `pdfplumber`, the engine applies specialized coordinate-tracking (Line-based and Text-Gutter strategies) to convert complex PDF tables into structured data.
* **Storage:** * Generates **CSV** files for portability and easy tracking of weekly changes.
    * Builds optimized **SQLite (.db)** databases with pre-configured indexes to support high-speed searches on low-power hardware like a Raspberry Pi.
* **Sync & Notify:** Updated files are committed back to the repository. A synchronization report—including row counts, success status, and processing duration—is sent instantly via a **Telegram Bot**.

## 📊 Data Outputs
After every successful run, the following files in the `/data` directory are updated:

* `kendra.db` / `janaushadhi_data.csv`: Store location data.
* `products.db` / `product_data.csv`: Medicine pricing and drug code data.

These files serve as the "Single Source of Truth" for any frontend application or API consuming JanAushadhi data.