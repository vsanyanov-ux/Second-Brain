import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def inspect_notion():
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    print(f"Top-level Client attributes: {dir(notion)}")

if __name__ == "__main__":
    inspect_notion()
