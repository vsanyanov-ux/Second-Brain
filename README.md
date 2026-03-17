# AI Second Brain System (Telegram + Notion + Google Calendar)

An automated system to capture, classify, and route information from Telegram messages (text, voice, links) into structured Notion databases and Google Calendar using AI (Mistral/OpenAI).

## 🧠 System Architecture

```mermaid
graph TD
    User((User)) -->|Text / Link / Voice| TG[Telegram Bot]
    TG -->|Forward Content| Processor[Brain Processor AI]
    
    subgraph AI Processing
        Processor --> LLM[Mistral AI / OpenAI]
        LLM -->|Classification & Data Extraction| Processor
    end

    Processor -->|Task/Note/Resource| NotionRouter{Notion Router}
    Processor -->|Event| CalendarRouter{Calendar Router}
    
    NotionRouter -->|Task| Projects[(Notion Projects)]
    NotionRouter -->|Resource| Resources[(Notion Resources)]
    NotionRouter -->|Note| Inbox[(Notion Inbox)]
    
    CalendarRouter -->|Add Event| GCal[(Google Calendar)]
    
    GCal -.->|Daily/Weekly Summary| TG
    Projects -.->|Daily Summary| TG
    
    TG -->|Confirmation / Links| User
    User -->|Interactive Buttons| TG
    TG -->|Update Status| Projects
```

## 🚀 Features

- **Multi-modal Capture**: Supports text, voice messages (Whisper transcription), and web links.
- **AI Classification**: Automatically sorts inputs into PARA-style categories (Projects, Resources, Inbox) or Calendar Events.
- **Google Calendar Integration**:
  - **Read**: Daily summaries and Weekly schedule (`/week`).
  - **Write**: Natural language event creation (e.g., "Meeting tomorrow at 5pm").
- **Interactive Tasks**: Mark Notion tasks as "Done" directly from Telegram using inline buttons.
- **Docker Ready**: Fully containerized for easy deployment on VPS.
- **Direct Access**: Optimized for servers with direct access to Mistral/OpenAI APIs (no proxy needed).

## 🛠️ Setup

### 1. Requirements
- Docker & Docker Compose
- Notion API Integration
- Google Cloud Project (for Calendar API)

### 2. Configuration (.env)
Create a `.env` file with the following:
```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_USER_ID=your_id
NOTION_TOKEN=your_token
NOTION_INBOX_ID=your_id
NOTION_PROJECTS_ID=your_id
NOTION_RESOURCES_ID=your_id
AI_PROVIDER=mistral # or openai
MISTRAL_API_KEY=your_key
SUMMARY_TIME=09:00
```

### 3. Google Calendar Setup
1. Enable Google Calendar API in Cloud Console.
2. Download `credentials.json` and place it in the root directory.
3. Run the bot locally once to generate `token.json` via interactive login.

### 4. Running the Bot (Docker)
```bash
# Build and start the container in background
docker compose up -d --build

# View logs
docker compose logs -f
```

## 🛠️ Utilities
- `find_notion_ids.py`: Automatically list your Notion database IDs.
- `calendar_api.py`: Independent module for testing Google Calendar.

---
*Inspired by Tiago Forte's Building a Second Brain.*
