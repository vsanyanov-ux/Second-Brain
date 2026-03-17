import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def test_query():
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_PROJECTS_ID")
    
    print(f"Token: {token[:10]}...")
    print(f"Database ID: {db_id}")
    
    notion = Client(auth=token)
    try:
        print("Attempting to query database...")
        response = notion.databases.query(
            database_id=db_id,
            page_size=1
        )
        print("Success! Found results.")
        # print(response)
    except AttributeError as e:
        print(f"AttributeError: {e}")
    except Exception as e:
        print(f"Other error: {e}")

if __name__ == "__main__":
    test_query()
