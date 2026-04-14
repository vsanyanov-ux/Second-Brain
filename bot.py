import os
import logging
import asyncio
import datetime
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
                        next_action_info = f" (🎯 {t['next_action']})" if t.get('next_action') else ""
                        summary_lines.append(f"  🔹 {t['title']}{next_action_info}")
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

    async def todo_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Fetches and sends all active tasks with their next actions."""
        status_msg = await update.message.reply_text("📋 Fetching your To-Do list...")
        try:
            tasks = self.notion.get_active_tasks()
            if not tasks:
                await status_msg.edit_text("✅ No active tasks found in Notion!")
                return

            lines = ["📋 **Your Active Tasks**:\n"]
            for t in tasks:
                line = f"🔹 **{t['title']}** ({t['status']})"
                # Try to get next action if we have it in the task data
                # We might need to update notion_api.py to fetch more fields
                next_action = t.get("next_action")
                if next_action:
                    line += f"\n   🎯 _Next_: {next_action}"
                lines.append(line)
            
            await status_msg.edit_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error in todo_list: {e}")
            await status_msg.edit_text(f"❌ Error fetching tasks: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if not text:
            return

        status_msg = await update.message.reply_text("🧠 Analyzing...")
        
        try:
            data = self.brain.classify_and_process(text)
            logging.info(f"AI Classification: {data}")
            
            # The Receipt (Audit Log)
            self._log_transaction(text, data)
            
            # The Bouncer (Confidence Filter)
            confidence = data.get("confidence", 1.0)
            if confidence < 0.7:
                await status_msg.delete()
                keyboard = [
                    [InlineKeyboardButton("Project", callback_data=f"fix_Project_{text[:30]}"),
                     InlineKeyboardButton("Idea", callback_data=f"fix_Idea_{text[:30]}")],
                    [InlineKeyboardButton("Person", callback_data=f"fix_Person_{text[:30]}"),
                     InlineKeyboardButton("Admin", callback_data=f"fix_Admin_{text[:30]}")],
                    [InlineKeyboardButton("Ignore", callback_data="ignore")]
                ]
                await update.message.reply_text(
                    f"🤔 I'm not entirely sure (Confidence: {confidence:.2f}).\n"
                    f"AI suggests: **{data.get('category')}**\n"
                    f"What is this?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
                return

            await self._save_and_respond(update, status_msg, data)
            
        except Exception as e:
            logging.error(f"General Error: {e}")
            await status_msg.edit_text(f"❌ An error occurred: {e}")

    async def _save_and_respond(self, update, status_msg, data):
        """Helper to save to Notion/Calendar and send confirmation."""
        category = data.get("category", "Idea")
        result = None
        
        try:
            if category == "Project":
                result = self.notion.add_to_projects(data)
                folder = "Projects"
            elif category == "Person":
                result = self.notion.add_to_resources(data)
                folder = "People/Resources"
            elif category == "Admin":
                result = self.notion.add_to_projects(data) # Mapping Admin to Projects for now
                folder = "Admin/Projects"
            elif category == "Event":
                result = self.calendar.add_event(
                    summary=data.get("title"),
                    start_time=data.get("start_time"),
                    end_time=data.get("end_time"),
                    description=data.get("summary")
                )
                folder = "Google Calendar"
            else: # Idea
                result = self.notion.add_to_inbox(data)
                folder = "Inbox/Ideas"
        except Exception as e:
            logging.error(f"Notion/Calendar Error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Error saving to **{folder}**:\n`{str(e)[:200]}`", parse_mode="Markdown")
            return

        if result:
            notion_url = result.get("url", "#")
            # The Fix Button (via buttons)
            keyboard = [[InlineKeyboardButton("🔄 Change Category", callback_data=f"fix_prompt_{result.get('id')}")]]
            await status_msg.edit_text(
                f"✅ Saved as **{category}** in **{folder}**\n"
                f"📌 Title: {data.get('title')}\n"
                f"🔗 [View in Notion]({notion_url})",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await status_msg.edit_text(f"❌ Unexpected Error: Saving to **{folder}** returned no result.", parse_mode="Markdown")

    def _log_transaction(self, text, data):
        """The Receipt: Log everything to audit_log.json."""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "input": text,
            "decision": data
        }
        try:
            import json
            logs = []
            if os.path.exists("audit_log.json"):
                with open("audit_log.json", "r", encoding="utf-8") as f:
                    logs = json.load(f)
            if isinstance(logs, list):
                logs.append(log_entry)
                logs = logs[-100:]
            else:
                logs = [log_entry]
            with open("audit_log.json", "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Logging error: {e}")

    async def fix_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """The Fix Button: Handler for correction callbacks."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "ignore":
            await query.edit_message_text("👌 Ignored.")
            return

        if query.data.startswith("fix_prompt_"):
            page_id = query.data.replace("fix_prompt_", "")
            keyboard = [
                [InlineKeyboardButton("Project", callback_data=f"move_{page_id}_Project"),
                 InlineKeyboardButton("Idea", callback_data=f"move_{page_id}_Idea")],
                [InlineKeyboardButton("Person", callback_data=f"move_{page_id}_Person"),
                 InlineKeyboardButton("Admin", callback_data=f"move_{page_id}_Admin")]
            ]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if query.data.startswith("move_"):
            _, page_id, new_cat = query.data.split("_")
            # Logic to move would be complex, for now we just update a tag/status if possible
            # Or just send a confirmation that it's a feature to be implemented.
            await query.edit_message_text(f"🔄 Request to move to **{new_cat}** received (Implementation in progress).", parse_mode="Markdown")

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
            BotCommand("todo", "Список всех задач и следующих шагов"),
            BotCommand("week", "Расписание на неделю")
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        builder = ApplicationBuilder().token(self.token).post_init(self.post_init)
        
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
        application.add_handler(CommandHandler("todo", self.todo_list))
        application.add_handler(CommandHandler("week", self.week_schedule))
        application.add_handler(CallbackQueryHandler(self.complete_task, pattern="^done_"))
        application.add_handler(CallbackQueryHandler(self.fix_callback, pattern="^(fix_|move_|ignore)"))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        
        print("Bot is running...")
        application.run_polling()

if __name__ == '__main__':
    bot = SecondBrainBot()
    bot.run()
