import os
import sys
import time
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

def backfill_next_actions():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    db_id = os.getenv("NOTION_PROJECTS_ID")
    
    print(f"Starting backfill for database: {db_id}")
    
    # 1. Query all pages from the Projects database
    response = notion.databases.query(database_id=db_id)
    pages = response.get("results", [])
    
    print(f"Found {len(pages)} pages to check.")
    
    updated_count = 0
    for page in pages:
        page_id = page["id"]
        properties = page.get("properties", {})
        
        # Get page title for logging
        title = "Untitled"
        name_prop = properties.get("Name", {}).get("title", [])
        if name_prop:
            title = name_prop[0].get("plain_text", "Untitled")
            
        # Check if Next Action is already set
        next_action_prop = properties.get("Next Action", {}).get("rich_text", [])
        if next_action_prop:
            print(f"Skipping '{title}' (Next Action already set)")
            continue
            
        print(f"Checking blocks for '{title}'...")
        
        # 2. List blocks for this page
        blocks_response = notion.blocks.children.list(block_id=page_id)
        blocks = blocks_response.get("results", [])
        
        found_next_action = None
        for block in blocks:
            if block["type"] == "paragraph":
                text_list = block["paragraph"].get("rich_text", [])
                if text_list:
                    full_text = "".join([t["plain_text"] for t in text_list])
                    # Look for "🎯 **Next Action**: " or "Next Action:"
                    if "Next Action" in full_text:
                        # Extract the text after the colon
                        if ":" in full_text:
                            found_next_action = full_text.split(":", 1)[1].strip()
                            # Remove the leading ** if it was bolded in the text
                            if found_next_action.startswith("**"):
                                found_next_action = found_next_action.replace("**", "").strip()
                            break
        
        # 3. If found, update the page property
        if found_next_action:
            print(f"Found Next Action: '{found_next_action}'. Updating...")
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Next Action": {
                        "rich_text": [
                            {"text": {"content": found_next_action}}
                        ]
                    }
                }
            )
            updated_count += 1
            # Small delay to avoid rate limits
            time.sleep(0.3)
        else:
            print(f"❓ No Next Action found in blocks for '{title}'")

    print(f"\nBackfill complete! Updated {updated_count} pages.")

if __name__ == "__main__":
    backfill_next_actions()
