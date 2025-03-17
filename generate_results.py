
import pandas as pd
import os
import sys
import datetime as dt
import time
import re
import warnings
from supabase import create_client, Client
import markdown
import plotly.graph_objects as go
import plotly.io as pio
from bs4 import BeautifulSoup
from tqdm import tqdm
import folium
from geopy.geocoders import Nominatim

## ----------------- Scripts for company financial htmls ----------------- ##
def generate_combined_plotly_pie_chart(income_data, expense_data, title):
    """Generate responsive inline Plotly pie charts for Income and Expenses, formatted for Markdown to HTML conversion."""

    # Remove zero values to avoid empty slices
    income_data = {k: v for k, v in income_data.items() if v > 0 and k not in ["Total revenue", "Total gross income"]}
    expense_data = {k: v for k, v in expense_data.items() if v > 0 and k not in ["Total expenses"]}
    
    # Create subplots for side-by-side pie charts
    fig = go.Figure()

    # Income Pie Chart
    fig.add_trace(go.Pie(
        labels=list(income_data.keys()),
        values=list(income_data.values()),
        name="Income",
        hole=0.3,
        domain={'x': [0, 0.49]},  # Adjust width
        title="Income"
    ))

    # Expense Pie Chart
    fig.add_trace(go.Pie(
        labels=list(expense_data.keys()),
        values=list(expense_data.values()),
        name="Expenses",
        hole=0.3,
        domain={'x': [0.51, 1]},  # Adjust width
        title="Expenses"
    ))

    # Layout adjustments
    fig.update_layout(
        autosize=True,
        height=500,  # Adjust height
        margin=dict(l=0, r=0, t=30, b=0),  # Remove margins
        title_text=None,
        showlegend=False,  # Keep legend for clarity
    )

    # Convert Plotly figure to an INLINE HTML string (full HTML block)
    plotly_html = pio.to_html(fig, full_html=True, include_plotlyjs='cdn')

    # Wrap it in a raw HTML block so Markdown processors treat it correctly
    markdown_compatible_html = f"""
<div style="width: 100%; text-align: center;">
{plotly_html}
</div>
"""

    return markdown_compatible_html

def format_table_html(df, bold_rows=None, underline_rows=None):
    """Convert DataFrame to a properly formatted HTML table with bold and underline formatting."""
    df_html = df.to_html(index=False, escape=False)

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(df_html, "html.parser")

    # Modify table styling
    table = soup.find("table")
    table["class"] = "styled-table"
    table["style"] = "width: 100%; border-collapse: collapse;"

    # Ensure headers are aligned properly
    headers = table.find_all("th")
    headers[0]["style"] = "text-align: left;"  # Category column left-align
    headers[1]["style"] = "text-align: right;"  # Amount column right-align

    # Modify all rows
    for row in table.find_all("tr")[1:]:  # Skip header row
        cells = row.find_all("td")
        if len(cells) == 2:
            category_cell = cells[0]  # First column
            amount_cell = cells[1]  # Second column

            category_cell["style"] = "text-align: left;"  # Left align
            amount_cell["style"] = "text-align: right;"  # Right align

            text_content = category_cell.text.strip()

            # Apply bold formatting
            if text_content in (bold_rows or []):
                strong_tag = soup.new_tag("strong")
                strong_tag.string = text_content
                category_cell.clear()
                category_cell.append(strong_tag)

            # Apply underline formatting
            if text_content in (underline_rows or []):
                category_cell["style"] += " border-bottom: 2px solid black;"

            # Apply bold & italic for section headers (empty amount column)
            if amount_cell.text.strip() == "":
                em_tag = soup.new_tag("em")
                strong_tag = soup.new_tag("strong")
                em_tag.string = text_content
                strong_tag.append(em_tag)
                category_cell.clear()
                category_cell.append(strong_tag)

    return str(soup)

