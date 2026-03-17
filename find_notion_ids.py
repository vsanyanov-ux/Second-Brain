import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def inspect_databases():
    token = os.getenv("NOTION_TOKEN")
    notion = Client(auth=token)
    
    db_ids = {
        "Inbox": os.getenv("NOTION_INBOX_ID"),
        "Projects": os.getenv("NOTION_PROJECTS_ID"),
        "Resources": os.getenv("NOTION_RESOURCES_ID")
    }
    
    print("--- Inspecting Databases ---")
    for name, db_id in db_ids.items():
        if not db_id: continue
        try:
            print(f"\nTarget: {name} (ID: {db_id})")
            db = notion.databases.retrieve(database_id=db_id)
            print(f"  Object Type: {db.get('object')}")
            print(f"  Title: {db.get('title', [{}])[0].get('plain_text', 'N/A')}")
            print(f"  Is Inline: {db.get('is_inline')}")
            
            # Check properties
            props = db.get("properties", {})
            print(f"  Properties: {list(props.keys())}")
            
            # Check if it has a 'title' property specifically (it usually does 'Name')
            title_props = [k for k, v in props.items() if v.get("type") == "title"]
            print(f"  Title Property: {title_props}")

        except Exception as e:
            print(f"  Failed inspection: {e}")

if __name__ == "__main__":
    inspect_databases()
