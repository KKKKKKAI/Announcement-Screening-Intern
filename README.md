
# Press Release Monitor
## Building an agentic intern to help monitoring company's news relating to interest of transactions
A Python-based automated monitoring system that tracks company press releases, sends email notifications for new releases, and generates AI-powered summaries using Ollama.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Core Components](#core-components)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Custom Extractors](#custom-extractors)
- [Database Structure](#database-structure)
- [Troubleshooting](#troubleshooting)

## Features

- **Automated Monitoring**: Continuously monitors company press release pages
- **Multi-Company Support**: Monitor multiple companies simultaneously
- **Custom Extractors**: Define custom parsing logic for different website structures
- **Email Notifications**: Get alerts when new press releases are detected
- **AI Summarization**: Generate concise summaries using Ollama models
- **Content Archival**: Download and store full press release content
- **Scheduled Checks**: Run daily checks at specified times
- **Database Storage**: SQLite database for tracking press releases

## Requirements

### Python Dependencies
```bash
pip install requests beautifulsoup4 schedule ollama
```

### External Requirements
- **Ollama**: Install from [ollama.ai](https://ollama.ai) for AI summarization
  ```bash
  # Pull the default model
  ollama pull llama3.2
  ```
- **webpage_downloader.py**: Required for downloading full article content (referenced but not included in main script)

## Installation

1. Clone or download the repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install and configure Ollama
4. Set up email configuration (see [Email Configuration](#email-configuration))

## Core Components

### 1. PressReleaseMonitor Class
The main monitoring engine that handles:
- Web scraping of press release pages
- Content extraction using BeautifulSoup
- Database management
- Email notifications
- Content summarization

### 2. Extractor System
- **Default Extractor**: Built-in logic that works with common press release page structures
- **Custom Extractors**: Python modules that define site-specific extraction logic

### 3. Database Manager
- SQLite database (`press_releases.db`) stores:
  - Press release metadata
  - Content hashes for duplicate detection
  - Extracted content
  - AI-generated summaries

### 4. Email Notifier
- Sends alerts for new press releases
- Includes AI summaries when available
- Supports SSL/TLS email servers

### 5. Content Summarizer
- Uses Ollama for AI-powered summarization
- Caches summaries to avoid regeneration
- Configurable model selection

## Usage Guide

### Basic Usage

#### Monitor a Single Company
```bash
python press_release_monitor.py \
  --url "https://example.com/news" \
  --company "Example Corp"
```

#### Monitor with Custom Extractor
```bash
python press_release_monitor.py \
  --url "https://example.com/news" \
  --company "Example Corp" \
  --extractor "extractors/example_extractor.py"
```

#### Schedule Daily Checks
```bash
python press_release_monitor.py \
  --url "https://example.com/news" \
  --company "Example Corp" \
  --time "09:00"
```

#### Disable Email Notifications
```bash
python press_release_monitor.py \
  --url "https://example.com/news" \
  --company "Example Corp" \
  --no-email
```

### Advanced Usage

#### Monitor Multiple Companies
Create a `companies.json` file:
```json
[
  {
    "name": "Company A",
    "url": "https://companya.com/press",
    "extractor": "extractors/company_a.py"
  },
  {
    "name": "Company B",
    "url": "https://companyb.com/news"
  }
]
```

Run with:
```bash
python press_release_monitor.py --config companies.json
```

#### Use Different Ollama Model
```bash
python press_release_monitor.py \
  --url "https://example.com/news" \
  --company "Example Corp" \
  --model "llama2"
```

## Configuration

### Email Configuration

#### Interactive Setup
Run the script without email config to be prompted:
```bash
python press_release_monitor.py --url "..." --company "..."
```

#### Configuration File
Create `email_config.json`:
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 465,
  "username": "your.email@gmail.com",
  "password": "your-app-password",
  "from": "your.email@gmail.com",
  "to": "recipient@example.com"
}
```

Use with:
```bash
python press_release_monitor.py \
  --url "..." \
  --company "..." \
  --email-config email_config.json
```

### Gmail App Password Setup
1. Enable 2-factor authentication in your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app-specific password
4. Use this password in the configuration

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url` | URL of the press release page | Required* |
| `--company` | Name of the company | Required* |
| `--extractor` | Path to custom extractor Python file | None (uses default) |
| `--time` | Time for daily checks (HH:MM format) | 09:00 |
| `--config` | Path to multi-company config JSON | None |
| `--model` | Ollama model for summarization | llama3.2 |
| `--email-config` | Path to email configuration JSON | None |
| `--no-email` | Disable email notifications | False |

*Required unless using `--config` for multiple companies

## Custom Extractors

### Creating a Custom Extractor

Custom extractors handle sites with unique structures. Create a Python file in the `extractors/` directory:

```python
# extractors/example_site.py

def extract_press_releases(soup, base_url):
    """
    Extract press releases from the parsed HTML.
    
    Args:
        soup (BeautifulSoup): Parsed HTML of the page
        base_url (str): Base URL for resolving relative links
        
    Returns:
        list: List of dictionaries with press release info
    """
    releases = []
    
    # Find all press release items (customize selector)
    items = soup.select('.press-release-item')
    
    for item in items:
        title = item.select_one('.title').get_text(strip=True)
        link = item.select_one('a')['href']
        
        # Handle relative URLs
        if link.startswith('/'):
            link = base_url + link
            
        # Extract optional fields
        date = item.select_one('.date')
        date_text = date.get_text(strip=True) if date else ''
        
        summary = item.select_one('.summary')
        summary_text = summary.get_text(strip=True) if summary else ''
        
        # Create content hash for duplicate detection
        import hashlib
        content = f"{title}|{link}|{summary_text}|{date_text}"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        releases.append({
            'title': title,
            'link': link,
            'summary': summary_text,
            'date': date_text,
            'content_hash': content_hash
        })
    
    return releases
```

### Extractor Requirements
- Must contain a function named `extract_press_releases`
- Must accept `soup` (BeautifulSoup object) and `base_url` (string) parameters
- Must return a list of dictionaries with at least:
  - `title`: Press release title
  - `link`: Full URL to the press release
  - `content_hash`: MD5 hash for duplicate detection
- Optional fields:
  - `summary`: Brief description
  - `date`: Publication date

## Database Structure

### Tables

#### press_releases
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| company_name | TEXT | Company identifier |
| title | TEXT | Press release title |
| link | TEXT | URL to press release |
| summary | TEXT | Brief description |
| date | TEXT | Publication date |
| content_hash | TEXT | MD5 hash for deduplication |
| first_seen | TEXT | When first detected |
| last_checked | TEXT | Last verification time |

#### article_summaries
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| content_id | INTEGER | Foreign key to extracted_content |
| summary | TEXT | AI-generated summary |
| model_name | TEXT | Ollama model used |
| created_at | TEXT | Summary creation time |

#### extracted_content (created by webpage_downloader.py)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| press_release_id | INTEGER | Foreign key to press_releases |
| content | TEXT | Full article content |

## Workflow

1. **Fetch**: Downloads the press release page HTML
2. **Extract**: Parses HTML to find press releases (using default or custom extractor)
3. **Compare**: Checks against database for new releases
4. **Download**: Calls `webpage_downloader.py` to fetch full content
5. **Summarize**: Generates AI summaries using Ollama
6. **Notify**: Sends email alerts with summaries
7. **Schedule**: Waits until next scheduled check

## Troubleshooting

### Common Issues

#### No Press Releases Found
- Check if the website structure has changed
- Create a custom extractor for the specific site
- Verify the URL is correct and accessible

#### Email Not Sending
- Verify SMTP settings are correct
- For Gmail, ensure you're using an app password
- Check firewall/network restrictions
- Enable "less secure apps" or use OAuth2

#### Ollama Errors
- Ensure Ollama is running: `ollama serve`
- Check if the model is installed: `ollama list`
- Pull the model if missing: `ollama pull llama3.2`

#### Database Errors
- Check file permissions for `press_releases.db`
- Delete the database file to start fresh
- Ensure sufficient disk space

### Debug Mode
Enable detailed logging by checking the log file:
```bash
tail -f press_release_monitor.log
```

### Testing Extractors
Test a custom extractor independently:
```python
from bs4 import BeautifulSoup
import requests
from extractors.your_extractor import extract_press_releases

url = "https://example.com/news"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
base_url = "https://example.com"

releases = extract_press_releases(soup, base_url)
print(f"Found {len(releases)} releases")
for release in releases:
    print(f"- {release['title']}")
```

## Examples

### Example 1: Tech Company Monitor
```bash
python press_release_monitor.py \
  --url "https://investor.techcorp.com/press-releases" \
  --company "TechCorp" \
  --time "08:00" \
  --email-config email_config.json
```

### Example 2: Financial Services Multi-Monitor
```json
// financial_companies.json
[
  {
    "name": "Big Bank",
    "url": "https://bigbank.com/media/press-releases",
    "extractor": "extractors/bigbank.py"
  },
  {
    "name": "Insurance Co",
    "url": "https://insurance.com/news"
  },
  {
    "name": "Investment Firm",
    "url": "https://investments.com/press"
  }
]
```

```bash
python press_release_monitor.py \
  --config financial_companies.json \
  --model "llama2:13b" \
  --email-config email_config.json
```

## Security Considerations

- Store `email_config.json` securely with restricted permissions
- Use app passwords instead of regular passwords
- Consider environment variables for sensitive data
- Regularly update dependencies for security patches
- Be mindful of rate limiting on target websites

## Contributing

When contributing custom extractors:
1. Test thoroughly with the target website
2. Handle edge cases (missing elements, different layouts)
3. Include comments explaining site-specific logic
4. Ensure the extractor fails gracefully

## License

[Add your license information here]

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the log file for detailed error messages
3. Ensure all dependencies are correctly installed
4. Verify website structure hasn't changed for custom extractors