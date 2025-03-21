import requests
import os
from datetime import datetime

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
        
        print(f"Webpage saved to: {filepath}")
        return filepath
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading webpage: {e}")
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
        import trafilatura
        
        with open(filepath, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        extracted_text = trafilatura.extract(html_content)
        return extracted_text
    
    except Exception as e:
        print(f"Error extracting content: {e}")
        return None

# Example usage
if __name__ == "__main__":
    url = "https://www.londoncityairport.com/media-centre/press-releases/london-city-airport-submits-application-to-accommodate-the-a320neo"
    downloaded_file = download_webpage(url)
    
    if downloaded_file:
        content = extract_from_local_file(downloaded_file)
        if content:
            print("\nExtracted content:")
            print("-" * 50)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("-" * 50)
            
            # Optional: Save the extracted content to a text file
            text_filepath = downloaded_file.replace(".html", ".txt")
            with open(text_filepath, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f"Extracted content saved to: {text_filepath}")