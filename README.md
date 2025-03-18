# Unprofitable NDIS Registered Provider Charity Web Scraping and Analysis Bot

## 📌 Overview

This project automates the detection of **unprofitable NDIS-registered charities** (those operating with a **Net Surplus ≤ 4%** of total revenue). 
Using **web scraping, data processing, and financial analysis**, this bot extracts charity data from the **ACNC** website, processes financial records, and generates **interactive reports**.

Once the charities have been identified, **automated reports** are generated detailing their financial performance and organizational details. 
An **interactive summary report** (`financial_reports.html`) is also created, allowing users to **filter, sort, and search** the identified charities.

📖 **Before using the web scraping bot, please read** [`instructions.pdf`](https://drive.google.com/file/d/1FUPx-QUphl2cA_0t0UpSFWScgg1ubVGX/view?usp=sharing) **for steps and potential issues.**

---

## 📂 Repository Structure

```
📂 Project Files:
├── 📜 bot.py  → Web scraping script for collecting charity financial data
├── 📜 generate_results.py  → Processes scraped data and generates reports
├── 📜 requirements.txt  → Required Python libraries
├── 📄 instructions.pdf  → Step-by-step guide for setup & troubleshooting
├── 📂 dist/  → Compressed package for running scripts without Python
│   ├── 🖥️ run_script.exe  → Executable file for automation
│   ├── 📜 All necessary files (bot.py, generate_results.py, etc.)
├── 📂 results/  → Example output data
│   ├── 📜 financial_reports.html  → Interactive summary report
│   ├── 📊 NDIS_CHARITIES.csv  → Full dataset (120+ rows)
│   ├── 📊 NDIS_CHARITIES_UNPROFITABLE_CONDENSED.csv  → Filtered unprofitable charities (15+ rows)
│   ├── 📂 charity_reports/  → Auto-generated individual reports
│   │   ├── 📜 [CharityName].html  → Individual charity reports
```

---

## ⚡ **Main Features**

### 🔍 **bot.py** (Web Scraping & Data Collection)
- 🕵 **Automated Web Scraping** → Uses **Selenium** to extract charity financial data.
- 📂 **Annual Information Statement (AIS) Extraction** → Collects due dates, financial reports, and revenue details.
- 🚀 **Parallelized Performance** → Multi-threaded web scraping for faster execution.
- 🌍 **Geolocation Mapping** → Uses **OpenCage API** to fetch latitude/longitude of charities.
- 🛠 **Supabase Database Integration** → Fetches and updates **NDIS charity records**.

### 📊 **generate_results.py** (Data Processing & Report Generation)
- 🔄 **Data Cleaning & Analysis** → Processes revenue, expenses, and surplus calculations.
- 📈 **Financial Visualization** → Uses **Plotly** to generate **interactive pie charts**.
- 📍 **Location-Based Insights** → Generates an **interactive map** for each charity.
- 📝 **Automated Report Generation** → Converts financial data into **interactive HTML reports**.
- 📂 **Export Results** → Saves data in:
  - `NDIS_CHARITIES.csv` → Full dataset
  - `NDIS_CHARITIES_UNPROFITABLE_CONDENSED.csv` → Only unprofitable charities

---

## 🛠 **Dependencies**
Libraries required to run the `.py` files are listed in `requirements.txt` and include:
```
pandas
supabase
markdown
plotly
beautifulsoup4
tqdm
folium
geopy
selenium
webdriver-manager
opencage
glob2
```