def generate_map_html(lat, lon, address="Unknown Address", charity_name="Charity"):
    """Create an interactive map using latitude & longitude and return HTML as a string for embedding."""

    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        print(f"Invalid coordinates: {lat}, {lon}")
        return "<p>Invalid coordinates</p>"

    # ✅ Create a Folium map centered at the given coordinates
    map_object = folium.Map(location=[lat, lon], zoom_start=15)

    popup_content = f"<b>{charity_name}</b><br>{address}"
    folium.Marker([lat, lon], popup=popup_content, tooltip="Click for details").add_to(map_object)

    # ✅ Return Folium's built-in HTML representation
    return map_object._repr_html_()

def generate_charity_report(charity):
    charity_legal_name = charity['Charity_Legal_Name']
    abn = charity['ABN']
    address = charity['Address']
    acnc_website = charity['Profile URL']
    reporting_year = int(charity['AIS Year'])
    latest_report = charity['Financial Report URL']
    longitude = charity['Longitude']
    latitude = charity['Latitude']

    # Define financial data columns
    income_cols = [
        'Revenue from government including grants', 'Donations and bequests',
        'Revenue from providing goods or services', 'Revenue from investments',
        'All other revenue', 'Total revenue', 'Other income (for example, gains)', 
        'Total gross income'
    ]

    expense_cols = [
        'Employee expenses', 'Interest expenses', 
        'Grants and donations made for use in Australia',
        'Grants and donations made for use outside Australia',
        'All other expenses', 'Total expenses'
    ]

    balance_cols = [
        'Total current assets', 'Total non-current assets', 'Total assets',
        'Total current liabilities', 'Total non-current liabilities',
        'Total liabilities', 'Net assets/liabilities'
    ]
    
    charity_type_cols = [ 'Preventing_or_relieving_suffering_of_animals', 'Advancing_Culture', 'Advancing_Education',
        'Advancing_Health','Promote_or_oppose_a_change_to_law__government_poll_or_prac','Advancing_natual_environment',
        'Promoting_or_protecting_human_rights','Purposes_beneficial_to_ther_general_public_and_other_analogous','Promoting_reconciliation__mutual_respect_and_tolerance',
        'Advancing_Religion','Advancing_social_or_public_welfare',
        'Advancing_security_or_safety_of_Australia_or_Australian_public','Aboriginal_or_TSI','Adults',
        'Aged_Persons','Children','Communities_Overseas',
        'Early_Childhood','Ethnic_Groups','Families',
        'Females','Financially_Disadvantaged','LGBTIQA+',
        'General_Community_in_Australia','Males','Migrants_Refugees_or_Asylum_Seekers',
        'Other_Beneficiaries','Other_Charities','People_at_risk_of_homelessness',
        'People_with_Chronic_Illness','People_with_Disabilities','Pre_Post_Release_Offenders',
        'Rural_Regional_Remote_Communities','Unemployed_Person','Veterans_or_their_families',
        'Victims_of_crime','Victims_of_Disasters','Youth',
        'animals','environment','other_gender_identities'
    ]
    
    listed_charity_types = [re.sub(r'_', ' ', k) for k in charity_type_cols if charity[k] == 'Y']
    # Step 2: Organize into two columns dynamically
    half = (len(listed_charity_types) + 1) // 2  # Split into two even columns
    col1 = listed_charity_types[:half]
    col2 = listed_charity_types[half:]
    for i in range(max(len(col1), len(col2))):
        left_col = col1[i] if i < len(col1) else ""  # If col1 is shorter, fill empty space
        right_col = col2[i] if i < len(col2) else ""
    
    charity_types_html = """
<table style="width: 80%; text-align: center; border-collapse: collapse; margin: auto;">
"""
    for i in range(max(len(col1), len(col2))):
        left_col = col1[i] if i < len(col1) else ""  # If col1 is shorter, fill empty space
        right_col = col2[i] if i < len(col2) else ""
        charity_types_html += f"""
<tr>
    <td style="padding: 8px; text-align: center;">{left_col}</td>
    <td style="padding: 8px; text-align: center;">{right_col}</td>
    </tr>
"""

    charity_types_html += "</table>"

    # Extract and format financial data
    income_data = {col: float(charity[col]) if pd.notna(charity[col]) else 0.0 for col in income_cols if col in charity}
    expense_data = {col: float(charity[col]) if pd.notna(charity[col]) else 0.0 for col in expense_cols if col in charity}
    balance_data = {col: float(charity[col]) if pd.notna(charity[col]) else 0.0 for col in balance_cols if col in charity}

    # Format numbers with commas and negative formatting
    formatted_income_data = {k: f"${int(v):,}" if v >= 0 else f"$({-int(v):,})" for k, v in income_data.items()}
    formatted_expense_data = {k: f"${int(v):,}" if v >= 0 else f"$({-int(v):,})" for k, v in expense_data.items()}
    formatted_balance_data = {k: f"${int(v):,}" if v >= 0 else f"$({-int(v):,})" for k, v in balance_data.items()}

    # Format net surplus/deficit
    charity['Net surplus/(deficit)'] = (
        f"$({-int(charity['Net surplus/(deficit)']):,})" 
        if charity['Net surplus/(deficit)'] < 0 
        else f"${int(charity['Net surplus/(deficit)']):,}"
    )

    # Convert to DataFrames
    income_statement = pd.DataFrame([
        ("Gross Income", ""),  # Section Header
        *formatted_income_data.items(),
        ("Expenses", ""),  # Section Header
        *formatted_expense_data.items(),
        ("Net Income", ""),  # Section Header
        ("Net surplus/(deficit)", charity['Net surplus/(deficit)']),
        ("Other comprehensive income", "$0"),
        ("Total comprehensive income", charity['Net surplus/(deficit)']),
    ], columns=["Category", "Amount ($)"])

    balance_sheet = pd.DataFrame([
        ("Assets", ""),  # Section Header
        *[(k, v) for k, v in formatted_balance_data.items() if "assets" in k.lower() and "net" not in k.lower()],  # Assets Only

        ("Liabilities", ""),  # Section Header
        *[(k, v) for k, v in formatted_balance_data.items() if "liabilities" in k.lower() and "net" not in k.lower()],  # Liabilities Only

        ("Net Assets/Liabilities", ""),  # Section Header
        ("Net assets/liabilities", formatted_balance_data.get("Net assets/liabilities", "$0"))  # Only once
    ], columns=["Category", "Amount ($)"])

    # Generate interactive Plotly chart as an HTML string
    plotly_chart_html = generate_combined_plotly_pie_chart(income_data, expense_data, "Financial Breakdown")

    # Convert DataFrames to HTML tables with styling
    income_table_html = format_table_html(
        income_statement,
        bold_rows=['Total revenue', 'Total gross income', 'Total expenses', 'Net surplus/(deficit)', 'Total comprehensive income'],
        underline_rows=['Total revenue','Total gross income', 'Total expenses', 'Net surplus/(deficit)', 'Total comprehensive income']
    )

    balance_table_html = format_table_html(
        balance_sheet,
        bold_rows=['Total assets', 'Total liabilities', 'Net assets/liabilities'],
        underline_rows=['Total assets', 'Total liabilities', 'Net assets/liabilities']
    )
    
    #@map_iframe = generate_map_html(address)
    map_iframe = generate_map_html(latitude, longitude, address, charity_legal_name)

    # Ensure Markdown text is correctly formatted
    charity_summary = f"""---
# **{charity_legal_name}** : ABN {abn}

**Address:** {address}  
**ACNC Profile:** <a href="{acnc_website}" target="_blank" rel="noopener noreferrer">View Profile</a>  
**Reporting Year:** {reporting_year}  
**Latest Financial Report:** <a href="{latest_report}" target="_blank" rel="noopener noreferrer">Download Report</a>  
**Net Surplus/(Deficit):** {charity['Net surplus/(deficit)']}  
**Surplus Percentage:** {charity['Surplus_Percentage']:.2f}%

---

# Who Does This Charity Help?
{charity_types_html}\n

---

# **Financial Breakdown**
## **Income & Expenses Pie Charts (Hover for values)**
{plotly_chart_html}  <!-- EMBED PLOTLY CHART DIRECTLY HERE -->

## **Income Statement**
{income_table_html}

## **Balance Sheet**
{balance_table_html}

# **Location Map**
{map_iframe}  <!-- EMBED THE MAP HERE -->

---
"""

    return charity_summary

