import os
import logging
import asyncio
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv

from processor import BrainProcessor
from notion_api import NotionIntegrator
from calendar_api import GoogleCalendarIntegrator

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
        self.calendar = GoogleCalendarIntegrator()
        self.user_id = os.getenv("TELEGRAM_USER_ID")
        self.summary_time = os.getenv("SUMMARY_TIME", "09:00")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username
        await update.message.reply_text(
            f"👋 Привет, {username}!\n\n"
            f"Я твой Second Brain бот. Я готов сохранять твои заметки, задачи и ссылки в Notion.\n\n"
            f"Твой Telegram ID: `{user_id}`\n"
            "Пожалуйста, добавь этот ID в файл `.env` как `TELEGRAM_USER_ID`, чтобы я мог присылать тебе утренние сводки."
        )

    async def manual_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger a summary via command."""
        # Use either the configured user_id or the current chat_id
        target_id = self.user_id if self.user_id else update.effective_chat.id
        await self._send_summary_to(target_id, context)

    async def send_daily_summary(self, context: ContextTypes.DEFAULT_TYPE):
        """Scheduled task for daily summary."""
        if not self.user_id:
            logging.warning("TELEGRAM_USER_ID not set, skipping summary.")
            return
        await self._send_summary_to(self.user_id, context)

    async def _send_summary_to(self, chat_id, context):
        """Core logic to fetch tasks and send message."""
        try:
            # 1. Fetch Notion Tasks
            tasks = self.notion.get_active_tasks()
            
            # 2. Fetch Calendar Events
            events = self.calendar.get_today_events()
            
            summary_lines = ["🌅 Доброе утро! Твоя сводка на сегодня:\n"]
            
            # Keyboards for buttons
            keyboard = []
            
            # Notion Section
            if tasks:
                grouped_tasks = {}
                for t in tasks:
                    status = t['status']
                    if status not in grouped_tasks:
                        grouped_tasks[status] = []
                    grouped_tasks[status].append(t)
                
                summary_lines.append("📋 *Задачи из Notion*: \n")
                for status, t_list in grouped_tasks.items():
                    summary_lines.append(f"📌 *{status}*:")
                    for t in t_list:
                        summary_lines.append(f"  🔹 {t['title']}")
                        # Add a button for each active task (limit to avoid too big keyboard)
                        if len(keyboard) < 8: 
                            keyboard.append([InlineKeyboardButton(f"✅ {t['title'][:20]}...", callback_data=f"done_{t['id']}")])
                    summary_lines.append("")
            else:
                summary_lines.append("✅ Активных задач в Notion нет.\n")

            # Calendar Section
            if events:
                summary_lines.append("🗓️ *События из Google Календаря*: \n")
                for event in events:
                    summary_lines.append(f"⏰ {event['time']} — {event['summary']}")
                summary_lines.append("")
            else:
                summary_lines.append("🗓️ Событий в календаре на сегодня нет.\n")
            
            message = "\n".join(summary_lines) + "Удачного дня! 💪"
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await context.bot.send_message(
                chat_id=chat_id, 
                text=message, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error in summary delivery: {e}")
            if chat_id:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка при формировании сводки: {e}")
                except: pass

    async def complete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback handler for marking task as Done."""
        query = update.callback_query
        await query.answer()
        
        task_id = query.data.replace("done_", "")
        try:
            self.notion.update_task_status(task_id, "Done")
            # Update the message text or just send a confirmation
            await query.edit_message_text(
                text=f"{query.message.text}\n\n✅ Задача отмечена как выполненная!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error completing task: {e}")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Ошибка при закрытии задачи: {e}")

    async def week_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fetches and sends events for the next 7 days."""
        target_id = self.user_id if self.user_id else update.effective_chat.id
        try:
            events = self.calendar.get_week_events()
            if not events:
                await update.message.reply_text("🗓️ Событий на этой неделе не запланировано.")
                return

            summary_lines = ["📅 *Твое расписание на неделю*:\n"]
            # Group by date
            grouped = {}
            for e in events:
                d = e['date']
                if d not in grouped:
                    grouped[d] = []
                grouped[d].append(e)

            for date, e_list in grouped.items():
                summary_lines.append(f"📆 *{date}*:")
                for e in e_list:
                    summary_lines.append(f"  ⏰ {e['time']} — {e['summary']}")
                summary_lines.append("")

            await update.message.reply_text("\n".join(summary_lines), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error in weekly schedule: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении расписания: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # (Same implementation as before, but keeping it inside the class)
        text = update.message.text
        if not text:
            return

        status_msg = await update.message.reply_text("🧠 Thinking...")
        
        try:
            data = self.brain.classify_and_process(text)
            logging.info(f"AI Classification: {data}")
            
            category = data.get("category", "Note")
            result = None
            
            try:
                if category == "Task":
                    result = self.notion.add_to_projects(data)
                    folder = "Projects/Tasks"
                elif category == "Resource":
                    result = self.notion.add_to_resources(data)
                    folder = "Resources"
                elif category == "Event":
                    result = self.calendar.add_event(
                        summary=data.get("title"),
                        start_time=data.get("start_time"),
                        end_time=data.get("end_time"),
                        description=data.get("summary")
                    )
                    folder = "Google Calendar"
                else:
                    result = self.notion.add_to_inbox(data)
                    folder = "Inbox"
            except Exception as e:
                logging.error(f"Notion Error: {e}")
                await status_msg.edit_text(f"❌ Notion Error: {e}\n(Category: {category})")
                return

            if result:
                notion_url = result.get("url", "#")
                await status_msg.edit_text(
                    f"✅ Saved as **{category}** in **{folder}**\n"
                    f"📌 Title: {data.get('title')}\n"
                    f"🔗 [View in Notion]({notion_url})",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(f"❌ Error saving to Notion.")
        except Exception as e:
            logging.error(f"General Error: {e}")
            await status_msg.edit_text(f"❌ An error occurred: {e}")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🎙️ Transcribing voice...")
        voice_file = await update.message.voice.get_file()
        file_path = "temp_voice.ogg"
        await voice_file.download_to_drive(file_path)
        text = self.brain.transcribe_voice(file_path)
        os.remove(file_path)
        await update.message.reply_text(f"📝 Transcript: {text}")
        update.message.text = text
        await self.handle_message(update, context)

    async def post_init(self, application):
        """Setup bot commands menu."""
        from telegram import BotCommand
        commands = [
            BotCommand("summary", "Сводка задач и событий на сегодня"),
            BotCommand("week", "Расписание на неделю")
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        proxy_url = os.getenv("SOCKS5_PROXY")
        builder = ApplicationBuilder().token(self.token).post_init(self.post_init)
        
        if proxy_url:
            print(f"Connecting to Telegram via proxy: {proxy_url}")
            builder.proxy(proxy_url)
            builder.get_updates_proxy(proxy_url)

        # Initialize job queue
        application = builder.build()
        job_queue = application.job_queue

        # Schedule daily summary
        try:
            h, m = map(int, self.summary_time.split(":"))
            job_queue.run_daily(self.send_daily_summary, time=time(hour=h, minute=m))
            print(f"Summary scheduled for {self.summary_time}")
        except Exception as e:
            print(f"Error scheduling job: {e}")
        
        # Handlers
        application.add_handler(CommandHandler("summary", self.manual_summary)) 
        application.add_handler(CommandHandler("week", self.week_schedule))
        application.add_handler(CallbackQueryHandler(self.complete_task, pattern="^done_"))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        
        print("Bot is running...")
        application.run_polling()

if __name__ == '__main__':
    bot = SecondBrainBot()
    bot.run()
