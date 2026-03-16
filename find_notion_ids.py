import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def find_databases():
    token = os.getenv("NOTION_TOKEN")
    if not token or token == "your_notion_token_here":
        print("❌ Error: NOTION_TOKEN not found in .env file.")
        return

    notion = Client(auth=token)
    try:
        results = notion.search(filter={"property": "object", "value": "database"}).get("results", [])
        
        if not results:
            print("❓ No databases found. Make sure you have shared your dashboard with the integration.")
            return

        print("\n--- Found Notion Databases ---")
        for db in results:
            name = db.get("title", [{}])[0].get("plain_text", "Untitled")
            db_id = db.get("id")
            print(f"Name: {name}")
            print(f"ID:   {db_id}\n")
        print("-------------------------------")
        print("Copy these IDs into your .env file!")
        
    except Exception as e:
        print(f"❌ Error connecting to Notion: {e}")

if __name__ == "__main__":
    find_databases()