def convert_md_to_html(md_content, html_filename):
    """Convert concatenated Markdown content directly into a properly formatted A4-sized HTML file."""
    
    # Convert Markdown to HTML with necessary extensions
    html_content = markdown.markdown(
        md_content, 
        extensions=['extra', 'tables', 'fenced_code', 'toc']
    )

    # Wrap with proper A4 page layout
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Charity Financial Report</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}

            body {{
                font-family: Arial, sans-serif;
                line-height: 1.5;
                max-width: 21cm;
                padding: 2cm;
                margin: auto;
                background-color: white;
                color: black;
            }}

            h1, h2 {{
                color: #333;
                text-align: center;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                page-break-inside: avoid;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}

            th {{
                background-color: #f4f4f4;
            }}

            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 10px auto;
                page-break-before: avoid;
            }}

            a {{
                color: #007bff;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Save directly to an HTML file
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(full_html)
        
## ----------------- Script for Report.html ----------------- ##
# ✅ 1. Process & Prepare Data
def prepare_data(csv_filename, report_folder):
    """ Load and prepare data for the HTML report """
    df = pd.read_csv(csv_filename)

    # Drop any -inf values from Surplus_Percentage
    df = df[df["Surplus_Percentage"] != -float("inf")]

    # Function to format filenames consistently
    def format_filename(name):
        return name.replace(" ", "_").replace("/", "_")[:50]  # Matches how you save reports

    # Convert Charity Legal Name into a clickable link that correctly maps to the stored HTML file
    df["Charity_Legal_Name"] = df["Charity_Legal_Name"].apply(
        lambda name: f'<a href="javascript:void(0);" onclick="loadReport(\'{report_folder}/{format_filename(name)}.html\')">{name}</a>'
    )

    return df

# ✅ 2. Generate HTML Tables & Filters
def generate_html(df, md_content):
    """ Convert DataFrame & Markdown into formatted HTML """
    table_html = df.to_html(index=False, classes="display", escape=False)

    html_content = markdown.markdown(md_content, extensions=['extra', 'tables', 'fenced_code', 'toc'])

    state_options = "".join(f'<option value="{state}">{state}</option>' for state in sorted(df["State"].dropna().unique()))
    classification_options = "".join(f'<option value="{classification}">{classification}</option>' for classification in sorted(df["Classification"].dropna().unique()))

    return table_html, html_content, state_options, classification_options

#✅ 3. JavaScript for Sorting & Filters
def generate_javascript():
    """ Generate JavaScript for interactivity, filtering, sorting """
    return """
    <script>
        function loadReport(reportPath) {
            console.log("Loading report: " + reportPath);
            document.getElementById("report-container").innerHTML = 
                `<iframe src="${reportPath}" onerror="this.onerror=null; this.src='about:blank';" width="100%" height="900px"></iframe>`;
        }

        $(document).ready(function() {
            var table = $('.dataframe').DataTable({
                "paging": true,
                "searching": true,
                "ordering": true,
                "order": [[2, "desc"]],  // ✅ Sorting by Surplus Percentage (column index 2)
                "columnDefs": [
                    { "targets": 2, "type": "num" },  // ✅ Ensure Surplus Percentage is treated as a number
                    { "targets": [5, 6, 7], "type": "num" }  // ✅ Ensure financial columns are sorted numerically
                ],
                "dom": 'lfrtip',  // ✅ Enables filtering, search, pagination, and length menu
                "pagingType": "full_numbers"
            });

            $('#state-filter').on('change', function() {
                var selectedState = $(this).val();
                table.column(13).search(selectedState ? '^' + selectedState + '$' : '', true, false).draw();
            });

            $('#classification-filter').on('change', function() {
                var selectedClassification = $(this).val();
                table.column(14).search(selectedClassification ? '^' + selectedClassification + '$' : '', true, false).draw();
            });
        });
    </script>
    """


# ✅ 4. Assemble Full HTML
def assemble_full_html(table_html, html_content, state_options, classification_options, javascript_code):
    """ Assemble the full HTML page with all components """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Charity Financial Report</title>

        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.11.5/js/dataTables.bootstrap5.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css">

        <style>
            /* Main container */
            .container {{
                max-width: 21cm; /* Keeps report content within A4 width */
                margin: auto;
                padding: 20px;
                background: white;
                box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
            }}

            h1, h2 {{ text-align: center; }}

            /* Updated table formatting */
            .summary-table {{
                width: 100%;  /* Ensures tables take full width */
                max-width: 21cm;  /* Matches A4 width */
                margin: 20px auto;  /* Centers the table */
                border-collapse: collapse;
                text-align: center;
            }}

            .summary-table th, .summary-table td {{
                padding: 10px;
                border: 1px solid #ddd;
                text-align: center;
            }}

            th {{
                background-color: #f4f4f4;
            }}

            /* Interactive table stretches full width */
            .full-width {{
                width: 100%;
                margin-top: 20px;
                overflow-x: auto;
            }}

            /* Filter section */
            .filter-container {{
                margin-bottom: 15px;
                display: flex;
                justify-content: space-between;
                flex-wrap: wrap;
            }}

            .filter-container select {{
                padding: 5px;
                font-size: 16px;
            }}

            /* Report container (where company reports load) */
            #report-container {{
                border: 1px solid #ddd;
                padding: 20px;
                margin-top: 20px;
                min-height: 1200px;
                background: white;
                text-align: center;
            }}

            iframe {{
                width: 100%;
                height: 1200px;
                border: none;
            }}
        </style>
    </head>
    <body>
        <!-- Main Report Section -->
        <div class="container">
            <h1>📊 Analysis of ACNC Charity & NDIS Registered Providers With Surplus Percentage ≤ 4%</h1>
            <div class="meta-info" style="text-align: center;">
                <p><strong>Generated:</strong> {dt.datetime.now().strftime('%Y-%m-%d')}</p>
                <p><strong>Author:</strong> Jonathan Markey <strong>Contact:</strong> jonmarkey1232@gmail.com</p>
                <p><strong>ABN:</strong> 77810429163</p>
            </div>
            <hr>

            {html_content}
        </div>

        <!-- Filters for State & Classification -->
        <h2 style="text-align: center;">Filter & View Data</h2>
        <div class="filter-container">
            <label for="state-filter">Filter by State:</label>
            <select id="state-filter">
                <option value="">All</option>
                {state_options}
            </select>

            <label for="classification-filter">Filter by Classification:</label>
            <select id="classification-filter">
                <option value="">All</option>
                {classification_options}
            </select>
        </div>

        <!-- Interactive Data Table -->
        <div class="full-width">
            {table_html}
        </div>

        <!-- Company Report Viewer -->
        <h2 style="text-align: center;">Company Report</h2>
        <div id="report-container">
            <p>Select a company from the table above to view its report here.</p>
        </div>

        {javascript_code}
    </body>
    </html>
    """


# ✅ 5. Write Final HTML to File
def write_html_file(html_content, html_filename):
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

# generating overview of charities in dataset
def generate_md_report(target_charities):    
    small = target_charities[target_charities["Total revenue"] <= 500000].shape[0]
    medium = target_charities[(target_charities["Total revenue"] > 500000) & (target_charities["Total revenue"] < 3000000)].shape[0]
    large = target_charities[target_charities["Total revenue"] >= 3000000].shape[0]
    
    report_content = f"""
