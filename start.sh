#!/bin/bash

# MealsBot Startup Script
# This script helps set up and run the MealsBot

echo "🍽️ MealsBot Setup Script"
echo "========================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or later."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "✅ pip3 found"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your bot token and user ID"
    echo "   You can get your bot token from @BotFather"
    echo "   You can get your user ID from @userinfobot"
    exit 1
fi

echo "✅ .env file found"

# Run setup test
echo "🧪 Running setup tests..."
python3 test_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Starting MealsBot..."
    python3 main.py
else
    echo "❌ Setup tests failed. Please fix the issues above."
    exit 1
fi
