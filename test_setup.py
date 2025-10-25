#!/usr/bin/env python3
"""
Test script for MealsBot
This script helps verify that the bot is properly configured and can connect to Telegram.
"""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test if environment variables are properly set."""
    print("🔍 Testing environment variables...")
    
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_user_id = os.getenv('ADMIN_USER_ID')
    
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        print("   Please set BOT_TOKEN in your .env file")
        return False
    
    if not admin_user_id:
        print("❌ ADMIN_USER_ID not found in environment variables")
        print("   Please set ADMIN_USER_ID in your .env file")
        return False
    
    if bot_token == "your_telegram_bot_token_here":
        print("❌ BOT_TOKEN is still set to placeholder value")
        print("   Please replace with your actual bot token")
        return False
    
    if admin_user_id == "your_telegram_user_id":
        print("❌ ADMIN_USER_ID is still set to placeholder value")
        print("   Please replace with your actual user ID")
        return False
    
    print("✅ Environment variables are properly configured")
    return True

def test_imports():
    """Test if all required packages can be imported."""
    print("🔍 Testing package imports...")
    
    try:
        import telegram
        print(f"✅ python-telegram-bot version: {telegram.__version__}")
    except ImportError as e:
        print(f"❌ Failed to import telegram: {e}")
        print("   Run: pip install python-telegram-bot")
        return False
    
    try:
        import schedule
        print("✅ schedule package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import schedule: {e}")
        print("   Run: pip install schedule")
        return False
    
    try:
        import sqlite3
        print("✅ sqlite3 package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import sqlite3: {e}")
        print("   sqlite3 should be included with Python")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv package imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import dotenv: {e}")
        print("   Run: pip install python-dotenv")
        return False
    
    return True

def test_bot_connection():
    """Test if the bot can connect to Telegram."""
    print("🔍 Testing bot connection to Telegram...")
    
    try:
        from telegram import Bot
        import asyncio
        load_dotenv()
        
        bot_token = os.getenv('BOT_TOKEN')
        bot = Bot(token=bot_token)
        
        # Get bot info using asyncio
        async def get_bot_info():
            return await bot.get_me()
        
        bot_info = asyncio.run(get_bot_info())
        print(f"✅ Bot connected successfully!")
        print(f"   Bot name: {bot_info.first_name}")
        print(f"   Bot username: @{bot_info.username}")
        print(f"   Bot ID: {bot_info.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Telegram: {e}")
        print("   Check your bot token and internet connection")
        return False

def test_database():
    """Test database initialization."""
    print("🔍 Testing database initialization...")
    
    try:
        import sqlite3
        
        # Test database creation
        conn = sqlite3.connect('test_meals_bot.db')
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_family_members (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_meal_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                week_start DATE,
                meal_type TEXT,
                day TEXT,
                response BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Clean up test database
        os.remove('test_meals_bot.db')
        
        print("✅ Database initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🍽️ MealsBot Setup Test\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Package Imports", test_imports),
        ("Bot Connection", test_bot_connection),
        ("Database", test_database)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        if test_func():
            passed += 1
        else:
            print(f"\n❌ {test_name} test failed!")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Message your bot on Telegram")
        print("3. Use /start to begin")
    else:
        print("⚠️ Some tests failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Set up your .env file with correct values")
        print("3. Check your internet connection")
        print("4. Verify your bot token with @BotFather")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