<div class="page-break"></div>

## **Executive Summary**
This report presents an analysis of the financial performance of charities registered with the Australian Charities and 
Not-for-profits Commission (ACNC) that provide registered services under the National Disability Insurance Scheme (NDIS). The focus is on charities with a **surplus percentage of 4% or less**. 
A condensed summary of the results is generated in **NDIS_CHARITIES_UNPROFITABLE_CONDENSED_{dt.datetime.now().strftime('%Y-%m-%d')}.csv**. Full results can also be found in **NDIS_CHARITIES.csv**.  

*This report was generated in Python using an automated script. The data was sourced from the ACNC and NDIS. Information in this report has not been independently vetted or verified and may be inaccurate. Use this report at your own discretion.*

## **Key Findings**
<table class="summary-table">
<thead>
<tr>
<th>Category</th>
<th>Count</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Total Charities</strong></td>
<td>{target_charities.shape[0]}</td>
</tr>
<tr>
<td><strong>Small Charities (≤ $500K Revenue)</strong></td>
<td>{small}</td>
</tr>
<tr>
<td><strong>Medium Charities ($500K - $3M Revenue)</strong></td>
<td>{medium}</td>
</tr>
<tr>
<td><strong>Large Charities (≥ $3M Revenue)</strong></td>
<td>{large}</td>
</tr>
</tbody>
</table>

