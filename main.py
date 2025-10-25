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
from flask import Flask

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    return "MealsBot is running!", 200

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "MealsBot"}, 200

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
        
        # Check if user is already a family member
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_active FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result:
            if result[0]:  # User is active family member
                welcome_message = f"""
🍽️ Welcome back, {first_name}!

You're already registered as a family member. Here's what you can do:

**Available Commands:**
/survey - Request a meal survey
/my_responses - View your recent responses
/help - Show help information

The bot will automatically send weekly surveys every Monday at 9:00 AM.

Let's plan your meals! 🍳
                """
            else:  # User was deactivated
                welcome_message = f"""
👋 Hi {first_name}!

You were previously registered but have been removed from the family group. 
Please contact the admin to be added back to the family meal planning.

**Available Commands:**
/help - Show help information
                """
        else:
            # New user - only admin can add them
            cursor.execute('''
                INSERT INTO family_members (user_id, username, first_name, last_name, is_active)
                VALUES (?, ?, ?, ?, 0)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
            
            welcome_message = f"""
👋 Hi {first_name}!

Thanks for your interest in MealsBot! You're not yet registered as a family member.

**To join the family meal planning:**
1. Contact the admin to be added to the family group
2. Once added, you'll receive weekly meal surveys
3. You'll be able to use all bot features

**Available Commands:**
/help - Show help information

**Note:** Only the admin can add family members for security.
            """
        
        conn.close()
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_text = """
🍽️ **MealsBot Help**

**How it works:**
1. Every Monday at 9:00 AM, I'll send a survey asking about your meal needs
2. You can select which meals you need for each day of the week
3. The admin gets a summary of everyone's needs
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
        user_id = update.effective_user.id
        
        # Check if user is an active family member
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_active FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            await update.message.reply_text(
                "❌ You're not registered as an active family member.\n\n"
                "Please contact the admin to be added to the family meal planning group."
            )
            return
        
        await self.send_meal_survey(update.effective_chat.id, user_id)
    
    async def my_responses_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's recent meal responses."""
        user_id = update.effective_user.id
        
        # Check if user is an active family member
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_active FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            await update.message.reply_text(
                "❌ You're not registered as an active family member.\n\n"
                "Please contact the admin to be added to the family meal planning group."
            )
            conn.close()
            return
        
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
            [InlineKeyboardButton("➕ Add Family Member", callback_data="admin_add_family")],
            [InlineKeyboardButton("📅 Send Survey Now", callback_data="admin_send_survey")],
            [InlineKeyboardButton("📈 Weekly Summary", callback_data="admin_weekly_summary")],
            [InlineKeyboardButton("👥 Send Survey to Group", callback_data="admin_send_group_survey")],
            [InlineKeyboardButton("🧪 Test Callback", callback_data="test_callback")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup
        )
    
    async def group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /group command to explain group functionality."""
        group_info = """
👥 **Group Functionality**

This bot works great in family groups! Here's how:

**For Family Groups:**
• Add the bot to your family group chat
• Admin can use `/admin` → "Send Survey to Group"
• Each family member gets their own personalized survey
• Only you can modify your own responses (secure!)

**How It Works:**
1. Admin sends group surveys using `/admin`
2. Each family member sees their own survey
3. Click buttons to select meals (✅/❌)
4. Click "Submit Survey" when done
5. Admin can view all responses

**Commands:**
/start - Register with the bot
/survey - Get your personal survey
/admin - Admin panel (admin only)
/group - Show this group info

**Privacy:** Each person can only see and modify their own responses!
        """
        await update.message.reply_text(group_info)
    
    async def send_meal_survey(self, chat_id: int, user_id: int):
        """Send a meal survey to a specific user or group."""
        week_start = self.get_week_start()
        
        # Get user's name for personalization
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT first_name FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        user_name = result[0] if result else "Family Member"
        conn.close()
        
        message_text = f"""
🍽️ **Weekly Meal Survey - Week of {week_start}**

Hi {user_name}! Please let us know which meals you'll need this week:

**Instructions:**
• Click the buttons below to select your meals
• Selected meals will show ✅
• Unselected meals will show ❌
• Click "Submit Survey" when done

Let's plan the perfect week of meals! 🍳
        """
        
        keyboard = []
        for day in self.days:
            day_buttons = []
            for meal_type in self.meal_types:
                callback_data = f"meal_{day.lower()}_{meal_type}_{user_id}"
                day_buttons.append(InlineKeyboardButton(
                    f"{meal_type.title()[:3]} ❌", 
                    callback_data=callback_data
                ))
            keyboard.append([InlineKeyboardButton(f"📅 {day}", callback_data="day_header")] + day_buttons)
        
        keyboard.append([
            InlineKeyboardButton("👀 Review Selection", callback_data=f"review_survey_{user_id}"),
            InlineKeyboardButton("✅ Submit Survey", callback_data=f"submit_survey_{user_id}")
        ])
        
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
        
        logger.info(f"Callback received: {data} from user {user_id}")
        
        if data.startswith("meal_"):
            # Handle meal selection
            parts = data.split("_")
            day = parts[1].title()
            meal_type = parts[2]
            target_user_id = int(parts[3]) if len(parts) > 3 else user_id
            
            # Only allow the target user to modify their responses
            if user_id != target_user_id:
                await query.message.reply_text("❌ You can only modify your own meal preferences.")
                return
            
            # Toggle meal response
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            week_start = self.get_week_start()
            
            # Check if response exists
            cursor.execute('''
                SELECT response FROM meal_responses
                WHERE user_id = ? AND week_start = ? AND day = ? AND meal_type = ?
            ''', (target_user_id, week_start, day, meal_type))
            
            result = cursor.fetchone()
            current_response = result[0] if result else None
            
            if current_response is None:
                # Insert new response
                cursor.execute('''
                    INSERT INTO meal_responses (user_id, week_start, meal_type, day, response)
                    VALUES (?, ?, ?, ?, ?)
                ''', (target_user_id, week_start, meal_type, day, True))
                new_response = True
            else:
                # Toggle existing response
                new_response = not current_response
                cursor.execute('''
                    UPDATE meal_responses SET response = ?
                    WHERE user_id = ? AND week_start = ? AND day = ? AND meal_type = ?
                ''', (new_response, target_user_id, week_start, day, meal_type))
            
            conn.commit()
            conn.close()
            
            # Create new keyboard with updated button text
            status = "✅" if new_response else "❌"
            button_text = f"{meal_type.title()[:3]} {status}"
            
            # Recreate the keyboard with updated button
            new_keyboard = []
            for row in query.message.reply_markup.inline_keyboard:
                new_row = []
                for button in row:
                    if button.callback_data == data:
                        # Create new button with updated text
                        new_button = InlineKeyboardButton(button_text, callback_data=data)
                        new_row.append(new_button)
                    else:
                        new_row.append(button)
                new_keyboard.append(new_row)
            
            new_reply_markup = InlineKeyboardMarkup(new_keyboard)
            await query.edit_message_reply_markup(reply_markup=new_reply_markup)
        
        elif data.startswith("review_survey_"):
            # Handle survey review
            target_user_id = int(data.split("_")[2])
            
            # Only allow the target user to review their survey
            if user_id != target_user_id:
                await query.message.reply_text("❌ You can only review your own survey.")
                return
            
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            week_start = self.get_week_start()
            cursor.execute('''
                SELECT meal_type, day, response
                FROM meal_responses
                WHERE user_id = ? AND week_start = ?
                ORDER BY day, meal_type
            ''', (target_user_id, week_start))
            
            responses = cursor.fetchall()
            conn.close()
            
            if not responses:
                await query.message.reply_text(
                    "📝 **No meals selected yet!**\n\n"
                    "Please select at least one meal before reviewing your survey."
                )
            else:
                # Get user's name
                conn = sqlite3.connect('meals_bot.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT first_name FROM family_members WHERE user_id = ?
                ''', (target_user_id,))
                result = cursor.fetchone()
                user_name = result[0] if result else "Family Member"
                conn.close()
                
                review_text = f"👀 **Survey Review - {user_name}**\n"
                review_text += f"**Week of {week_start}**\n\n"
                
                current_day = None
                selected_count = 0
                for meal_type, day, response in responses:
                    if day != current_day:
                        review_text += f"📅 **{day}:**\n"
                        current_day = day
                    
                    if response:
                        review_text += f"  ✅ {meal_type.title()}\n"
                        selected_count += 1
                
                review_text += f"\n📊 **Total meals selected: {selected_count}**\n\n"
                review_text += "Click 'Submit Survey' when you're ready, or continue selecting meals."
                
                await query.message.reply_text(review_text)
        
        elif data.startswith("submit_survey_"):
            # Handle survey submission
            target_user_id = int(data.split("_")[2])
            
            # Only allow the target user to submit their survey
            if user_id != target_user_id:
                await query.message.reply_text("❌ You can only submit your own survey.")
                return
            
            conn = sqlite3.connect('meals_bot.db')
            cursor = conn.cursor()
            
            week_start = self.get_week_start()
            cursor.execute('''
                SELECT COUNT(*) FROM meal_responses
                WHERE user_id = ? AND week_start = ?
            ''', (target_user_id, week_start))
            
            response_count = cursor.fetchone()[0]
            conn.close()
            
            if response_count == 0:
                await query.message.reply_text(
                    "⚠️ Please select at least one meal before submitting!"
                )
            else:
                # Get user's name
                conn = sqlite3.connect('meals_bot.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT first_name FROM family_members WHERE user_id = ?
                ''', (target_user_id,))
                result = cursor.fetchone()
                user_name = result[0] if result else "Family Member"
                conn.close()
                
                await query.message.reply_text(
                    f"✅ **Survey Submitted Successfully, {user_name}!**\n\n"
                    "Thank you for your responses. The admin will be notified of your meal preferences for this week. "
                    "You can update your responses anytime using /survey."
                )
                
                # Notify admin of new submission
                try:
                    await self.application.bot.send_message(
                        chat_id=self.admin_user_id,
                        text=f"📝 **New Survey Submission**\n\n"
                             f"**User:** {user_name}\n"
                             f"**Week:** {week_start}\n"
                             f"**Meals Selected:** {response_count}\n\n"
                             f"Use `/admin` → 'View All Responses' to see details."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin of submission: {e}")
        
        elif data == "test_callback":
            await query.message.reply_text("✅ Callback test successful! Buttons are working.")
        
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
        elif data == "admin_add_family":
            await self.show_pending_family_members(query)
        elif data == "admin_send_survey":
            await self.send_survey_to_all(query)
        elif data == "admin_weekly_summary":
            await self.show_weekly_summary(query)
        elif data == "admin_send_group_survey":
            await self.send_group_survey(query)
        elif data.startswith("activate_"):
            await self.activate_family_member(query, data)
        elif data.startswith("deactivate_"):
            await self.deactivate_family_member(query, data)
    
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
            ORDER BY is_active DESC, first_name
        ''')
        
        members = cursor.fetchall()
        conn.close()
        
        members_text = "👥 **Family Members Management**\n\n"
        keyboard = []
        
        for user_id, first_name, last_name, username, is_active in members:
            name = f"{first_name} {last_name}" if last_name else first_name
            if username:
                name += f" (@{username})"
            
            status = "🟢 Active" if is_active else "🔴 Inactive"
            members_text += f"• {name} - {status}\n"
            
            if is_active:
                keyboard.append([
                    InlineKeyboardButton(f"❌ Remove {first_name}", callback_data=f"deactivate_{user_id}")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(f"✅ Activate {first_name}", callback_data=f"activate_{user_id}")
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        members_text += "\n**Select an action:**"
        
        await query.message.reply_text(members_text, reply_markup=reply_markup)
    
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
        failed_count = 0
        
        for (user_id,) in active_members:
            try:
                await self.send_meal_survey(user_id, user_id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send survey to user {user_id}: {e}")
                failed_count += 1
        
        # Send detailed report to admin
        report_text = f"📤 **Survey Distribution Complete!**\n\n"
        report_text += f"✅ **Successfully sent:** {sent_count} surveys\n"
        
        if failed_count > 0:
            report_text += f"❌ **Failed to send:** {failed_count} surveys\n"
            report_text += f"*Some users may have blocked the bot or have privacy settings preventing messages.*\n"
        
        report_text += f"\n📊 **Total active family members:** {len(active_members)}"
        
        await query.message.reply_text(report_text)
    
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
    
    async def send_group_survey(self, query):
        """Send surveys to all active family members in the current chat (group)."""
        chat_id = query.message.chat_id
        
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
                await self.send_meal_survey(chat_id, user_id)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send group survey to user {user_id}: {e}")
        
        await query.message.reply_text(
            f"📤 Group surveys sent to {sent_count} family members!\n\n"
            "Each family member can only modify their own responses. "
            "The surveys are personalized and secure."
        )
    
    async def show_pending_family_members(self, query):
        """Show pending family members waiting to be added."""
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, first_name, last_name, username
            FROM family_members
            WHERE is_active = 0
            ORDER BY first_name
        ''')
        
        pending_members = cursor.fetchall()
        conn.close()
        
        if not pending_members:
            await query.message.reply_text(
                "✅ **No Pending Family Members**\n\n"
                "All users who have contacted the bot are already active family members."
            )
            return
        
        members_text = "👥 **Pending Family Members**\n\n"
        keyboard = []
        
        for user_id, first_name, last_name, username in pending_members:
            name = f"{first_name} {last_name}" if last_name else first_name
            if username:
                name += f" (@{username})"
            
            members_text += f"• {name}\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ Add {first_name}", callback_data=f"activate_{user_id}"),
                InlineKeyboardButton(f"❌ Reject {first_name}", callback_data=f"deactivate_{user_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            members_text + "\n**Select an action:**",
            reply_markup=reply_markup
        )
    
    async def activate_family_member(self, query, data):
        """Activate a family member."""
        logger.info(f"Activation callback received: {data}")
        user_id = int(data.split("_")[1])
        logger.info(f"Extracted user_id: {user_id}")
        
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE family_members SET is_active = 1 WHERE user_id = ?
        ''', (user_id,))
        
        cursor.execute('''
            SELECT first_name FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        name = result[0] if result else "Family Member"
        
        conn.commit()
        conn.close()
        
        # Send confirmation to admin
        await query.message.reply_text(
            f"✅ **{name} has been added to the family!**\n\n"
            f"They can now use /survey and receive weekly meal surveys.\n"
            f"📱 They will be notified of their activation."
        )
        
        # Notify the user that they've been activated
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"🎉 **Welcome to the family, {name}!**\n\n"
                     "You've been approved by the admin and can now use all bot features:\n\n"
                     "• Use `/survey` to plan your meals\n"
                     "• Receive weekly surveys automatically\n"
                     "• View your responses with `/my_responses`\n\n"
                     "Let's start planning your meals! 🍽️"
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} of activation: {e}")
    
    async def deactivate_family_member(self, query, data):
        """Deactivate a family member."""
        user_id = int(data.split("_")[1])
        
        conn = sqlite3.connect('meals_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE family_members SET is_active = 0 WHERE user_id = ?
        ''', (user_id,))
        
        cursor.execute('''
            SELECT first_name FROM family_members WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        name = result[0] if result else "Family Member"
        
        conn.commit()
        conn.close()
        
        # Send confirmation to admin
        await query.message.reply_text(
            f"❌ **{name} has been removed from the family.**\n\n"
            f"They will no longer receive surveys or have access to family features.\n"
            f"📱 They will be notified of their removal."
        )
        
        # Notify the user that they've been deactivated
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"👋 **Hello {name}**\n\n"
                     "You have been removed from the family meal planning group by the admin.\n\n"
                     "You will no longer receive:\n"
                     "• Weekly meal surveys\n"
                     "• Family meal planning updates\n"
                     "• Access to family features\n\n"
                     "If this was done in error, please contact the admin."
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} of deactivation: {e}")
    
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
    
    def run_sync(self):
        """Run the bot synchronously for Railway deployment."""
        self.application = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("survey", self.survey_command))
        self.application.add_handler(CommandHandler("my_responses", self.my_responses_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("group", self.group_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        logger.info("MealsBot started successfully!")
        logger.info("Weekly surveys will be sent every Monday at 9:00 AM")
        
        # Start Flask server in a separate thread for health checks
        import threading
        flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False), daemon=True)
        flask_thread.start()
        
        # Start the bot using the synchronous method
        self.application.run_polling()

if __name__ == "__main__":
    try:
        bot = MealsBot()
        logger.info("Starting MealsBot with synchronous method")
        bot.run_sync()
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
