import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

from processor import BrainProcessor
from notion_api import NotionIntegrator

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class SecondBrainBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.brain = BrainProcessor()
        self.notion = NotionIntegrator()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if not text:
            return

        await update.message.reply_text("🧠 Thinking...")
        
        # 1. Process with AI
        data = self.brain.classify_and_process(text)
        
        # 2. Route to Notion
        category = data.get("category", "Note")
        result = None
        
        if category == "Task":
            result = self.notion.add_to_projects(data)
            folder = "Projects/Tasks"
        elif category == "Resource":
            result = self.notion.add_to_resources(data)
            folder = "Resources"
        else:
            result = self.notion.add_to_inbox(data)
            folder = "Inbox"

        if result:
            notion_url = result.get("url", "#")
            await update.message.reply_text(
                f"✅ Saved as **{category}** in **{folder}**\n"
                f"📌 Title: {data.get('title')}\n"
                f"🔗 [View in Notion]({notion_url})",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Error saving to Notion. Check your Database IDs in .env\n"
                f"Category: {category}\n"
                f"Title: {data.get('title')}"
            )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🎙️ Transcribing voice...")
        
        # Download voice file
        voice_file = await update.message.voice.get_file()
        file_path = "temp_voice.ogg"
        await voice_file.download_to_drive(file_path)
        
        # Transcribe
        text = self.brain.transcribe_voice(file_path)
        os.remove(file_path) # Clean up
        
        await update.message.reply_text(f"📝 Transcript: {text}")
        
        # Process the transcript like a normal message
        update.message.text = text
        await self.handle_message(update, context)

    def run(self):
        application = ApplicationBuilder().token(self.token).build()
        
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        voice_handler = MessageHandler(filters.VOICE, self.handle_voice)
        
        application.add_handler(text_handler)
        application.add_handler(voice_handler)
        
        print("Bot is running...")
        application.run_polling()

if __name__ == '__main__':
    bot = SecondBrainBot()
    bot.run()