## **Number of Charities by State/Territory**
<table class="summary-table">
<thead>
<tr>
<th>State</th>
<th>Number of Charities</th>
</tr>
</thead>
<tbody>
<tr><td><strong>NSW</strong></td><td>{target_charities[target_charities['State'] == 'NSW'].shape[0]}</td></tr>
<tr><td><strong>VIC</strong></td><td>{target_charities[target_charities['State'] == 'VIC'].shape[0]}</td></tr>
<tr><td><strong>QLD</strong></td><td>{target_charities[target_charities['State'] == 'QLD'].shape[0]}</td></tr>
<tr><td><strong>WA</strong></td><td>{target_charities[target_charities['State'] == 'WA'].shape[0]}</td></tr>
<tr><td><strong>SA</strong></td><td>{target_charities[target_charities['State'] == 'SA'].shape[0]}</td></tr>
<tr><td><strong>TAS</strong></td><td>{target_charities[target_charities['State'] == 'TAS'].shape[0]}</td></tr>
<tr><td><strong>NT</strong></td><td>{target_charities[target_charities['State'] == 'NT'].shape[0]}</td></tr>
<tr><td><strong>ACT</strong></td><td>{target_charities[target_charities['State'] == 'ACT'].shape[0]}</td></tr>
</tbody>
</table>

