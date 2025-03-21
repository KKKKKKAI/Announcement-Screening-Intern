"""
Thames Water Press Release Extractor
------------------------------------------
This module provides a custom extractor function for Thames Water's press release page.
"""

import hashlib
from datetime import datetime
import logging
import re

logger = logging.getLogger('press_release_monitor')

def extract_press_releases(soup, base_url):
    """
    Extract press releases from the Thames Water press releases page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        base_url (str): Base URL for resolving relative links
        
    Returns:
        list: List of dictionaries containing press release information
    """
    releases = []
    
    try:
        # Find press release items using Thames Water specific selectors
        press_items = soup.select('a.Article-module__article__lWN7y')
        
        logger.info(f"Found {len(press_items)} press release items")
        
        for item in press_items:
            # Extract article URL
            link = item.get('href', '')
            
            # Extract title
            title_element = item.select_one('h3.Typography-module__heading-4__exIrU')
            
            # Extract date/time
            date_element = item.select_one('time')
            
            # Extract summary
            summary_element = item.select_one('div.BasicHtml-module__main__3BwiX p')
            
            if title_element and link:
                title = title_element.get_text(strip=True)
                
                # Handle relative URLs
                if link.startswith('/'):
                    link = base_url + link
                
                # Extract date if available, or use current date
                date = date_element.get_text(strip=True) if date_element else datetime.now().strftime('%Y-%m-%d')
                
                # Format date to be consistent (if possible)
                try:
                    # Try to parse various date formats
                    if re.match(r'\d{2}/\d{2} \d{2}:\d{2}', date):
                        # Format: "20/03 13:30"
                        day, month = date.split(' ')[0].split('/')
                        # Assuming current year since only day/month is provided
                        year = datetime.now().year
                        date = f"{year}-{month}-{day}"
                except Exception:
                    # Keep original date format if parsing fails
                    pass
                
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
        # Print the traceback for better debugging
        import traceback
        logger.error(traceback.format_exc())
    
    return releases