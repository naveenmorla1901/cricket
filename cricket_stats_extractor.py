import pandas as pd
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Club Configuration
clubId = [
    {"id": 1096797, "name": "Kakatiya CC", "type": "T7"},
    {"id": 1100194, "name": "Easton Cricket League", "type": "T7"},
    {"id": 2317, "name": "Dublin cricket League", "type": "T15"},
    {"id": 23340, "name":"SVATSCup", "type": "T15"},
    {"id": 21754, "name": "PDCC", "type": "T15"},
    {"id": 1000903, "name": "ColumbusCricketClubT15", "type": "T15"},
    {"id": 24116, "name": "TACO Cricket", "type": "T7"},
              # Add more like this
]

def get_cricket_stats_json(stat_type="batting", year=2025, output_dir="data"):
    """
    Extract cricket statistics and save as JSON files
    
    Args:
        stat_type: "batting", "bowling", "fielding", "ranking"
        year: Year for data (default 2025)
        output_dir: Directory to save JSON files
    """
    
    if not clubId:
        print("❌ No clubs configured! Please add club IDs to the clubId list.")
        return None

    print(f"Extracting {stat_type.upper()} statistics for {len(clubId)} configured club(s)...")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    all_data = []
    successful_clubs = []
    failed_clubs = []

    for i, club in enumerate(clubId, 1):
        club_id = club["id"]
        club_name = club["name"]
        match_type = club["type"]

        print(f"\n📊 Processing {i}/{len(clubId)}: {club_name} (ID: {club_id}, Type: {match_type})")

        try:
            df = extract_club_stats(stat_type, club_id, year)

            if df is not None and not df.empty:
                # Add club information columns
                df['Club_ID'] = club_id
                df['Club_Name'] = club_name
                df['Match_Type'] = match_type
                all_data.append(df)
                successful_clubs.append(club_name)
                print(f"   ✅ Extracted {len(df)} records")
            else:
                failed_clubs.append(f"{club_name} (No data)")
                print(f"   ⚠️  No data found")

        except Exception as e:
            failed_clubs.append(f"{club_name} (Error)")
            print(f"   ❌ Failed: {str(e)[:50]}...")
            continue

    # Summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful_clubs)} clubs")
    if successful_clubs:
        for club in successful_clubs:
            print(f"   - {club}")

    if failed_clubs:
        print(f"❌ Failed: {len(failed_clubs)} clubs")
        for club in failed_clubs:
            print(f"   - {club}")

    # Prepare JSON output
    json_data = {
        "data": [],
        "lastUpdated": datetime.now().isoformat(),
        "year": year,
        "statType": stat_type,
        "totalRecords": 0,
        "totalClubs": len(successful_clubs),
        "successfulClubs": successful_clubs,
        "failedClubs": failed_clubs
    }

    if all_data:
        # Combine all club data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Convert DataFrame to list of dictionaries
        # Handle NaN values by converting to None (which becomes null in JSON)
        json_data["data"] = combined_df.where(pd.notnull(combined_df), None).to_dict('records')
        json_data["totalRecords"] = len(combined_df)
        
        print(f"\n🎯 Final Result: {len(combined_df)} total records from {len(successful_clubs)} club(s)")
    else:
        print(f"\n❌ No data extracted from any club")

    # Save JSON file
    filename = f"{output_dir}/{stat_type}_{year}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"📁 Saved: {filename}")
    return json_data

def extract_club_stats(stat_type, club_id, year):
    """Extract stats for a single club"""

    # URL mapping for different stat types
    url_patterns = {
        "batting": f"https://cricclubs.com/allBattingRecords.do?league=all&year={year}&clubId={club_id}",
        "bowling": f"https://cricclubs.com/bowlingRecords.do?league=all&year={year}&clubId={club_id}",
        "fielding": f"https://cricclubs.com/fieldingRecords.do?league=all&year={year}&clubId={club_id}",
        "ranking": f"https://cricclubs.com/playerRankings.do?year={year}&league=all&clubId={club_id}"
    }

    if stat_type not in url_patterns:
        print(f"❌ Invalid stat type: {stat_type}")
        return None

    url = url_patterns[stat_type]

    # Chrome options for GitHub Actions (with warnings suppressed)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--log-level=3')  # Suppress INFO, WARNING, ERROR
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        return parse_stats_data(soup, stat_type)

    finally:
        if driver:
            driver.quit()

def parse_stats_data(soup, stat_type):
    """Parse different types of statistics tables"""

    # Keywords to identify different stat types
    table_keywords = {
        "batting": ['player', 'runs', 'mat', 'inns'],
        "bowling": ['player', 'wickets', 'overs', 'runs', 'economy'],
        "fielding": ['player', 'catches', 'stumping', 'runout'],
        "ranking": ['player', 'points', 'ranking', 'position']
    }

    tables = soup.find_all('table')

    # Find the correct table for stat type
    for table in tables:
        header_text = ' '.join([th.get_text().lower() for th in table.find_all(['th', 'td'])[:10]])

        expected_keywords = table_keywords.get(stat_type, ['player'])
        keyword_matches = sum(1 for word in expected_keywords if word in header_text)

        if keyword_matches >= 2:  # At least 2 matching keywords
            return extract_table_data(table, stat_type)

    return None