## **Charities Operrating at Surplus <= 4%**

The table below shows the charities operating at a surplus percentage of 4% or less. You can filter by state or revenue classification using the dropdowns above the table. You can search for specifics using the search bar. You can sort the data by clicking on the column headers. Click on the linked charity legal names in the same column to open the charity's financial report in the window below the table. Each report was generated using an automated script in Python and is based on the data found in the NDIS_CHARITIES.csv dataset. All the individual reports can be found and viewed in the generated charity_reports folder. *Note: To view the reports in the interactive window the financial_report.html file must not be moved from its current location.*  
"""
    return report_content

## ----------------- Main Script ----------------- ##
if __name__ == "__main__":
## **Step 1: Fetching Data from Supabase**
    start_time = time.time()
    SUPABASE_URL = "https://crhttqspythjsggyjksi.supabase.co"
    # View only Key
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyaHR0cXNweXRoanNnZ3lqa3NpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE1ODY4MTgsImV4cCI6MjA1NzE2MjgxOH0.-XhvBDYuij-z4tpHE2IzIL04h8vbnoFoPVYHZ-aznGM"

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    start_time = time.time()
    warnings.filterwarnings("ignore")

    print("Charity Financial Report Generator")

    # Step 1: Fetch existing ABNs from the Supabase database
    print("Checking Online Database for unprofitable Charities...")

    charities = []
    page_size = 1000  # Supabase's default limit
    start = 0

    try:
        while True:
            response = supabase.table("NDIS_CHARITIES").select("*").range(start, start + page_size - 1).execute()
                
            if response.data:
                charities.extend(response.data)
            # If fewer than page_size records were returned, we've fetched all data
                if len(response.data) < page_size:
                    break
                
                start += page_size  # Move to the next page
            else:
                print("No existing ABNs found in the database...")
                break

    except Exception as e:
        print(f"Failed to fetch existing ABNs from Supabase: {e}...")
        sys.exit(1)
            
    print(f"Found {len(charities)} existing Charities in the database...")

## **Step 2: Data Preprocessing**
    charities_df = pd.DataFrame(charities)
    charities_df.reset_index(drop=True, inplace=True)

    nr_charities = charities_df[charities_df['Net surplus/(deficit)'].isnull()].shape[0]

    charities_df = charities_df.dropna(subset=['Net surplus/(deficit)'])

    print(f"Dropped {nr_charities} non-reporting Charities...")

    financial_cols = ['Revenue from government including grants', 'Donations and bequests',
                    'Revenue from providing goods or services', 'Revenue from investments',
                    'All other revenue', 'Total revenue',
                    'Other income (for example, gains)', 'Total gross income',
                    'Employee expenses', 'Interest expenses',
                    'Grants and donations made for use in Australia',
                    'Grants and donations made for use outside Australia',
                    'All other expenses', 'Total expenses', 'Net surplus/(deficit)',
                    'Other comprehensive income', 'Total comprehensive income',
                    'Total current assets', 'Non-current loans receivable',
                    'Other non-current assets', 'Total non-current assets', 'Total assets',
                    'Total current liabilities', 'Non-current loans payable',
                    'Other non-current liabilities', 'Total non-current liabilities',
                    'Total liabilities', 'Net assets/liabilities']

    charities_df[financial_cols] = charities_df[financial_cols].replace('[\$,]', '', regex=True).astype(float).astype('Int64')

    charities_df['Surplus_Percentage'] = charities_df['Net surplus/(deficit)'].div(charities_df['Total revenue']).mul(100)

    negative_charities = charities_df[charities_df['Net surplus/(deficit)'] < 0]

    target_charities = charities_df[charities_df['Surplus_Percentage'] <= 4]
    
    #drop where total revenue is 0 or where Financial Report URL is null or 

    print(f"Found {negative_charities.shape[0]} Charities with Negative Surplus <= 0%...")

    print(f"Found {target_charities.shape[0]} Charities with Surplus Percentage <= 4%...")
    
## **Step 3: Generating .csv file Results**
    
    key_information = target_charities[['ABN', 'Charity_Legal_Name', 'Surplus_Percentage', 'Charity_Website',
                                        'Address', 'Total revenue', 'Total expenses', 'Net surplus/(deficit)', 'Phone', 'Email', 'AIS Year', 'View AIS', 'Financial Report URL', 'State',
                                        ]]

    key_information['Surplus_Percentage'] = key_information['Surplus_Percentage'].round(2)

    key_information['Classification'] = pd.cut(
        key_information['Total revenue'],
        bins=[-float('inf'), 500000, 3000000, float('inf')],
        labels=['Small', 'Medium', 'Large']
    )
            
    date = dt.datetime.now().strftime("%Y-%m-%d")
    filename = f'NDIS_CHARITIES_UNPROFITABLE_CONDENSED_{date}.csv'
    key_information.to_csv(filename, index=False, mode = 'w')
    
## **Generating the individual charity financial reports**
    # ✅ Create a folder to store individual reports
    output_folder = "charity_reports"
    os.makedirs(output_folder, exist_ok=True)

    # ✅ Generate separate reports for each charity
    for charity in range(len(target_charities)):
        data = target_charities.iloc[charity]  # Get the charity data
        charity_report = generate_charity_report(data)  # Generate the report

        # Create a valid filename from the charity name
        charity_name = data["Charity_Legal_Name"].replace(" ", "_").replace("/", "_")[:50]  # Limit name length
        html_filename = os.path.join(output_folder, f"{charity_name}.html")

        # Convert and save each charity's report as a separate HTML file
        convert_md_to_html(charity_report, html_filename)

    print(f"All reports successfully generated in the '{output_folder}' folder.")
    
## **Generating the Final Financial Report**
    # Define file paths
    csv_filename = filename  # Replace with the actual CSV filename
    html_filename = "financial_report.html"
    report_folder = "charity_reports"  # Folder where company reports are stored
    # ✅ Step 1: Prepare Data
    df = prepare_data(csv_filename, report_folder)

    md_report = generate_md_report(target_charities)

    # ✅ Step 2: Generate Table HTML & Filters
    table_html, html_content, state_options, classification_options = generate_html(df, md_report)

    # ✅ Step 3: Generate JavaScript
    javascript_code = generate_javascript()

    # ✅ Step 4: Assemble the full HTML
    full_html = assemble_full_html(table_html, html_content, state_options, classification_options, javascript_code)

    # ✅ Step 5: Write the HTML to a file
    write_html_file(full_html, html_filename)

    print(f"\nReport successfully generated: {html_filename}\n")
    end_time = time.time()
    print(f"Process completed in {end_time - start_time:.2f} seconds.")
    