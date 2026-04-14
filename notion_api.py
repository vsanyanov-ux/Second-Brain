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

    def get_active_tasks(self):
        """Retrieves tasks that are not 'Done' from the Projects database."""
        if not self.projects_id:
            return []
            
        response = self.notion.databases.query(
            database_id=self.projects_id,
            filter={
                "and": [
                    {
                        "property": "Status",
                        "status": {
                            "does_not_equal": "Done"
                        }
                    },
                    {
                        "property": "Status",
                        "status": {
                            "does_not_equal": "Archived"
                        }
                    }
                ]
            }
        )
        
        tasks = []
        for page in response.get("results", []):
            title = "No Title"
            properties = page.get("properties", {})
            # Extract title from 'Name' property
            name_prop = properties.get("Name", {}).get("title", [])
            if name_prop:
                title = name_prop[0].get("text", {}).get("content", "No Title")
            
            status = properties.get("Status", {}).get("status", {}).get("name", "Unknown")
            
            # Retrieve 'Next Action' property
            next_action = ""
            next_action_prop = properties.get("Next Action", {}).get("rich_text", [])
            if next_action_prop:
                next_action = next_action_prop[0].get("text", {}).get("content", "")
            
            tasks.append({
                "id": page.get("id"),
                "title": title, 
                "status": status,
                "next_action": next_action
            })
            
        return tasks

    def update_task_status(self, page_id, status_name="Done"):
        """Updates the status of a specific task."""
        return self.notion.pages.update(
            page_id=page_id,
            properties={
                "Status": {"status": {"name": status_name}}
            }
        )

    def add_to_inbox(self, data):
        """Specifically for Ideas/Inbox."""
        return self._create_page(self.inbox_id, data)

    def add_to_projects(self, data):
        """Specifically for Projects/Tasks."""
        return self._create_page(self.projects_id, data)

    def add_to_resources(self, data):
        """Specifically for Resources or People."""
        return self._create_page(self.resources_id, data)

    def _create_page(self, database_id, data):
        if not database_id or database_id == "your_id_here" or len(database_id) < 10:
            error_msg = f"Database ID for {data.get('category')} is missing or invalid in .env"
            logging.error(error_msg)
            raise ValueError(error_msg)

        category = data.get("category", "Idea")
        url = data.get("url")
        summary = data.get("summary", "")
        next_action = data.get("next_action", "")
        context = data.get("context", "")
        
        # Base properties common to all
        properties: dict = {
            "Name": {"title": [{"text": {"content": data.get("title", "No Title")}}]}
        }

        # Page content (blocks)
        children = []
        
        # Add summary/next action/context to page content for visibility
        content_parts = []
        if summary: content_parts.append(f"📝 {summary}")
        if next_action: content_parts.append(f"🎯 **Next Action**: {next_action}")
        if context: content_parts.append(f"👥 **Context**: {context}")
        
        if url:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "🔗 Link: "}},
                        {"type": "text", "text": {"content": url, "link": {"url": url}}}
                    ]
                }
            })

        for part in content_parts:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": part}}]
                }
            })

        # Specific mappings based on database schema
        if database_id == self.projects_id: # Projects Database
            properties["Status"] = {"status": {"name": "Not started"}}
            if next_action:
                properties["Next Action"] = {"rich_text": [{"text": {"content": next_action}}]}
                # Optionally remove from page text if it's in the property
                if f"🎯 **Next Action**: {next_action}" in content_parts:
                    content_parts.remove(f"🎯 **Next Action**: {next_action}")

        elif database_id == self.inbox_id: # Ideas Database (Inbox)
            # Use 'Text' property if it exists, or just rely on page content
            properties["Text"] = {"rich_text": [{"text": {"content": summary}}]}
            if data.get("tags"):
                properties["Tags"] = {"multi_select": [{"name": tag} for tag in data.get("tags")]}
            if url:
                # Assuming 'URL' property exists in the Inbox database
                properties["URL"] = {"url": url}

        elif database_id == self.resources_id: # Areas/Resources
            if category == "Person":
                properties["Type"] = {"status": {"name": "Person"}}
            else:
                properties["Type"] = {"status": {"name": "Resource"}}

        return self.notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children if children else None
        )
