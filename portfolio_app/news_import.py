# portfolio_app/news_import.py
import os
import sys
import json
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_portfolio_project.settings')
import django
django.setup()

from portfolio_app.models import News

def parse_french_date(date_str):
    """Convert French date format (DD/MM/YYYY) to Python datetime"""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        return None

def process_news_data(json_data):
    """Process and filter news data"""
    # Parse JSON string if needed
    if isinstance(json_data, str):
        news_items = json.loads(json_data)
    else:
        news_items = json_data

    # Filter and sort news items
    valid_items = []
    
    for item in news_items:
        # Check if required fields exist and are not empty
        if not all(key in item and item[key] for key in ['title', 'date', 'description']):
            print(f"Skipping item due to missing fields: {item}")
            continue
            
        # Parse date
        date = parse_french_date(item['date'])
        if not date:
            print(f"Skipping item due to invalid date format: {item['date']}")
            continue
            
        # Only keep items from 2023 onwards
        if date.year < 2023:
            print(f"Skipping item from before 2023: {date}")
            continue
            
        valid_items.append({
            'title': item['title'],
            'date': date,
            'description': item['description']
        })
    
    # Sort by date (newest first)
    return sorted(valid_items, key=lambda x: x['date'], reverse=True)

def import_to_database(processed_items):
    """Import processed items to Django database"""
    imported_count = 0
    skipped_count = 0
    
    for item in processed_items:
        # Check if news with same title and date already exists
        if not News.objects.filter(title=item['title'], date=item['date']).exists():
            News.objects.create(**item)
            imported_count += 1
            print(f"Imported: {item['title']}")
        else:
            skipped_count += 1
            print(f"Skipped (already exists): {item['title']}")
    
    return imported_count, skipped_count

def main(json_file_path):
    """Main function to process file and import data"""
    try:
        print(f"Starting import process...")
        print(f"Reading file from: {json_file_path}")
        
        # Read JSONL file
        news_items = []
        with open(json_file_path, 'r', encoding='utf-8') as file:
            json_str = file.read()
            # Remove any BOM if present
            if json_str.startswith('\ufeff'):
                json_str = json_str[1:]
            news_items = json.loads(json_str)
        
        print(f"Successfully read {len(news_items)} items from file")
        
        # Process the data
        processed_items = process_news_data(news_items)
        print(f"Processed {len(processed_items)} valid items")
        
        # Import to database
        imported, skipped = import_to_database(processed_items)
        
        print("\nProcessing complete:")
        print(f"- {len(processed_items)} valid items found")
        print(f"- {imported} new items imported")
        print(f"- {skipped} items skipped (already existed)")
        
    except FileNotFoundError:
        print(f"Error: Could not find file at {json_file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in file: {str(e)}")
        raise
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    # Use raw string for Windows file path
    file_path = r"C:\Users\DELL\Desktop\RL\Nouveau dossier\New folder\data\bvmt_2024-12-07_17-57-54.jsonl"
    main(file_path)