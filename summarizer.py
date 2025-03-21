import ollama
import os
import sqlite3
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("article_summarizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('article_summarizer')

def setup_summaries_table(conn):
    """
    Set up the summaries table in the database if it doesn't exist.
    
    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()
    
    # Create summaries table
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
    logger.info("Summaries table setup complete")

def get_unsummarized_articles(conn, company_name=None, limit=None):
    """
    Get articles that haven't been summarized yet.
    
    Args:
        conn: SQLite database connection
        company_name: Optional filter by company name
        limit: Optional limit on number of articles to return
        
    Returns:
        List of article dictionaries with id, title, content, etc.
    """
    cursor = conn.cursor()
    
    # Build query
    query = '''
    SELECT ec.id, ec.press_release_id, ec.company_name, ec.title, ec.content 
    FROM extracted_content ec
    LEFT JOIN article_summaries summ ON ec.id = summ.content_id
    WHERE summ.id IS NULL
    '''
    
    params = []
    
    # Add company filter if specified
    if company_name:
        query += " AND ec.company_name LIKE ?"
        params.append(f"%{company_name}%")
    
    # Add order by
    query += " ORDER BY ec.extraction_date DESC"
    
    # Add limit if specified
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    # Execute query
    cursor.execute(query, params)
    
    # Convert to list of dictionaries
    columns = [column[0] for column in cursor.description]
    articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return articles

def summarize_with_ollama(text, model_name="llama3.2"):
    """
    Summarize text using Ollama API.
    
    Args:
        text: Text to summarize
        model_name: Ollama model to use
        
    Returns:
        Generated summary
    """
    client = ollama.Client()
    
    # Create prompt for summarization
    prompt = f"Please summarize the following article concisely into bullet points:\n\n{text}"
    
    # Generate summary using Ollama
    response = client.generate(model=model_name, prompt=prompt)
    return response.response

def save_summary(conn, content_id, summary, model_name):
    """
    Save a summary to the database.
    
    Args:
        conn: SQLite database connection
        content_id: ID of the extracted_content entry
        summary: Generated summary text
        model_name: Name of the model used for summarization
    """
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute(
        'INSERT INTO article_summaries (content_id, summary, model_name, created_at) VALUES (?, ?, ?, ?)',
        (content_id, summary, model_name, current_time)
    )
    
    conn.commit()
    return cursor.lastrowid

def summarize_database_articles(database_path, model_name="llama3.2", company_name=None, limit=None):
    """
    Summarize articles from the database and save summaries back to the database.
    
    Args:
        database_path: Path to the SQLite database
        model_name: Ollama model to use for summarization
        company_name: Optional filter by company name
        limit: Optional limit on number of articles to process
    """
    # Connect to the database
    conn = sqlite3.connect(database_path)
    
    # Set up summaries table
    setup_summaries_table(conn)
    
    # Get articles that haven't been summarized yet
    articles = get_unsummarized_articles(conn, company_name, limit)
    
    logger.info(f"Found {len(articles)} articles to summarize")
    
    # Process each article
    for i, article in enumerate(articles, 1):
        article_id = article['id']
        title = article['title']
        content = article['content']
        
        logger.info(f"[{i}/{len(articles)}] Processing: {title} (ID: {article_id})")
        
        try:
            # Generate summary
            summary = summarize_with_ollama(content, model_name)
            
            # Save summary to database
            summary_id = save_summary(conn, article_id, summary, model_name)
            
            logger.info(f"Summary saved with ID: {summary_id}")
            
        except Exception as e:
            logger.error(f"Error processing article ID {article_id}: {str(e)}")
    
    conn.close()
    logger.info("Summarization complete!")

def list_summaries(database_path, company_name=None, limit=10):
    """
    List existing summaries in the database.
    
    Args:
        database_path: Path to the SQLite database
        company_name: Optional filter by company name
        limit: Maximum number of summaries to show
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Build query
    query = '''
    SELECT 
        summ.id AS summary_id,
        ec.title,
        ec.company_name,
        summ.created_at,
        summ.model_name,
        summ.summary
    FROM article_summaries summ
    JOIN extracted_content ec ON summ.content_id = ec.id
    '''
    
    params = []
    
    # Add company filter if specified
    if company_name:
        query += " WHERE ec.company_name LIKE ?"
        params.append(f"%{company_name}%")
    
    # Add order by and limit
    query += " ORDER BY summ.created_at DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    cursor.execute(query, params)
    
    # Fetch and display results
    results = cursor.fetchall()
    
    if not results:
        print("No summaries found.")
        return
    
    print(f"\nFound {len(results)} summaries:")
    print("-" * 80)
    
    for row in results:
        summary_id, title, company, created_at, model, summary = row
        
        print(f"ID: {summary_id} | {title} ({company})")
        print(f"Generated: {created_at} | Model: {model}")
        print("-" * 40)
        print(summary[:500] + "..." if len(summary) > 500 else summary)
        print("-" * 80)
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Summarize articles from the database')
    
    # Command subparsers
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Generate summaries for unsummarized articles')
    summarize_parser.add_argument('--db', default='press_releases.db', help='Path to the database file')
    summarize_parser.add_argument('--model', default='llama3.2', help='Ollama model to use')
    summarize_parser.add_argument('--company', help='Filter by company name')
    summarize_parser.add_argument('--limit', type=int, help='Limit number of articles to process')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List existing summaries')
    list_parser.add_argument('--db', default='press_releases.db', help='Path to the database file')
    list_parser.add_argument('--company', help='Filter by company name')
    list_parser.add_argument('--limit', type=int, default=10, help='Maximum number of summaries to show')
    
    args = parser.parse_args()
    
    # Default to summarize if no command specified
    if not args.command:
        args.command = 'summarize'
    
    if args.command == 'summarize':
        summarize_database_articles(
            args.db,
            model_name=args.model,
            company_name=args.company,
            limit=args.limit
        )
    elif args.command == 'list':
        list_summaries(
            args.db,
            company_name=args.company,
            limit=args.limit
        )

if __name__ == "__main__":
    main()