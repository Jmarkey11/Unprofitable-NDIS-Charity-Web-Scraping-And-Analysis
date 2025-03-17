import numpy as np
import pandas as pd
import os
import warnings
import multiprocessing
import time
import glob
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from supabase import create_client, Client
from datetime import datetime
from opencage.geocoder import OpenCageGeocode
import concurrent.futures
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from collections import Counter

### -------------------- Charity Bot: Automated Charity URL Scraping -------------------- ###

def scrape_charity_data(abn, driver):
    data = {"ABN": abn, "Profile URL": None, "AIS Year": None, "Due Date": None, "Date Received": None, 
            "View AIS": None, "Non_Reporting": True, "Financial Report URL": None}
    
    # Financial data placeholders
    financial_data = {
        "Revenue from government including grants": None,
        "Donations and bequests": None,
        "Revenue from providing goods or services": None,
        "Revenue from investments": None,
        "All other revenue": None,
        "Total revenue": None,
        "Other income (for example, gains)": None,
        "Total gross income": None,
        "Employee expenses": None,
        "Interest expenses": None,
        "Grants and donations made for use in Australia": None,
        "Grants and donations made for use outside Australia": None,
        "All other expenses": None,
        "Total expenses": None,
        "Net surplus/(deficit)": None,
        "Other comprehensive income": None,
        "Total comprehensive income": None,
        "Total current assets": None,
        "Non-current loans receivable": None,
        "Other non-current assets": None,
        "Total non-current assets": None,
        "Total assets": None,
        "Total current liabilities": None,
        "Non-current loans payable": None,
        "Other non-current liabilities": None,
        "Total non-current liabilities": None,
        "Total liabilities": None,
        "Net assets/liabilities": None
    }

    ### Step 1: Scrape Profile URL ###
    try:
        driver.get("https://www.acnc.gov.au/charity/charities")

        search_box = WebDriverWait(driver, 2, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search charity name or ABN']"))
        )
        search_box.clear()
        search_box.send_keys(abn)
        search_box.send_keys(Keys.RETURN)

        first_result = WebDriverWait(driver, 2, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/charity/charities/') and contains(@href, '/profile')]"))
        )

        relative_url = first_result.get_attribute("href")
        profile_url = f"https://www.acnc.gov.au{relative_url}" if relative_url.startswith("/") else relative_url
        data["Profile URL"] = profile_url
    except TimeoutException:
        # Return data only containing ABN if profile URL is not found, None for all other fields
        final_data = {**data, **financial_data}
        return final_data
        

    ### Step 2: Scrape AIS Data ###
    if data["Profile URL"]:
        financial_url = data["Profile URL"].replace("/profile", "/documents")
        driver.get(financial_url)

        try:
            rows = WebDriverWait(driver, 2, poll_frequency=0.2).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tbody/tr"))
            )

            for row in rows:
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) < 4:
                    continue

                title = columns[0].text.strip()
                due_date_text = columns[1].text.strip()
                date_received_text = columns[2].text.strip()
                ais_url = None

                if "Annual Information Statement" in title:
                    year = title.split()[-1]

                    # Ignore if it's a future AIS entry
                    if "Not yet submitted" in date_received_text or "Pending" in date_received_text or "Overdue" in date_received_text:
                        continue
                    
                    # Stop searching if AIS is "Not required"
                    if "Not required" in date_received_text:
                        break  

                    # Get the AIS link if available
                    if columns[3].find_elements(By.TAG_NAME, "a"):
                        ais_url = columns[3].find_element(By.TAG_NAME, "a").get_attribute("href")

                    # Store data and stop loop once a valid AIS is found
                    data.update({"AIS Year": year, "Due Date": due_date_text, "Date Received": date_received_text,
                                 "View AIS": ais_url, "Non_Reporting": False})
                    
                    # Find Financial Report URL for the same year
                    for sub_row in rows:
                        sub_columns = sub_row.find_elements(By.TAG_NAME, "td")
                        if len(sub_columns) < 4:
                            continue

                        if f"Financial Report {year}" in sub_columns[0].text.strip():
                            financial_link = sub_columns[3].find_elements(By.TAG_NAME, "a")
                            if financial_link:
                                data["Financial Report URL"] = financial_link[0].get_attribute("href")
                            break

                    break  # Stop once the most recent valid AIS is found

        except TimeoutException:
            # Returns ABN and profile URL if no AIS are found, None for all other fields
            final_data = {**data, **financial_data}
            return final_data

    ### Step 3: Scrape Financial Data ###
    if data["View AIS"]:
        driver.get(data["View AIS"])

        try:
            tables = WebDriverWait(driver, 2, poll_frequency=0.2).until(
                EC.presence_of_all_elements_located((By.XPATH, "//h3[contains(text(), 'Income and Expenses')]/following::table"))
            )

            for table in tables:
                rows = table.find_elements(By.XPATH, ".//tr")
                for row in rows:
                    columns = row.find_elements(By.XPATH, "./td")
                    if len(columns) == 2:
                        label, value = columns[0].text.strip(), columns[1].text.strip()

                        for item in financial_data.keys():
                            if item.lower() in label.lower():
                                financial_data[item] = value

        except TimeoutException:
            # Returns ABN, profile URL, AIS data if no financial data is found. None for financial data fields
            final_data = {**data, **financial_data}
            return final_data

    # Combine data and return all found results
    final_data = {**data, **financial_data}
    return final_data

