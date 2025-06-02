Here's your updated README file, with the "Custom Extractors" section replaced by a manual for your auto extractor generator script.

-----

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
  - [Auto Extractor Generator Manual](#auto-extractor-generator-manual)
  - [Database Structure](#database-structure)
  - [Workflow](#workflow)
  - [Troubleshooting](#troubleshooting)
  - [Examples](#examples)
  - [Security Considerations](https://www.google.com/search?q=%23security-considerations)
  - [Contributing](https://www.google.com/search?q=%23contributing)
  - [License](https://www.google.com/search?q=%23license)
  - [Support](https://www.google.com/search?q=%23support)

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
      ` bash   # Pull the default model   ollama pull llama3.2    `
  - **webpage\_downloader.py**: Required for downloading full article content (referenced but not included in main script)

## Installation

1.  Clone or download the repository
2.  Install Python dependencies:
       `bash    pip install -r requirements.txt    `
3.  Install and configure Ollama
4.  Set up email configuration (see [Email Configuration](https://www.google.com/search?q=%23email-configuration))

## Core Components

### 1\. PressReleaseMonitor Class

The main monitoring engine that handles:

  - Web scraping of press release pages
  - Content extraction using BeautifulSoup
  - Database management
  - Email notifications
  - Content summarization

### 2\. Extractor System

  - **Default Extractor**: Built-in logic that works with common press release page structures
  - **Custom Extractors**: Python modules that define site-specific extraction logic

### 3\. Database Manager

  - SQLite database (`press_releases.db`) stores:
      - Press release metadata
      - Content hashes for duplicate detection
      - Extracted content
      - AI-generated summaries

### 4\. Email Notifier

  - Sends alerts for new press releases
  - Includes AI summaries when available
  - Supports SSL/TLS email servers

### 5\. Content Summarizer

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

1.  Enable 2-factor authentication in your Google account
2.  Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3.  Generate an app-specific password
4.  Use this password in the configuration

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url` | URL of the press release page | Required\* |
| `--company` | Name of the company | Required\* |
| `--extractor` | Path to custom extractor Python file | None (uses default) |
| `--time` | Time for daily checks (HH:MM format) | 09:00 |
| `--config` | Path to multi-company config JSON | None |
| `--model` | Ollama model for summarization | llama3.2 |
| `--email-config` | Path to email configuration JSON | None |
| `--no-email` | Disable email notifications | False |

\*Required unless using `--config` for multiple companies

-----

## Auto Extractor Generator Manual

The `extractor_generator.py` script automates the creation of custom press release extractors using Ollama. This tool analyzes the HTML structure of a given URL and generates a Python function tailored to extract relevant information.

### How it Works

1.  **Fetch Page**: Downloads the HTML content of the specified URL.
2.  **Save HTML (Optional)**: Caches the downloaded HTML for future analysis or debugging.
3.  **Analyze Structure**: Examines the HTML to identify common patterns, such as repeated elements, links, titles, and dates, which often indicate press release listings.
4.  **Generate Prompt**: Constructs a detailed prompt for the Ollama model, including the analysis of the page structure and a sample of the HTML.
5.  **Generate Code**: Calls the Ollama model to generate a Python function (`extract_press_releases`) based on the prompt.
6.  **Save Extractor**: Saves the generated Python code as a `.py` file in the specified output directory.
7.  **Test Extractor (Optional)**: Automatically tests the generated extractor against the original URL to verify its functionality and extract data.

### Usage

To use the auto extractor generator, run the `extractor_generator.py` script from your terminal:

```bash
python extractor_generator.py <URL> [OPTIONS]
```

#### Arguments

  * `<URL>`: The URL of the press release page you want to generate an extractor for. This is a **required positional argument**.

#### Options

| Argument | Description | Default |
| :------- | :---------- | :------ |
| `--model` | Specifies the Ollama model to use for code generation. | `llama3.2` |
| `--output-dir` | Directory where the generated extractor Python file will be saved. | `./extractors` |
| `--html-cache-dir` | Directory to save downloaded HTML pages during the generation process. | `./downloaded_pages/extractor_generation` |
| `--use-cached-html` | Path to a previously downloaded HTML file. If provided, the script will use this file instead of fetching the URL. Useful for debugging or iterative development. | None |
| `--test` | If this flag is present, the script will attempt to test the generated extractor immediately after creation. | False |
| `--no-save` | If this flag is present, the generated code will be printed to the console but not saved to a file. | False |
| `--name` | The filename for the generated extractor (e.g., `company_name_extractor.py`). If not provided, a name will be derived from the URL. | Derived from URL |

### Examples

#### Generate and Save an Extractor

This command will fetch the HTML from `https://example.com/news`, analyze it, generate an extractor named `example_corp.py`, and save it in the `./extractors` directory.

```bash
python extractor_generator.py https://example.com/news --name example_corp.py
```

#### Generate, Save, and Test an Extractor

This command does the same as above but also runs an automated test on the generated extractor to ensure it can successfully pull data from the provided URL.

```bash
python extractor_generator.py https://example.com/news --name example_corp.py --test
```

#### Generate Extractor and Print to Console (without saving)

Useful for quick inspection or if you want to copy-paste the code manually.

```bash
python extractor_generator.py https://example.com/news --no-save
```

#### Use a Different Ollama Model

If you have other Ollama models installed, you can specify them:

```bash
python extractor_generator.py https://example.com/news --name example_corp.py --model llama2
```

#### Regenerate Extractor Using Cached HTML

If you've already run the generator and have a cached HTML file (e.g., in `./downloaded_pages/extractor_generation/example_com_20250601_123456.html`), you can reuse it to regenerate or modify an extractor without refetching the page.

```bash
python extractor_generator.py https://example.com/news \
  --name example_corp_v2.py \
  --use-cached-html ./downloaded_pages/extractor_generation/example_com_20250601_123456.html \
  --test
```

### Output

Upon successful generation and saving, the script will print a confirmation message indicating the path to the saved extractor file. If `--test` is enabled, it will also show the test results, including the number of press releases found and a sample of the extracted titles and links.

### Troubleshooting Generation Issues

  * **"Failed to fetch the page"**: Ensure the URL is correct, accessible, and not blocking automated requests. You might need to check your internet connection or the website's `robots.txt`.
  * **"Error generating code with Ollama"**: Verify that your Ollama server is running and the specified model is installed (`ollama list`).
  * **"No press releases found - extractor may need adjustment" (during test)**: This indicates that the generated extractor couldn't identify press releases using the learned patterns. The website's structure might be too complex or unusual for the AI to infer correctly. In such cases, the generated extractor will serve as a starting point, and you'll need to manually refine it (see the "Custom Extractors" section in the main README for manual extractor creation guidelines).
  * **Generated code is incorrect/incomplete**: The AI might not have perfectly understood the page structure. Review the generated code and compare it to the actual HTML. You can use the `--no-save` flag to quickly inspect the generated code without saving.

-----

## Database Structure

### Tables

#### `press_releases`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| company\_name | TEXT | Company identifier |
| title | TEXT | Press release title |
| link | TEXT | URL to press release |
| summary | TEXT | Brief description |
| date | TEXT | Publication date |
| content\_hash | TEXT | MD5 hash for deduplication |
| first\_seen | TEXT | When first detected |
| last\_checked | TEXT | Last verification time |

#### `article_summaries`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| content\_id | INTEGER | Foreign key to extracted\_content |
| summary | TEXT | AI-generated summary |
| model\_name | TEXT | Ollama model used |
| created\_at | TEXT | Summary creation time |

#### `extracted_content` (created by webpage\_downloader.py)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| press\_release\_id | INTEGER | Foreign key to press\_releases |
| content | TEXT | Full article content |

## Workflow

1.  **Fetch**: Downloads the press release page HTML
2.  **Extract**: Parses HTML to find press releases (using default or custom extractor)
3.  **Compare**: Checks against database for new releases
4.  **Download**: Calls `webpage_downloader.py` to fetch full content
5.  **Summarize**: Generates AI summaries using Ollama
6.  **Notify**: Sends email alerts with summaries
7.  **Schedule**: Waits until next scheduled check

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

## Support

For issues or questions:

1.  Check the troubleshooting section
2.  Review the log file for detailed error messages
3.  Ensure all dependencies are correctly installed
4.  Verify website structure hasn't changed for custom extractors