import sqlite3
import sys
import os
from datetime import datetime
import pandas as pd
from tabulate import tabulate

def get_all_tables(database_path):
    """
    Get a list of all tables in the database.
    
    Args:
        database_path (str): Path to the SQLite database
        
    Returns:
        list: List of table names
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return []
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Query all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return tables
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def get_table_columns(database_path, table_name):
    """
    Get a list of columns for a specific table.
    
    Args:
        database_path (str): Path to the SQLite database
        table_name (str): Name of the table
        
    Returns:
        list: List of column names
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return []
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Query columns for the table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        conn.close()
        return columns
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def view_database(database_path="press_releases.db", table_name=None, limit=None, output_format="table"):
    """
    View items in the database, optionally specifying a table.
    
    Args:
        database_path (str): Path to the SQLite database
        table_name (str, optional): Specific table to view (if None, defaults to press_releases)
        limit (int, optional): Limit the number of records to display
        output_format (str): Format to display results ("table", "csv", "json")
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        
        # If no table specified, use press_releases as default
        if table_name is None:
            table_name = "press_releases"
        
        # Check if the table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            print(f"Table '{table_name}' not found in the database.")
            tables = get_all_tables(database_path)
            if tables:
                print(f"Available tables: {', '.join(tables)}")
            conn.close()
            return
        
        # Create a query with optional limit
        query = f"SELECT * FROM {table_name}"
        
        # Add ORDER BY if it's the press_releases table (maintain compatibility with original function)
        if table_name == "press_releases" and "first_seen" in get_table_columns(database_path, table_name):
            query += " ORDER BY first_seen DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        # Load data into a DataFrame for easier formatting
        df = pd.read_sql_query(query, conn)
        
        # Close the connection
        conn.close()
        
        if len(df) == 0:
            print(f"No records found in the table '{table_name}'.")
            return
        
        # Format the output based on preference
        if output_format == "json":
            print(df.to_json(orient="records", indent=2))
        elif output_format == "csv":
            print(df.to_csv(index=False))
        else:  # Default to table
            # Limit long fields for better display
            for col in df.columns:
                if df[col].dtype == 'object':  # Only process string columns
                    df[col] = df[col].apply(lambda x: (str(x)[:60] + '...') if isinstance(x, str) and len(x) > 60 else x)
            
            # Convert to table format
            print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
        
        print(f"\nTotal records in {table_name}: {len(df)}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def search_by_column(database_path, table_name, column_name, search_term, output_format="table", limit=None):
    """
    Search for specific terms in a single column of a table.
    
    Args:
        database_path (str): Path to the SQLite database
        table_name (str): Table to search in
        column_name (str): Column to search in
        search_term (str): Term to search for
        output_format (str): Format to display results ("table", "csv", "json")
        limit (int, optional): Limit the number of records to display
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        
        # Check if the table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            print(f"Table '{table_name}' not found in the database.")
            tables = get_all_tables(database_path)
            if tables:
                print(f"Available tables: {', '.join(tables)}")
            conn.close()
            return
        
        # Check if the column exists
        columns = get_table_columns(database_path, table_name)
        if column_name not in columns:
            print(f"Column '{column_name}' not found in table '{table_name}'.")
            print(f"Available columns: {', '.join(columns)}")
            conn.close()
            return
        
        # Create a search query
        query = f"""
        SELECT * FROM {table_name} 
        WHERE {column_name} LIKE ?
        """
        search_param = f"%{search_term}%"
        
        # Add limit if specified
        if limit:
            query += f" LIMIT {limit}"
        
        # Load data into a DataFrame
        df = pd.read_sql_query(query, conn, params=(search_param,))
        
        # Close the connection
        conn.close()
        
        if len(df) == 0:
            print(f"No records found in '{table_name}' where {column_name} matches '{search_term}'.")
            return
        
        # Format the output based on preference
        if output_format == "json":
            print(df.to_json(orient="records", indent=2))
        elif output_format == "csv":
            print(df.to_csv(index=False))
        else:  # Default to table
            # Limit long fields for better display
            for col in df.columns:
                if df[col].dtype == 'object':  # Only process string columns
                    df[col] = df[col].apply(lambda x: (str(x)[:60] + '...') if isinstance(x, str) and len(x) > 60 else x)
            
            # Convert to table format
            print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
        
        print(f"\nFound {len(df)} records in '{table_name}' where {column_name} matches '{search_term}'")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def search_multi_columns(database_path, table_name, column_values, output_format="table", operator="AND", limit=None):
    """
    Search for records matching multiple column conditions.
    
    Args:
        database_path (str): Path to the SQLite database
        table_name (str): Table to search in
        column_values (dict): Dictionary of column:search_term pairs
        output_format (str): Format to display results ("table", "csv", "json")
        operator (str): Logical operator to join conditions ("AND" or "OR")
        limit (int, optional): Limit the number of records to display
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    if not column_values:
        print("No search criteria provided.")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        
        # Check if the table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            print(f"Table '{table_name}' not found in the database.")
            tables = get_all_tables(database_path)
            if tables:
                print(f"Available tables: {', '.join(tables)}")
            conn.close()
            return
        
        # Check if all columns exist
        columns = get_table_columns(database_path, table_name)
        invalid_columns = [col for col in column_values.keys() if col not in columns]
        if invalid_columns:
            print(f"Invalid columns: {', '.join(invalid_columns)}")
            print(f"Available columns: {', '.join(columns)}")
            conn.close()
            return
        
        # Build the WHERE clause
        where_clauses = []
        params = []
        
        for col, value in column_values.items():
            where_clauses.append(f"{col} LIKE ?")
            params.append(f"%{value}%")
        
        # Join conditions with the specified operator
        op = " AND " if operator.upper() == "AND" else " OR "
        where_clause = op.join(where_clauses)
        
        # Create the query
        query = f"SELECT * FROM {table_name} WHERE {where_clause}"
        
        # Add limit if specified
        if limit:
            query += f" LIMIT {limit}"
        
        # Execute the query
        df = pd.read_sql_query(query, conn, params=params)
        
        # Close the connection
        conn.close()
        
        if len(df) == 0:
            print(f"No matching records found in '{table_name}'.")
            return
        
        # Format the output based on preference
        if output_format == "json":
            print(df.to_json(orient="records", indent=2))
        elif output_format == "csv":
            print(df.to_csv(index=False))
        else:  # Default to table
            # Limit long fields for better display
            for col in df.columns:
                if df[col].dtype == 'object':  # Only process string columns
                    df[col] = df[col].apply(lambda x: (str(x)[:60] + '...') if isinstance(x, str) and len(x) > 60 else x)
            
            # Convert to table format
            print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
        
        # Format the search criteria for display
        criteria = [f"{col} LIKE '%{val}%'" for col, val in column_values.items()]
        criteria_str = f" {op.lower()} ".join(criteria)
        
        print(f"\nFound {len(df)} records in '{table_name}' where {criteria_str}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def list_tables(database_path="press_releases.db"):
    """
    List all tables in the database with their row counts and column information.
    
    Args:
        database_path (str): Path to the SQLite database
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            conn.close()
            return
        
        # Get information for each table
        table_info = []
        
        for table_name in [t[0] for t in tables]:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = ", ".join([col[1] for col in columns])
            
            # Add to table info
            table_info.append({
                "Table": table_name,
                "Rows": row_count,
                "Columns": column_names
            })
        
        conn.close()
        
        # Display table information
        print(tabulate(table_info, headers="keys", tablefmt="psql"))
        
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
        # Check if the press_releases table exists
        tables = get_all_tables(database_path)
        if "press_releases" not in tables:
            print("The press_releases table doesn't exist in this database.")
            return
        
        # Check if company_name column exists
        columns = get_table_columns(database_path, "press_releases")
        
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Use the appropriate query based on whether company_name column exists
        if "company_name" in columns:
            query = """
            SELECT 
                company_name AS company,
                COUNT(*) AS count,
                MIN(first_seen) AS earliest,
                MAX(first_seen) AS latest
            FROM press_releases
            GROUP BY company_name
            ORDER BY count DESC
            """
        else:
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

