import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class NotionIntegrator:
    def __init__(self):
        self.notion = Client(auth=os.getenv("NOTION_TOKEN"))
        self.inbox_id = os.getenv("NOTION_INBOX_ID")
        self.projects_id = os.getenv("NOTION_PROJECTS_ID")
        self.resources_id = os.getenv("NOTION_RESOURCES_ID")

    def add_to_inbox(self, data):
        """Adds a new page to the Inbox database."""
        return self._create_page(self.inbox_id, data)

    def add_to_projects(self, data):
        """Adds a new task/project page."""
        return self._create_page(self.projects_id, data)

    def add_to_resources(self, data):
        """Adds a resource entry."""
        return self._create_page(self.resources_id, data)

    def _create_page(self, database_id, data):
        if not database_id or database_id == "your_id_here":
            print(f"Warning: Database ID for {data.get('category')} is missing.")
            return None

        properties = {
            "Name": {"title": [{"text": {"content": data.get("title", "No Title")}}]},
            "Summary": {"rich_text": [{"text": {"content": data.get("summary", "")}}]},
            "Category": {"select": {"name": data.get("category", "Note")}}
        }
        
        if data.get("tags"):
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in data.get("tags")]}

        return self.notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