def scrape_abn_chunk(abn_list, return_list):
    """
    Wrapper function to scrape multiple ABNs in a single process.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Run in headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.page_load_strategy = "eager"
    options.add_argument("--log-level=3")  # Suppress logs

    try:
        # Corrected WebDriver initialization
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return None  # ❌ Return None if WebDriver fails to start
    
    try:
        for abn in abn_list:
            data = scrape_charity_data(abn, driver)
            return_list.append(data)  # Append result to shared list
    finally:
        driver.quit()
        
def run_parallel_scraping(num_processes, abn_list):
    """Runs web scraping in parallel with one WebDriver per process."""
    chunk_size = max(1, len(abn_list) // num_processes)
    manager = multiprocessing.Manager()
    results_list = manager.list()
    processes = []

    for i in range(num_processes):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i != num_processes - 1 else len(abn_list)
        process_abns = abn_list[start:end]

        p = multiprocessing.Process(target=scrape_abn_chunk, args=(process_abns, results_list))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    return pd.DataFrame(list(results_list))

if __name__ == "__main__":
    csv_files = glob.glob("Reg_Prvdrs*.csv")

    if not csv_files:
        print(f"No NDIS file found. Download latest file at: \n\thttps://www.ndis.gov.au/participants/working-providers/find-registered-provider/provider-finder\n and add to current folder at: {os.getcwd()}. \n Refer to instructions.pdf for more details.")
        sys.exit(1)
        
    SUPABASE_URL = "https://crhttqspythjsggyjksi.supabase.co"
    # admin key - may need to change to read only key and change permissions
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyaHR0cXNweXRoanNnZ3lqa3NpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MTU4NjgxOCwiZXhwIjoyMDU3MTYyODE4fQ.dVnlhmfvaSpe7IjXS_FyBw_YbhCwVx_rjeBAn8wsVyc"

    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    start_time = time.time()
    warnings.filterwarnings("ignore")

    print("Charity Bot: Automated Charity Data Scraping".encode("utf-8", "ignore").decode("utf-8"))

    ### **Step 1: Fetch entire Supabase dataset and convert to DataFrame** ###
    print("Fetching complete NDIS_CHARITIES dataset from Supabase...")

    page_size = 1000
    start = 0
    all_records = []

    try:
        while True:
            response = supabase.table("NDIS_CHARITIES").select("*").range(start, start + page_size - 1).execute()

            if response.data:
                all_records.extend(response.data)  # Append all fetched records
                print(f"Fetched {len(response.data)} records (Total: {len(all_records)})")

                if len(response.data) < page_size:
                    break  # Exit loop if there are no more records

                start += page_size
            else:
                print("No records found in the database.")
                break

    except Exception as e:
        print(f"Failed to fetch data from Supabase: {e}")
        sys.exit(1)

    # Convert fetched data to a DataFrame
    sb_df = pd.DataFrame(all_records)

    key_info = sb_df[["ABN", "AIS Year", "Non_Reporting"]].copy()

    ### **Step 2: Load ACNC and NDIS Data** ###
    print("Loading data from ACNC Charity Database API...")

    try:
        ACNC_data = pd.read_csv(
            "https://data.gov.au/data/dataset/b050b242-4487-4306-abf5-07ca073e5594/resource/8fb32972-24e9-4c95-885e-7140be51be8a/download/datadotgov_main.csv",
            low_memory=False
        )
    except Exception as e:
        print(f"Failed to load ACNC data: {e}")
        sys.exit(1)

    ACNC_data['ABN'] = ACNC_data['ABN'].astype(str).replace(r'\.0$', '', regex=True)

    print("Loading NDIS Provider Data...")
    csv_files = glob.glob("Reg_Prvdrs*.csv")

    if not csv_files:
        print(f"Download the latest NDIS Registered Providers List CSV file and add it to the current folder at: {os.getcwd()}.")
        sys.exit(1)

    NDIS_file = csv_files[0]
    print(f"Using NDIS file: {NDIS_file}")
    NDIS_data = pd.read_csv(NDIS_file, low_memory=False)
    NDIS_data['ABN'] = NDIS_data['ABN'].astype(str).replace(r'\.0$', '', regex=True)

    ### **Step 3: Merge ACNC and NDIS datasets** ###
    merged_dataset = pd.merge(ACNC_data, NDIS_data, on='ABN').drop_duplicates(subset='ABN')

    ### **Step 4: Filter ABNs based on database check** ###
    key_info["AIS Year"] = key_info["AIS Year"].fillna(-1)  # Replace NaNs in AIS Year
    key_info["Non_Reporting"] = key_info["Non_Reporting"].fillna(False)  # Replace NaNs in Non_Reporting
    key_info["ABN"] = key_info["ABN"].astype(str)  # Ensure ABN is a string
    merged_dataset["ABN"] = merged_dataset["ABN"].astype(str)

    # Get ABNs from merged_dataset that are NOT in key_info
    abn_list = merged_dataset.loc[~merged_dataset["ABN"].isin(key_info["ABN"]), "ABN"].tolist()
    print(len(abn_list))  # Debugging step

    # Extend abn_list by adding ABNs from key_info where AIS Year != 2025 or 2024 and Non_Reporting is False
    filtered_abns = key_info.loc[
        (key_info["AIS Year"] != 2025.0) & 
        (key_info["AIS Year"] != 2024.0) & 
        (~key_info["Non_Reporting"]), 
        "ABN"
    ]

    abn_list.extend(filtered_abns.tolist())
    print(len(abn_list))  # Debugging step

    # Filter merged_dataset to only include rows that match abn_list
    new_data = merged_dataset[merged_dataset['ABN'].isin(abn_list)].drop_duplicates(subset='ABN')

    print(f"{len(new_data)} ABNs need to be added or updated in the database.")
    if new_data.empty:
        print("No new ABNs to process. Exiting.")
        sys.exit(0)

    new_data["Execution_Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    ### TESTING DATASET FIRST 100 ROWS
    #new_data = new_data[:100]

    ### **Step 5: Extract ABNs for Scraping** ###
    abn_list = new_data['ABN'].tolist()
    print(f"\nTotal ABNs to process: {len(abn_list)}")
    print(f"Estimated time to complete: {len(abn_list) * 6 / 10:.2f} seconds. Do not close the Terminal.")
    print("Proceeding to scrape the ACNC website for charity URLs...\n")
    
    ### **Step 6: Run Parallel Web Scraping** ###
    n_parallels = 10
    scraped_results = run_parallel_scraping(n_parallels, abn_list)

    ### **Step 7: Merge Results** ###
    if scraped_results is not None and not scraped_results.empty:
        new_data = new_data.merge(scraped_results, on="ABN", how="left").drop_duplicates(subset="ABN")
        print(f"Total URLs scraped: {new_data['Profile URL'].count()}")
    else:
        print("Scraping completed, but no data was collected.")
        sys.exit(1)

    time.sleep(1)
    
    # ✅ OpenCage API Setup
    API_KEY = "93c6afe378bd450ba882ce76d70dca4a"
    geocoder = OpenCageGeocode(API_KEY)

    # ✅ Function to Fetch Latitude/Longitude (Returns as Text)
    def get_lat_lon_opencage(address):
        """Fetch latitude and longitude using OpenCage API, returning as text."""
        try:
            result = geocoder.geocode(address)
            if result:
                lat = str(result[0]["geometry"]["lat"])  # Convert to string
                lon = str(result[0]["geometry"]["lng"])  # Convert to string
                return lat, lon
        except Exception as e:
            print(f"Error geocoding {address}: {e}")
        
        return "None", "None"  # Return as string if not found

    # ✅ Function to Run Batch Geocoding with 10 Workers
    def batch_geocode_addresses(addresses, workers=10):
        """Geocode addresses in parallel using OpenCage API, returning results as strings."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(get_lat_lon_opencage, addresses))  # ✅ Fixed list() usage
        
        latitudes, longitudes = zip(*results)  # ✅ Unpack results correctly
        return latitudes, longitudes

    ### **Step 7.1: Add Geocoding Process**
    addresses = new_data["Address"].tolist()
    latitudes, longitudes = batch_geocode_addresses(addresses, workers=10)
    
    new_data["Latitude"] = latitudes
    new_data["Longitude"] = longitudes

    ### **Step 8: Save Data Locally** ###
    new_data['ABN'] = new_data['ABN'].astype("Int64")
    data = pd.concat([new_data, sb_df]).drop_duplicates(subset="ABN", keep="first")
    # Save the final dataset
    output_file = "NDIS_CHARITIES.csv"
    data.to_csv(output_file, index=False, mode='w')

    ### **Step 9: Update Supabase Database** ###
    print("Uploading data to Supabase...")
    
    def update_supabase_table(new_data, supabase):
        """Uploads the new dataset to Supabase, ensuring it matches the existing schema."""
        new_data = new_data.where(pd.notna(new_data), None)
        data_to_upload = new_data.to_dict(orient="records")

        if not data_to_upload:
            print("No new data to upload. Exiting update process.")
            return

        batch_size = 100
        for i in range(0, len(data_to_upload), batch_size):
            batch = data_to_upload[i:i + batch_size]
            try:
                response = supabase.table("NDIS_CHARITIES").upsert(batch).execute()
                if response.data:
                    print(f"Successfully uploaded batch {i + 1} to {i + batch_size}")
                else:
                    print(f"No data was inserted/updated in batch {i + 1} to {i + batch_size}")
            except Exception as e:
                print(f"Error uploading batch {i + 1} to {i + batch_size}: {e}")

        print(f"Data upload completed. {len(data_to_upload)} records added to the database.")

    update_supabase_table(new_data, supabase)

    end_time = time.time()
    print(f"\nTotal runtime: {end_time - start_time:.2f} seconds.\n")