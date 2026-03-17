import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def test_direct_retrieval():
    token = os.getenv("NOTION_TOKEN")
    notion = Client(auth=token)
    
    db_ids = {
        "Inbox": os.getenv("NOTION_INBOX_ID"),
        "Projects": os.getenv("NOTION_PROJECTS_ID"),
        "Resources": os.getenv("NOTION_RESOURCES_ID")
    }
    
    print("Testing Direct Retrieval...")
    for name, db_id in db_ids.items():
        if not db_id or "your" in db_id:
            print(f"{name}: ID missing or invalid.")
            continue
            
        try:
            db = notion.databases.retrieve(database_id=db_id)
            title = db.get("title", [{}])[0].get("plain_text", "Untitled")
            print(f"{name} ({db_id}): Success! Title: {title}")
        except Exception as e:
            print(f"{name} ({db_id}): Failed. Error: {e}")

if __name__ == "__main__":
    test_direct_retrieval()
