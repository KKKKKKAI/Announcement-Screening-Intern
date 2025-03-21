"""
Press Release Webpage Downloader
--------------------------------
This script fetches the latest press releases from the database and downloads
their content to local HTML files for archiving and processing.
"""

import requests
import os
import sqlite3
import logging
import argparse
from datetime import datetime
import trafilatura
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webpage_downloader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('webpage_downloader')

def download_webpage(url, output_folder="downloaded_pages"):
    """
    Downloads a webpage's HTML content to a local file.
    
    Args:
        url: The URL of the webpage to download
        output_folder: Folder to save the downloaded HTML
    
    Returns:
        The path to the saved file
    """
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': '*',  # Accept all languages
        'Accept-Encoding': 'identity',  # Request uncompressed content
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # Get the webpage content
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        
        # Create a filename based on the URL and timestamp
        domain = url.split('//')[-1].split('/')[0].replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.html"
        filepath = os.path.join(output_folder, filename)
        
        # Save the content to a file
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(response.text)
        
        logger.info(f"Webpage saved to: {filepath}")
        return filepath
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading webpage: {e}")
        return None

def extract_from_local_file(filepath):
    """
    Extract the main content from a locally saved HTML file using Trafilatura.
    
    Args:
        filepath: Path to the local HTML file
        
    Returns:
        The extracted text content
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        extracted_text = trafilatura.extract(html_content)
        return extracted_text
    
    except Exception as e:
        logger.error(f"Error extracting content: {e}")
        return None

def get_latest_press_releases(database_path="press_releases.db", days=1, limit=10, company_name=None, download_processed=False):
    """
    Retrieve the latest press releases from the database.
    
    Args:
        database_path: Path to the SQLite database
        days: Only retrieve press releases from last N days
        limit: Maximum number of press releases to retrieve
        company_name: Filter by specific company name
        download_processed: Whether to include already downloaded press releases
    
    Returns:
        List of press release dictionaries
    """
    if not os.path.exists(database_path):
        logger.error(f"Database file not found: {database_path}")
        return []
    
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Check if downloaded_pages table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloaded_pages'")
        downloaded_table_exists = cursor.fetchone() is not None
        
        # Create downloaded_pages table if it doesn't exist
        if not downloaded_table_exists:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloaded_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                press_release_id INTEGER,
                html_path TEXT,
                text_path TEXT,
                download_date TEXT,
                FOREIGN KEY (press_release_id) REFERENCES press_releases(id)
            )
            ''')
            conn.commit()
            logger.info("Created downloaded_pages table")
        
        # Start preparing the query and parameters
        params = []
        
        # Base query - start with these conditions regardless of other filters
        base_query = """
            SELECT id, company_name, title, link, summary, date, first_seen
            FROM press_releases
            WHERE 1=1
        """
        
        # Add date filter
        if days > 0:
            base_query += " AND first_seen >= datetime('now', '-' || ? || ' day')"
            params.append(days)
        
        # Add company filter if provided
        if company_name:
            base_query += " AND company_name = ?"
            params.append(company_name)
        
        # Add download filter if needed and if table exists
        if downloaded_table_exists and not download_processed:
            base_query += """ AND NOT EXISTS (
                SELECT 1 FROM downloaded_pages 
                WHERE press_release_id = press_releases.id
            )"""
        
        # Add order and limit
        base_query += " ORDER BY first_seen DESC"
        if limit > 0:
            base_query += " LIMIT ?"
            params.append(limit)
        
        # Log the query and parameters for debugging
        logger.debug(f"SQL Query: {base_query}")
        logger.debug(f"Parameters: {params}")
        
        # Execute the query
        cursor.execute(base_query, params)
        releases = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        logger.info(f"Retrieved {len(releases)} press releases from database")
        return releases
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        # Print the traceback for easier debugging
        import traceback
        logger.error(traceback.format_exc())
        return []

def download_press_releases(releases, output_folder="downloaded_pages", extract_text=True, database_path="press_releases.db"):
    """
    Download web pages for a list of press releases.
    
    Args:
        releases: List of press release dictionaries
        output_folder: Folder to save downloaded HTML
        extract_text: Whether to extract text content from HTML
        database_path: Path to the SQLite database
    
    Returns:
        Number of successfully downloaded press releases
    """
    if not releases:
        logger.info("No press releases to download")
        return 0
    
    # Ensure download tracking table exists
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Create downloaded_pages table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloaded_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            press_release_id INTEGER,
            html_path TEXT,
            text_path TEXT,
            download_date TEXT,
            FOREIGN KEY (press_release_id) REFERENCES press_releases(id)
        )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error setting up downloaded_pages table: {e}")
        return 0
    
    success_count = 0
    
    for release in releases:
        logger.info(f"Downloading: {release['title']} ({release['link']})")
        
        # Add a small delay to avoid hammering the server
        time.sleep(1)
        
        # Download the HTML
        html_path = download_webpage(release['link'], output_folder)
        
        if html_path:
            text_path = None
            
            # Extract text if requested
            if extract_text:
                extracted_text = extract_from_local_file(html_path)
                if extracted_text:
                    text_path = html_path.replace(".html", ".txt")
                    try:
                        with open(text_path, 'w', encoding='utf-8') as file:
                            file.write(extracted_text)
                        logger.info(f"Extracted content saved to: {text_path}")
                    except Exception as e:
                        logger.error(f"Error saving extracted text: {e}")
                        text_path = None
            
            # Record the download in the database
            try:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                INSERT INTO downloaded_pages (press_release_id, html_path, text_path, download_date)
                VALUES (?, ?, ?, ?)
                ''', (release['id'], html_path, text_path, current_time))
                conn.commit()
                success_count += 1
            except sqlite3.Error as e:
                logger.error(f"Database error recording download: {e}")
    
    conn.close()
    logger.info(f"Successfully downloaded {success_count}/{len(releases)} press releases")
    return success_count

def main():
    parser = argparse.ArgumentParser(description='Download press release web pages from database')
    parser.add_argument('--db', default='press_releases.db', help='Path to the database file')
    parser.add_argument('--output', default='downloaded_pages', help='Output folder for downloaded pages')
    parser.add_argument('--days', type=int, default=7, help='Only download press releases from last N days')
    parser.add_argument('--limit', type=int, default=20, help='Maximum number of press releases to download')
    parser.add_argument('--company', help='Filter by company name')
    parser.add_argument('--all', action='store_true', help='Download all matching releases, including already processed ones')
    parser.add_argument('--no-extract', action='store_true', help='Skip text extraction')
    
    args = parser.parse_args()
    
    # Ensure download tracking table exists first
    try:
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        
        # Create downloaded_pages table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloaded_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            press_release_id INTEGER,
            html_path TEXT,
            text_path TEXT,
            download_date TEXT,
            FOREIGN KEY (press_release_id) REFERENCES press_releases(id)
        )
        ''')
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Database error setting up downloaded_pages table: {e}")
        return
    
    # Get latest press releases
    releases = get_latest_press_releases(
        database_path=args.db,
        days=args.days,
        limit=args.limit,
        company_name=args.company,
        download_processed=args.all
    )
    
    if not releases:
        logger.info("No press releases found matching criteria")
        return
    
    logger.info(f"Found {len(releases)} press releases to download")
    
    # Download the press releases
    download_press_releases(
        releases,
        output_folder=args.output,
        extract_text=not args.no_extract,
        database_path=args.db
    )

if __name__ == "__main__":
    main()