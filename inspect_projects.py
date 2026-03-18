import os
import json
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def inspect():
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    db_id = os.getenv("NOTION_PROJECTS_ID")
    
    print(f"Querying database: {db_id}")
    try:
        response = notion.databases.query(database_id=db_id, page_size=1)
        if response["results"]:
            page = response["results"][0]
            print("Properties found in the first page:")
            print(json.dumps(list(page["properties"].keys()), indent=2))
            
            # Print specifically for Next Action if it exists
            for prop_name in page["properties"]:
                if "next" in prop_name.lower() or "action" in prop_name.lower():
                    print(f"\nFound potential property: {prop_name}")
                    print(json.dumps(page["properties"][prop_name], indent=2))
        else:
            print("No pages found in the database.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
