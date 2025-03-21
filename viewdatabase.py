import sqlite3
import sys
import os
from datetime import datetime
import pandas as pd
from tabulate import tabulate

def view_database(database_path="press_releases.db", limit=None, output_format="table"):
    """
    View all items in the press releases database.
    
    Args:
        database_path (str): Path to the SQLite database
        limit (int, optional): Limit the number of records to display
        output_format (str): Format to display results ("table", "csv", "json")
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        
        # Create a query with optional limit
        query = "SELECT * FROM press_releases ORDER BY first_seen DESC"
        if limit:
            query += f" LIMIT {limit}"
            
        # Load data into a DataFrame for easier formatting
        df = pd.read_sql_query(query, conn)
        
        # Close the connection
        conn.close()
        
        if len(df) == 0:
            print("No records found in the database.")
            return
        
        # Format the output based on preference
        if output_format == "json":
            print(df.to_json(orient="records", indent=2))
        elif output_format == "csv":
            print(df.to_csv(index=False))
        else:  # Default to table
            # Limit long fields for better display
            for col in ['title', 'summary', 'link']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: (x[:60] + '...') if isinstance(x, str) and len(x) > 60 else x)
            
            # Convert to table format
            print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
        
        print(f"\nTotal records: {len(df)}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def search_database(search_term, database_path="press_releases.db", output_format="table"):
    """
    Search for specific terms in the press releases database.
    
    Args:
        search_term (str): Term to search for in title or summary
        database_path (str): Path to the SQLite database
        output_format (str): Format to display results ("table", "csv", "json")
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        
        # Create a search query
        query = """
        SELECT * FROM press_releases 
        WHERE title LIKE ? OR summary LIKE ? OR link LIKE ?
        ORDER BY first_seen DESC
        """
        search_param = f"%{search_term}%"
        
        # Load data into a DataFrame
        df = pd.read_sql_query(query, conn, params=(search_param, search_param, search_param))
        
        # Close the connection
        conn.close()
        
        if len(df) == 0:
            print(f"No records found matching '{search_term}'.")
            return
        
        # Format the output based on preference
        if output_format == "json":
            print(df.to_json(orient="records", indent=2))
        elif output_format == "csv":
            print(df.to_csv(index=False))
        else:  # Default to table
            # Limit long fields for better display
            for col in ['title', 'summary', 'link']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: (x[:60] + '...') if isinstance(x, str) and len(x) > 60 else x)
            
            # Convert to table format
            print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
        
        print(f"\nFound {len(df)} records matching '{search_term}'")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def get_company_stats(database_path="press_releases.db"):
    """Get statistics on which companies have press releases in the database."""
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Extract domain from link to identify company
        query = """
        SELECT 
            CASE
                WHEN link LIKE '%thameswater.co.uk%' THEN 'Thames Water'
                WHEN link LIKE '%londoncityairport.com%' THEN 'London City Airport'
                -- Add more companies as needed
                ELSE SUBSTR(link, INSTR(link, '://') + 3, 
                      CASE 
                          WHEN INSTR(SUBSTR(link, INSTR(link, '://') + 3), '/') = 0 
                          THEN LENGTH(SUBSTR(link, INSTR(link, '://') + 3))
                          ELSE INSTR(SUBSTR(link, INSTR(link, '://') + 3), '/') - 1
                      END)
            END AS company,
            COUNT(*) AS count,
            MIN(first_seen) AS earliest,
            MAX(first_seen) AS latest
        FROM press_releases
        GROUP BY company
        ORDER BY count DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Close the connection
        conn.close()
        
        if not rows:
            print("No records found in the database.")
            return
        
        # Display results
        print(tabulate(rows, headers=['Company', 'Count', 'Earliest', 'Latest'], tablefmt='psql'))
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def clear_database(database_path="press_releases.db", confirm=True):
    """
    Remove all items from the press releases database.
    
    Args:
        database_path (str): Path to the SQLite database
        confirm (bool): Whether to ask for confirmation before deleting
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    if confirm:
        response = input(f"Are you sure you want to delete ALL records from {database_path}? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM press_releases")
        count = cursor.fetchone()[0]
        
        # Delete all records
        cursor.execute("DELETE FROM press_releases")
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        conn.close()
        
        print(f"Successfully deleted {count} records from the database.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Simple command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description='View or search press releases database')
    parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    parser.add_argument('--limit', '-l', type=int, help='Limit the number of records to display')
    parser.add_argument('--format', '-f', choices=['table', 'csv', 'json'], default='table', 
                        help='Output format')
    parser.add_argument('--search', '-s', help='Search term to find in the database')
    parser.add_argument('--stats', action='store_true', help='Show statistics by company')
    parser.add_argument('--clear', action='store_true', help='Clear all records from the database')
    parser.add_argument('--force', action='store_true', help='Skip confirmation when clearing database')
    
    args = parser.parse_args()
    
    if args.clear:
        clear_database(args.db, not args.force)
    elif args.stats:
        get_company_stats(args.db)
    elif args.search:
        search_database(args.search, args.db, args.format)
    else:
        view_database(args.db, args.limit, args.format)