import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import time
import hashlib
import logging
import smtplib
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
    def __init__(self, url, database_path="press_releases.db", email_config=None):
        """
        Initialize the press release monitor.
        
        Args:
            url (str): URL of the press release page to monitor
            database_path (str): Path to the SQLite database
            email_config (dict): Configuration for email notifications
        """
        self.url = url
        self.database_path = database_path
        self.email_config = email_config
        self.setup_database()
        
    def setup_database(self):
        """Set up the SQLite database to store press release data."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS press_releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            summary TEXT,
            date TEXT,
            content_hash TEXT,
            first_seen TEXT,
            last_checked TEXT
        )
        ''')
        
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
        Extract press releases from the parsed HTML.
        
        This is a generic implementation. You'll need to customize this method
        for the specific website structure you're monitoring.
        """
        releases = []
        
        # This is a generic implementation - adjust the selectors for your specific website
        # Example for a common structure:
        try:
            # Find press release container (adjust these selectors for the specific site)
            press_items = soup.select('.press-release-item, .news-item, article, .press-release')
            
            if not press_items:
                # Alternative selectors if the above don't work
                press_items = soup.select('.news-listing article, .press-releases li, .news-container .item')
            
            if not press_items:
                # If still not found, try to look for a list of news items
                press_items = soup.find_all('div', class_=lambda c: c and ('news' in c.lower() or 'press' in c.lower()))
            
            for item in press_items:
                # Try to extract title and link
                title_element = item.select_one('h2, h3, .title, a strong')
                link_element = item.select_one('a')
                date_element = item.select_one('.date, time, .published, .timestamp')
                summary_element = item.select_one('.summary, .excerpt, .description, p')
                
                if title_element and link_element:
                    title = title_element.get_text(strip=True)
                    link = link_element['href']
                    
                    # Handle relative URLs
                    if link.startswith('/'):
                        base_url = '/'.join(self.url.split('/')[:3])  # Extract base URL
                        link = base_url + link
                    
                    # Extract date if available
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
        
        return releases
    
    def save_new_releases(self, releases):
        """Save new press releases to the database and return new ones."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        new_releases = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for release in releases:
            # Check if this release exists
            cursor.execute(
                "SELECT id FROM press_releases WHERE link = ? OR content_hash = ?", 
                (release['link'], release['content_hash'])
            )
            
            existing = cursor.fetchone()
            
            if not existing:
                # This is a new release
                cursor.execute('''
                INSERT INTO press_releases (title, link, summary, date, content_hash, first_seen, last_checked)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    release['title'],
                    release['link'],
                    release['summary'],
                    release['date'],
                    release['content_hash'],
                    current_time,
                    current_time
                ))
                new_releases.append(release)
            else:
                # Update last_checked timestamp
                cursor.execute(
                    "UPDATE press_releases SET last_checked = ? WHERE link = ?",
                    (current_time, release['link'])
                )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Found {len(new_releases)} new press releases")
        return new_releases
    
    def send_email_notification(self, new_releases):
        """Send email notification for new press releases."""
        if not self.email_config or not new_releases:
            return
        
        try:
            msg = EmailMessage()
            msg['Subject'] = f"[Press Release Alert] {len(new_releases)} New Press Releases"
            msg['From'] = self.email_config['from']
            msg['To'] = self.email_config['to']
            
            content = "New press releases detected:\n\n"
            for idx, release in enumerate(new_releases, 1):
                content += f"{idx}. {release['title']}\n"
                content += f"   Date: {release['date']}\n"
                content += f"   Link: {release['link']}\n"
                if release['summary']:
                    content += f"   Summary: {release['summary']}\n"
                content += "\n"
            
            msg.set_content(content)
            
            with smtplib.SMTP_SSL(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
                
            logger.info("Email notification sent successfully")
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    def check_for_updates(self):
        """Main function to check for updates."""
        logger.info(f"Checking for updates at {self.url}")
        
        soup = self.fetch_press_releases()
        if not soup:
            return
        
        releases = self.extract_press_releases(soup)
        new_releases = self.save_new_releases(releases)
        
        if new_releases:
            logger.info(f"Found {len(new_releases)} new press releases")
            for release in new_releases:
                logger.info(f"New release: {release['title']} - {release['link']}")
            
            if self.email_config:
                self.send_email_notification(new_releases)
        else:
            logger.info("No new press releases found")
        
        return new_releases

def run_daily_check(url, email_config=None):
    """Run the press release check once."""
    monitor = PressReleaseMonitor(url, email_config=email_config)
    return monitor.check_for_updates()

def setup_scheduled_checks(url, time_of_day="09:00", email_config=None):
    """Set up scheduled daily checks."""
    logger.info(f"Setting up scheduled checks for {url} at {time_of_day} daily")
    
    monitor = PressReleaseMonitor(url, email_config=email_config)
    
    def job():
        monitor.check_for_updates()
    
    schedule.every().day.at(time_of_day).do(job)
    
    logger.info("Starting scheduler...")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Example usage
    COMPANY_URL = "https://example.com/press-releases"
    
    # Optional: Email configuration
    EMAIL_CONFIG = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 465,
        'username': 'your_email@gmail.com',
        'password': 'your_app_password',
        'from': 'your_email@gmail.com',
        'to': 'recipient@example.com'
    }
    
    # Uncomment to run once
    # run_daily_check(COMPANY_URL, email_config=EMAIL_CONFIG)
    
    # Uncomment to set up scheduled checks
    setup_scheduled_checks(COMPANY_URL, time_of_day="09:00", email_config=EMAIL_CONFIG)