import logging
import os
import sqlite3
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database setup
def init_database():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect('meals_bot.db')
    cursor = conn.cursor()
    
    # Create family members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS family_members (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create meal responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            week_start DATE,
            meal_type TEXT,
            day TEXT,
            response BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES family_members (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

class MealsBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.admin_user_id = int(os.getenv('ADMIN_USER_ID', 0))
        self.application = None
        self.meal_types = ['breakfast', 'lunch', 'dinner']
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN not found in environment variables")
        
        init_database()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        
        # Add user to family members if not exists
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO family_members (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
        
        welcome_message = f"""
🍽️ Welcome to MealsBot, {first_name}!

This bot helps coordinate family meal planning. Here's what I can do:

📅 **Weekly Surveys**: I'll send you a survey every week to check which meals you need
🍳 **Meal Planning**: Help the house chef prepare meals accordingly
👨‍👩‍👧‍👦 **Family Coordination**: Keep everyone informed about meal plans

**Available Commands:**
/start - Show this welcome message
/help - Show help information
/survey - Manually trigger a meal survey
/my_responses - View your recent meal responses
/admin - Admin commands (admin only)

The bot will automatically send weekly surveys every Monday at 9:00 AM. You can also request a survey anytime using /survey.

Let's make meal planning easier for your family! 🏠✨
        """
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_text = """
🍽️ **MealsBot Help**

**How it works:**
1. Every Monday at 9:00 AM, I'll send a survey asking about your meal needs
2. You can select which meals you need for each day of the week
3. The house chef gets a summary of everyone's needs
4. You can also request surveys manually anytime

**Commands:**
/start - Welcome message and bot introduction
/help - Show this help message
/survey - Request a meal survey now
/my_responses - View your recent responses
/admin - Admin panel (admin only)

**Meal Survey:**
- Click the buttons to select which meals you need
- You can change your responses anytime before the week starts
- Responses are saved automatically

**Need Help?**
Contact the admin if you have any issues or suggestions!
        """
        await update.message.reply_text(help_text)
    
    async def survey_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /survey command to manually trigger a meal survey."""
        await self.send_meal_survey(update.effective_chat.id, update.effective_user.id)
    
    async def my_responses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's recent meal responses."""
        user_id = update.effective_user.id
        
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        # Get current week's responses
        week_start = self.get_week_start()
        cursor.execute('''
            SELECT meal_type, day, response, timestamp
            FROM meal_responses
            WHERE user_id = ? AND week_start = ?
            ORDER BY day, meal_type
        ''', (user_id, week_start))
        
        responses = cursor.fetchall()
        conn.close()
        
        if not responses:
            await update.message.reply_text("📝 You haven't responded to this week's survey yet. Use /survey to fill it out!")
            return
        
        response_text = f"📋 **Your Meal Responses for Week of {week_start}**\n\n"
        
        current_day = None
        for meal_type, day, response, timestamp in responses:
            if day != current_day:
                response_text += f"**{day}:**\n"
                current_day = day
            
            status = "✅ Yes" if response else "❌ No"
            response_text += f"  • {meal_type.title()}: {status}\n"
        
        await update.message.reply_text(response_text)
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands."""
        if update.effective_user.id != self.admin_user_id:
            await update.message.reply_text("❌ You don't have admin privileges.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 View All Responses", callback_data="admin_view_responses")],
            [InlineKeyboardButton("👥 Manage Family Members", callback_data="admin_manage_family")],
            [InlineKeyboardButton("📅 Send Survey Now", callback_data="admin_send_survey")],
            [InlineKeyboardButton("📈 Weekly Summary", callback_data="admin_weekly_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup
        )
    
    async def send_meal_survey(self, chat_id: int, user_id: int):
        """Send a meal survey to a specific user."""
        week_start = self.get_week_start()
        
        message_text = f"""
🍽️ **Weekly Meal Survey - Week of {week_start}**

Please let us know which meals you'll need this week (Monday to Sunday):

**Instructions:**
• Click the buttons below to select your meals
• ✅ = You need this meal
• ❌ = You don't need this meal
• You can change your responses anytime

Let's plan the perfect week of meals! 🍳
        """
        
        keyboard = []
        for day in self.days:
            day_buttons = []
            for meal_type in self.meal_types:
                callback_data = f"meal_{day.lower()}_{meal_type}"
                day_buttons.append(InlineKeyboardButton(
                    f"{meal_type.title()[:3]}", 
                    callback_data=callback_data
                ))
            keyboard.append([InlineKeyboardButton(f"📅 {day}", callback_data="day_header")] + day_buttons)
        
        keyboard.append([InlineKeyboardButton("✅ Submit Survey", callback_data="submit_survey")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data.startswith("meal_"):
            # Handle meal selection
            parts = data.split("_")
            day = parts[1].title()
            meal_type = parts[2]
            
            # Toggle meal response
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            week_start = self.get_week_start()
            
            # Check if response exists
            cursor.execute('''
                SELECT response FROM meal_responses
                WHERE user_id = ? AND week_start = ? AND day = ? AND meal_type = ?
            ''', (user_id, week_start, day, meal_type))
            
            result = cursor.fetchone()
            current_response = result[0] if result else None
            
            if current_response is None:
                # Insert new response
                cursor.execute('''
                    INSERT INTO meal_responses (user_id, week_start, meal_type, day, response)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, week_start, meal_type, day, True))
                new_response = True
            else:
                # Toggle existing response
                new_response = not current_response
                cursor.execute('''
                    UPDATE meal_responses SET response = ?
                    WHERE user_id = ? AND week_start = ? AND day = ? AND meal_type = ?
                ''', (new_response, user_id, week_start, day, meal_type))
            
            conn.commit()
            conn.close()
            
            # Update button text
            status = "✅" if new_response else "❌"
            button_text = f"{meal_type.title()[:3]} {status}"
            
            # Find and update the button
            for row in query.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == data:
                        button.text = button_text
                        break
            
            await query.edit_message_reply_markup(reply_markup=query.message.reply_markup)
            
            await query.message.reply_text(
                f"📝 Updated: {day} {meal_type.title()} - {'Yes' if new_response else 'No'}"
            )
        
        elif data == "submit_survey":
            # Handle survey submission
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            week_start = self.get_week_start()
            cursor.execute('''
                SELECT COUNT(*) FROM meal_responses
                WHERE user_id = ? AND week_start = ?
            ''', (user_id, week_start))
            
            response_count = cursor.fetchone()[0]
            conn.close()
            
            if response_count == 0:
                await query.message.reply_text(
                    "⚠️ Please select at least one meal before submitting!"
                )
            else:
                await query.message.reply_text(
                    "✅ **Survey Submitted Successfully!**\n\n"
                    "Thank you for your responses. The house chef will be notified of your meal preferences for this week. "
                    "You can update your responses anytime using /survey."
                )
        
        elif data.startswith("admin_"):
            await self.handle_admin_callback(query, data)
    
    async def handle_admin_callback(self, query, data):
        """Handle admin-specific callback queries."""
        if query.from_user.id != self.admin_user_id:
            await query.message.reply_text("❌ You don't have admin privileges.")
            return
        
        if data == "admin_view_responses":
            await self.show_all_responses(query)
        elif data == "admin_manage_family":
            await self.manage_family_members(query)
        elif data == "admin_send_survey":
            await self.send_survey_to_all(query)
        elif data == "admin_weekly_summary":
            await self.show_weekly_summary(query)
    
    async def show_all_responses(self, query):
        """Show all family members' responses for the current week."""
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        week_start = self.get_week_start()
        
        # Get all active family members
        cursor.execute('''
            SELECT user_id, first_name, last_name, username
            FROM family_members
            WHERE is_active = 1
        ''')
        
        family_members = cursor.fetchall()
        
        summary_text = f"📊 **Weekly Meal Summary - Week of {week_start}**\n\n"
        
        for user_id, first_name, last_name, username in family_members:
            name = f"{first_name} {last_name}" if last_name else first_name
            if username:
                name += f" (@{username})"
            
            summary_text += f"👤 **{name}**\n"
            
            # Get responses for this user
            cursor.execute('''
                SELECT meal_type, day, response
                FROM meal_responses
                WHERE user_id = ? AND week_start = ?
                ORDER BY day, meal_type
            ''', (user_id, week_start))
            
            responses = cursor.fetchall()
            
            if responses:
                current_day = None
                for meal_type, day, response in responses:
                    if day != current_day:
                        summary_text += f"  📅 {day}:\n"
                        current_day = day
                    
                    status = "✅" if response else "❌"
                    summary_text += f"    • {meal_type.title()}: {status}\n"
            else:
                summary_text += "  ⚠️ No responses yet\n"
            
            summary_text += "\n"
        
        conn.close()
        
        await query.message.reply_text(summary_text)
    
    async def manage_family_members(self, query):
        """Show family member management options."""
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, first_name, last_name, username, is_active
            FROM family_members
            ORDER BY first_name
        ''')
        
        members = cursor.fetchall()
        conn.close()
        
        members_text = "👥 **Family Members Management**\n\n"
        
        for user_id, first_name, last_name, username, is_active in members:
            name = f"{first_name} {last_name}" if last_name else first_name
            if username:
                name += f" (@{username})"
            
            status = "🟢 Active" if is_active else "🔴 Inactive"
            members_text += f"• {name} - {status}\n"
        
        members_text += "\n**Note:** Family members are automatically added when they use /start"
        
        await query.message.reply_text(members_text)
    
    async def send_survey_to_all(self, query):
        """Send survey to all active family members."""
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id FROM family_members WHERE is_active = 1
        ''')
        
        active_members = cursor.fetchall()
        conn.close()
        
        sent_count = 0
        for (user_id,) in active_members:
            try:
                await self.send_meal_survey(user_id, user_id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send survey to user {user_id}: {e}")
        
        await query.message.reply_text(
            f"📤 Survey sent to {sent_count} family members!"
        )
    
    async def show_weekly_summary(self, query):
        """Show a summary of the week's meal needs."""
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        week_start = self.get_week_start()
        
        summary_text = f"📈 **Weekly Meal Summary - Week of {week_start}**\n\n"
        
        for day in self.days:
            summary_text += f"📅 **{day}**\n"
            
            for meal_type in self.meal_types:
                cursor.execute('''
                    SELECT COUNT(*) FROM meal_responses
                    WHERE week_start = ? AND day = ? AND meal_type = ? AND response = 1
                ''', (week_start, day, meal_type))
                
                count = cursor.fetchone()[0]
                summary_text += f"  • {meal_type.title()}: {count} people\n"
            
            summary_text += "\n"
        
        conn.close()
        
        await query.message.reply_text(summary_text)
    
    def get_week_start(self) -> str:
        """Get the start date of the current week (Monday)."""
        today = datetime.now().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        return week_start.strftime('%Y-%m-%d')
    
    def schedule_weekly_surveys(self):
        """Schedule weekly surveys to be sent every Monday at 9:00 AM."""
        def send_weekly_survey():
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id FROM family_members WHERE is_active = 1
            ''')
            
            active_members = cursor.fetchall()
            conn.close()
            
            for (user_id,) in active_members:
                try:
                    # Use asyncio to run the async function
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.send_meal_survey(user_id, user_id))
                    loop.close()
                except Exception as e:
                    logger.error(f"Failed to send weekly survey to user {user_id}: {e}")
        
        schedule.every().monday.at("09:00").do(send_weekly_survey)
        logger.info("Weekly surveys scheduled for every Monday at 9:00 AM")
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread."""
        import threading
        
        def scheduler_loop():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
    
    async def run(self):
        """Run the bot."""
        self.application = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("survey", self.survey_command))
        self.application.add_handler(CommandHandler("my_responses", self.my_responses_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Schedule weekly surveys
        self.schedule_weekly_surveys()
        self.run_scheduler()
        
        logger.info("MealsBot started successfully!")
        logger.info("Weekly surveys will be sent every Monday at 9:00 AM")
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the bot running
        try:
            await self.application.updater.idle()
        finally:
            await self.application.stop()

if __name__ == "__main__":
    try:
        bot = MealsBot()
        import asyncio
        asyncio.run(bot.run())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
