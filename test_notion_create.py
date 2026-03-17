import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def test_create_page():
    token = os.getenv("NOTION_TOKEN")
    notion = Client(auth=token)
    db_id = os.getenv("NOTION_PROJECTS_ID")
    inbox_id = os.getenv("NOTION_INBOX_ID")
    
    print(f"--- Testing INBOX ({inbox_id}) ---")
    try:
        res = notion.pages.create(
            parent={"database_id": inbox_id},
            properties={"Name": {"title": [{"text": {"content": "Test Note"}}]}}
        )
        print("Success in INBOX!")
    except Exception as e:
        print(f"Failed in INBOX: {e}")

    print(f"\n--- Testing PROJECTS ({db_id}) ---")
    
    properties = {
        "Name": {"title": [{"text": {"content": "Test Task"}}]}
    }
    
    try:
        # Minimal properties first
        res = notion.pages.create(
            parent={"database_id": db_id},
            properties=properties
        )
        print("Success with minimal properties!")
        print(f"Page URL: {res.get('url')}")
        
        # Now try with full properties
        properties["Summary"] = {"rich_text": [{"text": {"content": "Test Summary"}}]}
        properties["Category"] = {"select": {"name": "Task"}}
        
        try:
            res2 = notion.pages.create(
                parent={"database_id": db_id},
                properties=properties
            )
            print("Success with full properties!")
        except Exception as e:
            print(f"Failed with full properties: {e}")
            
    except Exception as e:
        print(f"Failed even with minimal properties: {e}")

if __name__ == "__main__":
    test_create_page()