def clear_database(database_path="press_releases.db", table_name=None, confirm=True):
    """
    Remove all items from a table in the database.
    
    Args:
        database_path (str): Path to the SQLite database
        table_name (str, optional): Specific table to clear (if None, defaults to press_releases)
        confirm (bool): Whether to ask for confirmation before deleting
    """
    if not os.path.exists(database_path):
        print(f"Database file not found: {database_path}")
        return
    
    # If no table specified, use press_releases as default
    if table_name is None:
        table_name = "press_releases"
    
    # Check if the table exists
    tables = get_all_tables(database_path)
    if table_name not in tables:
        print(f"Table '{table_name}' not found in the database.")
        print(f"Available tables: {', '.join(tables)}")
        return
    
    if confirm:
        response = input(f"Are you sure you want to delete ALL records from table '{table_name}'? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        # Delete all records
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        conn.close()
        
        print(f"Successfully deleted {count} records from table '{table_name}'.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Command-line interface with enhanced functionality
    import argparse
    
    parser = argparse.ArgumentParser(description='View and search SQLite database tables')
    
    # Main subparsers
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View table contents')
    view_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    view_parser.add_argument('--table', '-t', help='Table to view (default: press_releases)')
    view_parser.add_argument('--limit', '-l', type=int, help='Limit the number of records to display')
    view_parser.add_argument('--format', '-f', choices=['table', 'csv', 'json'], default='table', 
                             help='Output format')
    
    # Search single column command
    search_parser = subparsers.add_parser('search', help='Search in a single column')
    search_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    search_parser.add_argument('--table', '-t', required=True, help='Table to search in')
    search_parser.add_argument('--column', '-c', required=True, help='Column to search in')
    search_parser.add_argument('--term', '-s', required=True, help='Search term')
    search_parser.add_argument('--limit', '-l', type=int, help='Limit the number of records to display')
    search_parser.add_argument('--format', '-f', choices=['table', 'csv', 'json'], default='table', 
                               help='Output format')
    
    # Multi-column search command
    multi_parser = subparsers.add_parser('multi', help='Search across multiple columns')
    multi_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    multi_parser.add_argument('--table', '-t', required=True, help='Table to search in')
    multi_parser.add_argument('--columns', '-c', required=True, help='Column:value pairs separated by commas (e.g., title:water,company_name:Thames)')
    multi_parser.add_argument('--operator', '-o', choices=['and', 'or'], default='and', 
                              help='Logical operator to join conditions (default: and)')
    multi_parser.add_argument('--limit', '-l', type=int, help='Limit the number of records to display')
    multi_parser.add_argument('--format', '-f', choices=['table', 'csv', 'json'], default='table', 
                              help='Output format')
    
    # List tables command
    list_parser = subparsers.add_parser('list', help='List all tables in the database')
    list_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics by company')
    stats_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear all records from a table')
    clear_parser.add_argument('--db', '-d', default='press_releases.db', help='Path to the database file')
    clear_parser.add_argument('--table', '-t', help='Table to clear (default: press_releases)')
    clear_parser.add_argument('--force', action='store_true', help='Skip confirmation when clearing table')
    
    args = parser.parse_args()
    
    # Determine and execute the requested command
    if args.command == 'view' or args.command is None:  # Default to view if no command specified
        view_database(args.db, args.table, args.limit, args.format)
    
    elif args.command == 'search':
        search_by_column(args.db, args.table, args.column, args.term, args.format, args.limit)
    
    elif args.command == 'multi':
        # Parse column:value pairs
        try:
            column_values = {}
            for pair in args.columns.split(','):
                col, val = pair.split(':')
                column_values[col.strip()] = val.strip()
            
            search_multi_columns(args.db, args.table, column_values, args.format, args.operator, args.limit)
        except ValueError:
            print("Error: Column:value pairs must be in format 'column1:value1,column2:value2'")
    
    elif args.command == 'list':
        list_tables(args.db)
    
    elif args.command == 'stats':
        get_company_stats(args.db)
    
    elif args.command == 'clear':
        clear_database(args.db, args.table, not args.force)
    
    else:
        # Show help if no valid command is provided
        parser.print_help()