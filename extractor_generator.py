import requests
from bs4 import BeautifulSoup
import ollama
import os
import re
import logging
from urllib.parse import urlparse
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extractor_generator')

class ExtractorGenerator:
    def __init__(self, model="llama3.2", html_cache_dir="../downloaded_pages/extractor_generation"):
        """
        Initialize the extractor generator.
        
        Args:
            model (str): Ollama model to use for code generation
            html_cache_dir (str): Directory to save downloaded HTML pages
        """
        self.client = ollama.Client()
        self.model = model
        self.html_cache_dir = html_cache_dir
        
    def save_html(self, url, html_text):
        """
        Save the downloaded HTML to disk.
        
        Args:
            url (str): URL of the page
            html_text (str): HTML content
            
        Returns:
            str: Path to saved file
        """
        # Create directory if it doesn't exist
        os.makedirs(self.html_cache_dir, exist_ok=True)
        
        # Generate filename from URL
        domain = urlparse(url).netloc.replace('www.', '')
        filename = re.sub(r'[^\w\s-]', '', domain)
        filename = re.sub(r'[-\s]+', '_', filename)
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename}_{timestamp}.html"
        
        filepath = os.path.join(self.html_cache_dir, filename)
        
        # Save HTML with metadata
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"<!-- URL: {url} -->\n")
            f.write(f"<!-- Downloaded: {datetime.now().isoformat()} -->\n")
            f.write(html_text)
        
        logger.info(f"HTML saved to: {filepath}")
        return filepath
    
    def load_cached_html(self, filepath):
        """
        Load HTML from a cached file.
        
        Args:
            filepath (str): Path to the HTML file
            
        Returns:
            tuple: (BeautifulSoup object, html_text)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_text = f.read()
            soup = BeautifulSoup(html_text, 'html.parser')
            return soup, html_text
        except Exception as e:
            logger.error(f"Error loading cached HTML: {e}")
            return None, None
    
    def fetch_page(self, url):
        """
        Fetch and parse the HTML page.
        
        Args:
            url (str): URL of the press release page
            
        Returns:
            tuple: (BeautifulSoup object, response text)
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup, response.text
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None, None
    
    def analyze_page_structure(self, soup, url):
        """
        Analyze the HTML structure to identify press release patterns.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            url (str): Original URL
            
        Returns:
            dict: Analysis results
        """
        analysis = {
            'url': url,
            'base_url': '/'.join(url.split('/')[:3]),
            'potential_containers': [],
            'link_patterns': [],
            'date_patterns': [],
            'title_patterns': [],
            'common_classes': {},
            'sample_items': []
        }
        
        # Find potential press release containers
        # Look for repeated structures with links
        all_links = soup.find_all('a', href=True)
        
        # Group links by their parent's class
        parent_classes = {}
        for link in all_links:
            if link.parent and link.parent.get('class'):
                parent_class = ' '.join(link.parent.get('class'))
                if parent_class not in parent_classes:
                    parent_classes[parent_class] = []
                parent_classes[parent_class].append(link)
        
        # Find classes with multiple similar links (likely press releases)
        for class_name, links in parent_classes.items():
            if len(links) >= 3:  # At least 3 similar items
                analysis['potential_containers'].append({
                    'class': class_name,
                    'count': len(links),
                    'parent_tag': links[0].parent.name
                })
        
        # Analyze article/news related elements
        article_selectors = [
            'article', '.article', '.news-item', '.press-release',
            '[class*="article"]', '[class*="news"]', '[class*="press"]',
            '.post', '.entry', '.item', '[class*="post"]', '[class*="entry"]'
        ]
        
        for selector in article_selectors:
            items = soup.select(selector)
            if len(items) >= 2:
                # Sample the first few items
                for item in items[:3]:
                    sample = {
                        'selector': selector,
                        'html_sample': str(item)[:500],  # First 500 chars
                        'links': [a.get('href') for a in item.find_all('a', href=True)][:2],
                        'headings': [h.get_text(strip=True) for h in item.find_all(['h1', 'h2', 'h3', 'h4'])][:2],
                        'dates': self._find_dates(item)
                    }
                    if sample['links'] or sample['headings']:
                        analysis['sample_items'].append(sample)
        
        # Find common class patterns
        all_elements = soup.find_all(class_=True)
        class_counts = {}
        for elem in all_elements:
            for class_name in elem.get('class', []):
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        # Filter to relevant classes
        relevant_keywords = ['article', 'news', 'press', 'post', 'title', 'date', 'link', 'item', 'entry']
        for class_name, count in class_counts.items():
            if count >= 3 and any(keyword in class_name.lower() for keyword in relevant_keywords):
                analysis['common_classes'][class_name] = count
        
        return analysis
    
    def _find_dates(self, element):
        """Find date-like patterns in an element."""
        dates = []
        
        # Look for time tags
        time_tags = element.find_all('time')
        dates.extend([t.get_text(strip=True) for t in time_tags])
        
        # Look for date patterns in text
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}\s+\d{2}:\d{2}'
        ]
        
        text = element.get_text()
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches[:2])  # Limit to first 2 matches
        
        return dates[:3]  # Return up to 3 dates
    
    def generate_extractor_prompt(self, analysis, html_sample):
        """
        Generate a prompt for Ollama to create the extractor function.
        
        Args:
            analysis (dict): Page structure analysis
            html_sample (str): Sample HTML from the page
            
        Returns:
            str: Prompt for Ollama
        """
        prompt = f"""You are an expert Python developer specializing in web scraping with BeautifulSoup.

I need you to create a Python function that extracts press releases from a company website.
The function MUST be named 'extract_press_releases' and follow this exact signature:

def extract_press_releases(soup, base_url):
    '''Extract press releases from the parsed HTML.
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        base_url (str): Base URL for resolving relative links
        
    Returns:
        list: List of dictionaries containing press release information
    '''

Here's the analysis of the website structure:
URL: {analysis['url']}
Base URL: {analysis['base_url']}

Common classes found: {json.dumps(analysis['common_classes'], indent=2)}

Sample items found:
{json.dumps(analysis['sample_items'], indent=2)}

Here's a sample of the HTML structure:
{html_sample}

Requirements for the function:
1. Find all press release items on the page
2. For each item, extract:
   - title (required): The headline/title of the press release
   - link (required): The URL to the full press release
   - date (optional): The publication date
   - summary (optional): A brief description if available
   - content_hash (required): MD5 hash of title|link|summary|date for deduplication

3. Handle relative URLs by prepending base_url
4. Use appropriate error handling and logging
5. Import necessary modules (hashlib, datetime, logging, re)
6. Create the content_hash using: hashlib.md5(content.encode()).hexdigest()

Based on the HTML structure, identify the correct selectors for finding press release items.
Look for patterns in classes, IDs, or HTML structure that indicate press releases.

Generate ONLY the Python code for the extractor function, including necessary imports at the top.
Add helpful comments explaining the selectors used.
Make the code robust to handle missing elements gracefully.

Start your response with the imports and the function definition."""
        
        return prompt
    
    def generate_extractor_code(self, url, use_cached_html=None):
        """
        Generate extractor code for a given press release page.
        
        Args:
            url (str): URL of the press release page
            use_cached_html (str): Path to cached HTML file (optional)
            
        Returns:
            tuple: (success, code_or_error, html_filepath)
        """
        logger.info(f"Generating extractor for: {url}")
        
        # Use cached HTML if provided
        if use_cached_html and os.path.exists(use_cached_html):
            logger.info(f"Using cached HTML from: {use_cached_html}")
            soup, html_text = self.load_cached_html(use_cached_html)
            html_filepath = use_cached_html
        else:
            # Fetch the page
            soup, html_text = self.fetch_page(url)
            if not soup:
                return False, "Failed to fetch the page", None
            
            # Save the HTML
            html_filepath = self.save_html(url, html_text)
        
        # Analyze the structure
        logger.info("Analyzing page structure...")
        analysis = self.analyze_page_structure(soup, url)
        
        # Get a representative HTML sample
        html_sample = ""
        if analysis['sample_items']:
            html_sample = analysis['sample_items'][0].get('html_sample', '')
        else:
            # Fallback: get first 2000 chars of body
            body = soup.find('body')
            if body:
                html_sample = str(body)[:2000]
        
        # Generate the prompt
        prompt = self.generate_extractor_prompt(analysis, html_sample)
        
        # Call Ollama to generate the code
        logger.info("Generating extractor code with Ollama...")
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt
            )
            
            code = response['response']
            
            # Clean up the response (remove any markdown formatting)
            code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
            code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
            
            # Add header comment
            company_name = urlparse(url).netloc.replace('www.', '').split('.')[0].title()
            header = f'''"""
{company_name} Press Release Extractor
{'=' * (len(company_name) + 24)}
This module provides a custom extractor function for {company_name}'s press release page.
Generated automatically from: {url}
HTML snapshot saved at: {html_filepath}
Generated on: {datetime.now().isoformat()}
"""

'''
            final_code = header + code.strip()
            
            return True, final_code, html_filepath
            
        except Exception as e:
            logger.error(f"Error generating code with Ollama: {e}")
            return False, str(e), html_filepath
    
    def save_extractor(self, code, url, extractor_name, output_dir="../extractors"):
        """
        Save the generated extractor code to a file.
        
        Args:
            code (str): Generated Python code
            url (str): Original URL (used for naming)
            output_dir (str): Directory to save extractors
            
        Returns:
            str: Path to saved file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, extractor_name)
        
        # Save the code
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        
        logger.info(f"Extractor saved to: {filepath}")
        return filepath
    
    def test_extractor(self, extractor_path, url):
        """
        Test the generated extractor to ensure it works.
        
        Args:
            extractor_path (str): Path to the extractor file
            url (str): URL to test against
            
        Returns:
            tuple: (success, results_or_error)
        """
        try:
            # Import the extractor module
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_extractor", extractor_path)
            extractor_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(extractor_module)
            
            # Fetch the page
            soup, _ = self.fetch_page(url)
            if not soup:
                return False, "Failed to fetch page for testing"
            
            base_url = '/'.join(url.split('/')[:3])
            
            # Call the extractor function
            results = extractor_module.extract_press_releases(soup, base_url)
            
            logger.info(f"Test results: Found {len(results)} press releases")
            
            # Validate results
            if not results:
                return False, "No press releases found - extractor may need adjustment"
            
            # Check if results have required fields
            for i, item in enumerate(results[:3]):  # Check first 3
                if not item.get('title') or not item.get('link'):
                    return False, f"Item {i} missing required fields (title/link)"
            
            return True, results
            
        except Exception as e:
            logger.error(f"Error testing extractor: {e}")
            import traceback
            return False, traceback.format_exc()


def main():
    """Main function to run the extractor generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate press release extractors automatically')
    parser.add_argument('url', help='URL of the press release page')
    parser.add_argument('--model', default='llama3.2', help='Ollama model to use')
    parser.add_argument('--output-dir', default='./extractors', help='Directory to save extractors')
    parser.add_argument('--html-cache-dir', default='./downloaded_pages/extractor_generation', 
                        help='Directory to save downloaded HTML')
    parser.add_argument('--use-cached-html', help='Path to previously downloaded HTML file')
    parser.add_argument('--test', action='store_true', help='Test the generated extractor')
    parser.add_argument('--no-save', action='store_true', help='Print code without saving')
    parser.add_argument('--name', help='name of the extractor')
    
    args = parser.parse_args()
    
    # Create generator
    generator = ExtractorGenerator(model=args.model, html_cache_dir=args.html_cache_dir)
    
    # Generate the extractor
    success, code_or_error, html_filepath = generator.generate_extractor_code(
        args.url, 
        use_cached_html=args.use_cached_html
    )
    
    if not success:
        logger.error(f"Failed to generate extractor: {code_or_error}")
        return 1
    
    code = code_or_error
    
    if html_filepath:
        print(f"\n📄 HTML saved to: {html_filepath}")
    
    if args.no_save:
        # Just print the code
        print("\n" + "="*80)
        print("GENERATED EXTRACTOR CODE:")
        print("="*80 + "\n")
        print(code)
        return 0
    
    # Save the extractor
    filepath = generator.save_extractor(code, args.url, args.name, args.output_dir)
    print(f"\n✓ Extractor saved to: {filepath}")
    
    # Test if requested
    if args.test:
        print("\nTesting generated extractor...")
        test_success, test_results = generator.test_extractor(filepath, args.url)
        
        if test_success:
            print(f"✓ Test successful! Found {len(test_results)} press releases:")
            for i, item in enumerate(test_results[:5], 1):
                print(f"  {i}. {item['title'][:60]}...")
                print(f"     Link: {item['link']}")
                if item.get('date'):
                    print(f"     Date: {item['date']}")
                print()
        else:
            print(f"✗ Test failed: {test_results}")
            print("\nYou may need to manually adjust the generated extractor.")
    
    return 0


if __name__ == "__main__":
    exit(main())