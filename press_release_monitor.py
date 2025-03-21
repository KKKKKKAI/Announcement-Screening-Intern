import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import time
import hashlib
import logging
import smtplib
import importlib.util
import inspect
import re
import subprocess
import ollama
from email.message import EmailMessage
from datetime import datetime
import schedule

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("press_release_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('press_release_monitor')

class PressReleaseMonitor:
    def __init__(self, url, company_name, extractor_path=None, database_path="press_releases.db", 
                 email_config=None, summarization_model="llama3.2"):
        """
        Initialize the press release monitor.
        
        Args:
            url (str): URL of the press release page to monitor
            company_name (str): Name of the company being monitored
            extractor_path (str): Path to the Python file containing the custom extractor function
            database_path (str): Path to the SQLite database
            email_config (dict): Configuration for email notifications
            summarization_model (str): Ollama model to use for summarization
        """
        self.url = url
        self.company_name = company_name
        self.database_path = database_path
        self.email_config = email_config
        self.summarization_model = summarization_model
        self.extractor_func = self._load_extractor(extractor_path)
        self.setup_database()
        
    def _load_extractor(self, extractor_path):
        """
        Load the custom extractor function from a file.
        
        Args:
            extractor_path (str): Path to the Python file containing the extractor function
            
        Returns:
            function: The loaded extractor function or default extractor if path is None
        """
        if not extractor_path:
            logger.info("No custom extractor provided, using default extractor")
            return self._default_extract_press_releases
            
        try:
            logger.info(f"Loading custom extractor from {extractor_path}")
            
            # Load the module from file path
            spec = importlib.util.spec_from_file_location("extractor_module", extractor_path)
            extractor_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(extractor_module)
            
            # Find extraction function in the module
            for name, obj in inspect.getmembers(extractor_module):
                if name == "extract_press_releases" and inspect.isfunction(obj):
                    logger.info(f"Successfully loaded extractor function: {name}")
                    return obj
                    
            # If function not found, fall back to default
            logger.warning(f"No 'extract_press_releases' function found in {extractor_path}, using default extractor")
            return self._default_extract_press_releases
            
        except Exception as e:
            logger.error(f"Error loading custom extractor: {e}")
            logger.info("Falling back to default extractor")
            return self._default_extract_press_releases
    
    def _default_extract_press_releases(self, soup, base_url):
        """
        Default extractor for press releases from HTML.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            base_url (str): Base URL for resolving relative links
            
        Returns:
            list: List of dictionaries containing press release information
        """
        releases = []
        
        try:
            # Try multiple common selectors for press releases
            selectors = [
                '.press-release-item, .news-item, article, .press-release',
                '.news-listing article, .press-releases li, .news-container .item',
                'a.news-item, a.press-item, div.press-item, div.news-item',
                '.news a, .press a, .press-releases a'
            ]
            
            press_items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    press_items = items
                    logger.info(f"Found {len(items)} press items using selector: {selector}")
                    break
            
            # If still not found, try to look for items with news/press in class name
            if not press_items:
                press_items = soup.find_all(['div', 'article', 'li', 'a'], class_=lambda c: c and ('news' in c.lower() or 'press' in c.lower()))
                logger.info(f"Found {len(press_items)} press items using class name search")
            
            # If still not found, look for anchor tags with date-like strings
            if not press_items:
                all_links = soup.find_all('a')
                date_pattern = r'(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
                press_items = [link for link in all_links if link.text and re.search(date_pattern, link.text.lower())]
                logger.info(f"Found {len(press_items)} press items using date pattern search")
            
            for item in press_items:
                # Try multiple selectors for title and link
                title_element = None
                for title_selector in ['h2', 'h3', 'h4', '.title', '.headline', 'strong', 'b']:
                    title_element = item.select_one(title_selector)
                    if title_element:
                        break
                
                # Find link element - either the item itself (if it's an <a>) or an <a> inside it
                link_element = item if item.name == 'a' else item.find('a')
                
                # Try to find date element
                date_element = None
                for date_selector in ['.date', 'time', '.published', '.timestamp', '.meta', 'span']:
                    date_element = item.select_one(date_selector)
                    if date_element:
                        break
                
                # Try to find summary element
                summary_element = None
                for summary_selector in ['.summary', '.excerpt', '.description', 'p', '.teaser']:
                    summary_element = item.select_one(summary_selector)
                    if summary_element:
                        break
                
                if title_element and link_element:
                    title = title_element.get_text(strip=True)
                    link = link_element.get('href')
                    
                    # Handle relative URLs
                    if link and link.startswith('/'):
                        link = base_url + link
                    
                    # Extract date if available, or use current date
                    date = date_element.get_text(strip=True) if date_element else datetime.now().strftime('%Y-%m-%d')
                    
                    # Extract summary if available
                    summary = summary_element.get_text(strip=True) if summary_element else ''
                    
                    # Create a hash of the content for comparison
                    content = f"{title}|{link}|{summary}|{date}"
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    releases.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'date': date,
                        'content_hash': content_hash
                    })
            
            logger.info(f"Extracted {len(releases)} press releases")
        except Exception as e:
            logger.error(f"Error extracting press releases: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return releases
    
    def setup_database(self):
        """Set up the SQLite database to store press release data."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Check if company_name column exists, if not, add it
        cursor.execute("PRAGMA table_info(press_releases)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Create table if it doesn't exist
        if 'press_releases' not in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            cursor.execute('''
            CREATE TABLE press_releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                title TEXT,
                link TEXT,
                summary TEXT,
                date TEXT,
                content_hash TEXT,
                first_seen TEXT,
                last_checked TEXT,
                UNIQUE(company_name, link)
            )
            ''')
            logger.info("Created new press_releases table with company_name column")
        elif 'company_name' not in columns:
            # Add company_name column if it doesn't exist and table already exists
            cursor.execute("ALTER TABLE press_releases ADD COLUMN company_name TEXT")
            logger.info("Added company_name column to existing press_releases table")
            
            # Remove old unique constraint and add a new one including company_name
            try:
                # SQLite doesn't support DROP CONSTRAINT directly, need to recreate table
                cursor.execute('''
                CREATE TABLE press_releases_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    title TEXT,
                    link TEXT,
                    summary TEXT,
                    date TEXT,
                    content_hash TEXT,
                    first_seen TEXT,
                    last_checked TEXT,
                    UNIQUE(company_name, link)
                )
                ''')
                
                # Copy data from old table to new
                cursor.execute('''
                INSERT INTO press_releases_new(id, title, link, summary, date, content_hash, first_seen, last_checked)
                SELECT id, title, link, summary, date, content_hash, first_seen, last_checked FROM press_releases
                ''')
                
                # Drop old table and rename new one
                cursor.execute("DROP TABLE press_releases")
                cursor.execute("ALTER TABLE press_releases_new RENAME TO press_releases")
                logger.info("Restructured table to include company_name in uniqueness constraint")
            except sqlite3.Error as e:
                logger.error(f"Error restructuring database: {e}")
        
        # Set up article_summaries table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS article_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            model_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (content_id) REFERENCES extracted_content(id)
        )
        ''')
        
        # Create index for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_id ON article_summaries(content_id)')
        
        conn.commit()
        conn.close()
        logger.info(f"Database setup completed at {self.database_path}")
        
    def fetch_press_releases(self):
        """Fetch and parse the press release page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching press releases: {e}")
            return None
    
    def extract_press_releases(self, soup):
        """
        Extract press releases from the parsed HTML using the loaded extractor function.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            list: List of dictionaries containing press release information
        """
        base_url = '/'.join(self.url.split('/')[:3])  # Extract base URL (e.g., https://example.com)
        
        try:
            # Call the extractor function with soup and base_url
            return self.extractor_func(soup, base_url)
        except TypeError:
            # Some older extractors might not accept base_url, try with just soup
            try:
                return self.extractor_func(soup)
            except Exception as e:
                logger.error(f"Error calling extractor function: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return []
    
    def download_new_releases(self, new_releases):
        """Download the content of newly detected press releases."""
        if new_releases:
            try:
                logger.info(f"Downloading content for {len(new_releases)} new press releases")
                subprocess.run([
                    "python", "webpage_downloader.py", 
                    "--company", self.company_name,
                    "--days", "1"  # Only get very recent ones
                ], check=True)
                return True
            except subprocess.SubprocessError as e:
                logger.error(f"Error downloading content: {e}")
                return False
        return False
    
    def get_extracted_content_ids(self, press_release_ids):
        """
        Get extracted content IDs for the given press release IDs.
        
        Args:
            press_release_ids (list): List of press release IDs
            
        Returns:
            dict: Mapping of press release IDs to extracted content IDs
        """
        if not press_release_ids:
            return {}
            
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Build placeholders for SQL IN clause
        placeholders = ','.join(['?'] * len(press_release_ids))
        
        # Query content IDs
        cursor.execute(f'''
        SELECT press_release_id, id 
        FROM extracted_content 
        WHERE press_release_id IN ({placeholders})
        ''', press_release_ids)
        
        id_mapping = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        return id_mapping
    
    def summarize_content(self, content_ids):
        """
        Generate summaries for the given content IDs.
        
        Args:
            content_ids (list): List of content IDs to summarize
            
        Returns:
            dict: Mapping of content IDs to summaries
        """
        if not content_ids:
            return {}
            
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Initialize Ollama client
        client = ollama.Client()
        summaries = {}
        
        for content_id in content_ids:
            # Check if summary already exists
            cursor.execute(
                "SELECT id, summary FROM article_summaries WHERE content_id = ?", 
                (content_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Use existing summary
                summaries[content_id] = existing[1]
                logger.info(f"Using existing summary for content ID {content_id}")
            else:
                # Get content to summarize
                cursor.execute(
                    "SELECT content FROM extracted_content WHERE id = ?", 
                    (content_id,)
                )
                content_row = cursor.fetchone()
                
                if content_row and content_row[0]:
                    try:
                        # Create prompt for summarization
                        prompt = f"Please summarize the following article concisely into bullet points:\n\n{content_row[0]}"
                        
                        # Generate summary using Ollama
                        response = client.generate(model=self.summarization_model, prompt=prompt)
                        summary = response.response
                        
                        # Save summary to database
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        cursor.execute(
                            'INSERT INTO article_summaries (content_id, summary, model_name, created_at) VALUES (?, ?, ?, ?)',
                            (content_id, summary, self.summarization_model, current_time)
                        )
                        conn.commit()
                        
                        summaries[content_id] = summary
                        logger.info(f"Generated new summary for content ID {content_id}")
                    except Exception as e:
                        logger.error(f"Error generating summary for content ID {content_id}: {str(e)}")
        
        conn.close()
        return summaries
    
    def save_new_releases(self, releases):
        """Save new press releases to the database and return new ones."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        new_releases = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for release in releases:
            # Skip entries without essential data
            if not release.get('title') or not release.get('link'):
                continue
                
            # Check if this release exists for this company
            cursor.execute(
                "SELECT id FROM press_releases WHERE company_name = ? AND (link = ? OR content_hash = ?)", 
                (self.company_name, release['link'], release['content_hash'])
            )
            
            existing = cursor.fetchone()
            
            if not existing:
                # This is a new release
                cursor.execute('''
                INSERT INTO press_releases (company_name, title, link, summary, date, content_hash, first_seen, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.company_name,
                    release['title'],
                    release['link'],
                    release.get('summary', ''),
                    release.get('date', current_time),
                    release['content_hash'],
                    current_time,
                    current_time
                ))
                
                # Get the ID of the inserted row
                release['id'] = cursor.lastrowid
                
                # Add company name to the release data for notifications
                release['company_name'] = self.company_name
                new_releases.append(release)
            else:
                # Update last_checked timestamp
                cursor.execute(
                    "UPDATE press_releases SET last_checked = ? WHERE company_name = ? AND link = ?",
                    (current_time, self.company_name, release['link'])
                )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Found {len(new_releases)} new press releases for {self.company_name}")
        return new_releases
            
    def send_email_notification(self, new_releases, summaries=None):
        """
        Send email notification for new press releases with summaries if available.
        
        Args:
            new_releases (list): List of new press releases
            summaries (dict): Mapping of content IDs to summaries
        """
        if not self.email_config or not new_releases:
            return
        
        try:
            msg = EmailMessage()
            msg['Subject'] = f"[Press Release Alert] {len(new_releases)} New Press Releases from {self.company_name}"
            msg['From'] = self.email_config['from']
            msg['To'] = self.email_config['to']
            
            content = f"New press releases detected from {self.company_name}:\n\n"
            
            for idx, release in enumerate(new_releases, 1):
                content += f"{idx}. {release['title']}\n"
                content += f"   Date: {release.get('date', 'N/A')}\n"
                content += f"   Link: {release['link']}\n"
                
                # Add summary if available
                if summaries and 'content_id' in release and release['content_id'] in summaries:
                    content += f"\n   Summary:\n{summaries[release['content_id']]}\n"
                elif release.get('summary'):
                    content += f"   Brief: {release['summary']}\n"
                
                content += "\n" + "-"*50 + "\n\n"
            
            msg.set_content(content)
            
            with smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
                
            logger.info(f"Email notification with summaries sent successfully for {self.company_name}")
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    def check_for_updates(self):
        """Main function to check for updates."""
        logger.info(f"Checking for updates at {self.url} for {self.company_name}")
        
        soup = self.fetch_press_releases()
        if not soup:
            return
        
        releases = self.extract_press_releases(soup)
        new_releases = self.save_new_releases(releases)
        
        if new_releases:
            logger.info(f"Found {len(new_releases)} new press releases for {self.company_name}")
            
            # Get IDs for the new releases
            press_release_ids = [release['id'] for release in new_releases if 'id' in release]
            
            # Download content of new releases
            download_success = self.download_new_releases(new_releases)
            
            if download_success:
                # Wait a moment for downloads to complete
                time.sleep(2)
                
                # Get extracted content IDs
                content_id_mapping = self.get_extracted_content_ids(press_release_ids)
                
                # Add content IDs to release objects for reference
                for release in new_releases:
                    if 'id' in release and release['id'] in content_id_mapping:
                        release['content_id'] = content_id_mapping[release['id']]
                
                # Generate summaries for new content
                content_ids = list(content_id_mapping.values())
                summaries = self.summarize_content(content_ids)
                
                # Log the new releases
                for release in new_releases:
                    logger.info(f"New release for {self.company_name}: {release['title']} - {release['link']}")
                
                # Send email notification with summaries
                if self.email_config:
                    self.send_email_notification(new_releases, summaries)
            else:
                # Send email notification without summaries
                if self.email_config:
                    self.send_email_notification(new_releases)
        else:
            logger.info(f"No new press releases found for {self.company_name}")
        
        return new_releases


def run_daily_check(url, company_name, extractor_path=None, email_config=None, summarization_model="llama3.2"):
    """Run the press release check once."""
    monitor = PressReleaseMonitor(
        url, 
        company_name, 
        extractor_path=extractor_path, 
        email_config=email_config,
        summarization_model=summarization_model
    )
    return monitor.check_for_updates()


def setup_scheduled_checks(url, company_name, time_of_day="09:00", extractor_path=None, 
                           email_config=None, summarization_model="llama3.2"):
    """Set up scheduled daily checks."""
    logger.info(f"Setting up scheduled checks for {company_name} at {url} at {time_of_day} daily")
    
    monitor = PressReleaseMonitor(
        url, 
        company_name, 
        extractor_path=extractor_path, 
        email_config=email_config,
        summarization_model=summarization_model
    )
    
    # Run an immediate check
    monitor.check_for_updates()
    
    def job():
        monitor.check_for_updates()
    
    schedule.every().day.at(time_of_day).do(job)
    
    logger.info(f"Scheduled daily checks for {company_name} at {time_of_day}")
    return monitor


def run_multiple_companies(companies, email_config=None, summarization_model="llama3.2"):
    """
    Run checks for multiple companies.
    
    Args:
        companies (list): List of dictionaries containing company information
                          Each dict should have 'name', 'url', and optionally 'extractor'
        email_config (dict): Email configuration for notifications
        summarization_model (str): Model to use for summarization
    """
    monitors = []
    
    for company in companies:
        logger.info(f"Setting up monitor for {company['name']}")
        monitor = PressReleaseMonitor(
            url=company['url'],
            company_name=company['name'],
            extractor_path=company.get('extractor'),
            email_config=email_config,
            summarization_model=summarization_model
        )
        
        # Run an immediate check
        monitor.check_for_updates()
        monitors.append(monitor)
    
    # Schedule daily checks for all companies
    for i, company in enumerate(companies):
        time_offset = i * 5  # Stagger checks by 5 minutes per company
        hour = 9
        minute = time_offset % 60
        hour += time_offset // 60
        time_str = f"{hour:02d}:{minute:02d}"
        
        schedule.every().day.at(time_str).do(monitors[i].check_for_updates)
        logger.info(f"Scheduled daily check for {company['name']} at {time_str}")
    
    # Run the schedule
    logger.info("Starting scheduler for all companies...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Monitor press releases from company websites')
    parser.add_argument('--url', required=False, help='URL of the press release page')
    parser.add_argument('--company', required=False, help='Name of the company')
    parser.add_argument('--extractor', help='Path to custom extractor function')
    parser.add_argument('--time', default="09:00", help='Time to run the daily check (HH:MM)')
    parser.add_argument('--config', help='Path to JSON file with multiple company configurations')
    parser.add_argument('--model', default="llama3.2", help='Ollama model to use for summarization')
    
    args = parser.parse_args()
    
    # Email configuration - update with your details or load from a config file
    EMAIL_CONFIG = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 465,
        'username': 'f.kai.ye03@gmail.com',
        'password': '6866449yfkhh',
        'from': 'f.kai.ye03@gmail.com',
        'to': 'f.kai.ye03@example.com'
    }
    
    # If config file is provided, load multiple companies
    if args.config:
        import json
        try:
            with open(args.config, 'r') as f:
                companies = json.load(f)
            run_multiple_companies(
                companies, 
                email_config=EMAIL_CONFIG,
                summarization_model=args.model
            )
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            sys.exit(1)
    # Otherwise run for a single company
    elif args.url and args.company:
        setup_scheduled_checks(
            url=args.url,
            company_name=args.company,
            time_of_day=args.time,
            extractor_path=args.extractor,
            email_config=EMAIL_CONFIG,
            summarization_model=args.model
        )
        
        # Run the schedule
        logger.info("Starting scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        # Example usage with hardcoded values
        companies = [
            {
                "name": "Thames Water",
                "url": "https://www.thameswater.co.uk/about-us/newsroom/latest-news",
                "extractor": "extractors/thames_water.py"
            }
        ]
        
        # Uncomment to run multiple companies
        # run_multiple_companies(companies, email_config=EMAIL_CONFIG)
        
        # Or run a single company
        setup_scheduled_checks(
            url=companies[0]["url"],
            company_name=companies[0]["name"],
            extractor_path=companies[0]["extractor"],
            email_config=EMAIL_CONFIG,
            summarization_model=args.model
        )
        
        # Run the schedule
        logger.info("Starting scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)