def extract_table_data(table, stat_type):
    """Extract data from statistics table"""
    rows = table.find_all('tr')
    if len(rows) < 2:
        return None

    headers = [cell.get_text().strip() for cell in rows[0].find_all(['th', 'td']) if cell.get_text().strip()]

    data = []
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) >= 2:
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    value = cell.get_text().strip()

                    # Extract player ID from links (usually in player column)
                    if ('player' in headers[i].lower() or i <= 1) and cell.find('a'):
                        href = cell.find('a').get('href', '')
                        if 'playerId=' in href:
                            row_data['Player_ID'] = href.split('playerId=')[1].split('&')[0]

                    row_data[headers[i]] = value

            # Only add rows with player names
            player_field = next((k for k in row_data.keys() if 'player' in k.lower()), None)
            if player_field and row_data.get(player_field, '').strip():
                data.append(row_data)

    if data:
        df = pd.DataFrame(data)
        return clean_stats_data(df, stat_type)
    return None

def clean_stats_data(df, stat_type):
    """Clean data based on stat type"""

    # Common numeric patterns for different stat types
    cleaning_patterns = {
        "batting": {
            'int_cols': ['#', 'Mat', 'Inns', 'NO', 'Runs', 'Points', "4's", "6's", "50's", "100's", 'HS'],
            'float_cols': ['SR', 'Avg']
        },
        "bowling": {
            'int_cols': ['#', 'Mat', 'Overs', 'Runs', 'Wkts', 'Maidens', 'Points'],
            'float_cols': ['Avg', 'Econ', 'SR']
        },
        "fielding": {
            'int_cols': ['#', 'Mat', 'Catches', 'Stumping', 'RunOut', 'Points'],
            'float_cols': []
        },
        "ranking": {
            'int_cols': ['#', 'Rank', 'Points', 'Matches'],
            'float_cols': ['Avg']
        }
    }

    patterns = cleaning_patterns.get(stat_type, cleaning_patterns["batting"])

    # Clean numeric columns
    for col in patterns['int_cols']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace(['--', '-', '', '*', 'N/A'], '0'), errors='coerce').fillna(0).astype(int)

    for col in patterns['float_cols']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace(['--', '-', '', '*', 'N/A'], '0'), errors='coerce').fillna(0)

    return df

def extract_all_stats(year=2025, output_dir="data"):
    """Extract all stat types for given year"""
    stat_types = ["batting", "bowling", "fielding", "ranking"]
    
    print(f"🚀 Starting extraction of all statistics for {year}")
    print(f"📂 Output directory: {output_dir}")
    print(f"🏏 Clubs configured: {len(clubId)}")
    
    results = {}
    
    for stat_type in stat_types:
        print(f"\n{'='*80}")
        print(f"🎯 EXTRACTING {stat_type.upper()} STATISTICS")
        print(f"{'='*80}")
        
        try:
            result = get_cricket_stats_json(stat_type, year, output_dir)
            results[stat_type] = result
            print(f"✅ {stat_type.capitalize()} extraction completed")
        except Exception as e:
            print(f"❌ {stat_type.capitalize()} extraction failed: {str(e)}")
            results[stat_type] = None
    
    # Create summary file
    summary = {
        "extractionTime": datetime.now().isoformat(),
        "year": year,
        "totalClubs": len(clubId),
        "clubsConfigured": [{"id": club["id"], "name": club["name"], "type": club["type"]} for club in clubId],
        "results": {
            stat_type: {
                "success": result is not None,
                "totalRecords": result["totalRecords"] if result else 0,
                "successfulClubs": result["successfulClubs"] if result else [],
                "failedClubs": result["failedClubs"] if result else []
            } for stat_type, result in results.items()
        }
    }
    
    summary_file = f"{output_dir}/extraction_summary_{year}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎯 FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"📊 Total extractions: {len(stat_types)}")
    print(f"✅ Successful: {sum(1 for r in results.values() if r is not None)}")
    print(f"❌ Failed: {sum(1 for r in results.values() if r is None)}")
    print(f"📁 Summary saved: {summary_file}")
    
    return results

if __name__ == "__main__":
    import sys
    
    # Get year from command line argument or use default
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    
    print(f"🏏 Cricket Stats Extractor")
    print(f"📅 Year: {year}")
    print(f"📂 Output: {output_dir}")
    print(f"🏆 Clubs: {len(clubId)} configured")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Extract all statistics
    results = extract_all_stats(year, output_dir)
    
    print(f"\n🎉 All done! Check the '{output_dir}' directory for JSON files.")