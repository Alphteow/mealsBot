# MealsBot Deployment Guide

## Quick Start

1. **Get a Telegram Bot Token:**
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token you receive

2. **Get your Telegram User ID:**
   - Message @userinfobot on Telegram
   - It will reply with your user ID

3. **Set up environment variables:**
   - Copy `env.example` to `.env`
   - Fill in your bot token and user ID

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

## Deployment Options

### Option 1: Railway (FREE - Recommended)

Railway offers a generous free tier perfect for Telegram bots:

1. **Sign up at [railway.app](https://railway.app)** with GitHub
2. **Create a new project** and connect your GitHub repository
3. **Set environment variables** in Railway dashboard:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_USER_ID`: Your Telegram user ID
4. **Deploy automatically** - Railway will detect Python and deploy

**Free tier includes:**
- 500 hours of usage per month
- Automatic deployments from GitHub
- Built-in environment variable management
- No credit card required

### Option 2: Render (FREE)

Render provides free hosting for web services:

1. **Sign up at [render.com](https://render.com)** with GitHub
2. **Create a new Web Service** from your GitHub repository
3. **Configure:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
4. **Set environment variables** in Render dashboard
5. **Deploy**

**Free tier includes:**
- 750 hours per month
- Automatic deployments
- SSL certificates included

### Option 3: Fly.io (FREE)

Fly.io offers free allowances for small applications:

1. **Install Fly CLI** and sign up
2. **Create fly.toml** configuration file
3. **Deploy:**
   ```bash
   fly launch
   fly secrets set BOT_TOKEN=your_bot_token
   fly secrets set ADMIN_USER_ID=your_user_id
   fly deploy
   ```

**Free tier includes:**
- 3 shared-cpu-1x 256MB VMs
- 160GB-hours per month
- Global edge deployment

### Option 2: Railway

1. **Connect your GitHub repository to Railway**
2. **Set environment variables in Railway dashboard:**
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_USER_ID`: Your Telegram user ID
3. **Deploy automatically**

### Option 3: DigitalOcean App Platform

1. **Create a new app** from GitHub repository
2. **Set environment variables:**
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_USER_ID`: Your Telegram user ID
3. **Deploy**

### Option 4: VPS/Server

1. **Set up a VPS** (Ubuntu recommended)
2. **Install Python 3.11+** and pip
3. **Clone repository:**
   ```bash
   git clone your-repo-url
   cd mealsBot
   ```
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up environment variables:**
   ```bash
   export BOT_TOKEN=your_bot_token
   export ADMIN_USER_ID=your_user_id
   ```
6. **Run with process manager:**
   ```bash
   # Using PM2
   npm install -g pm2
   pm2 start main.py --name mealsbot --interpreter python3
   
   # Or using systemd
   sudo systemctl enable mealsbot
   sudo systemctl start mealsbot
   ```

## Bot Features

### For Family Members:
- `/start` - Welcome message and registration
- `/help` - Show help information
- `/survey` - Request a meal survey
- `/my_responses` - View your responses

### For Admin:
- `/admin` - Admin panel with options:
  - View all family responses
  - Manage family members
  - Send survey to everyone
  - View weekly summary

### Automatic Features:
- **Weekly Surveys**: Sent every Monday at 9:00 AM
- **Interactive Buttons**: Easy meal selection
- **Data Persistence**: All responses saved to database
- **Real-time Updates**: Change responses anytime

## Database

The bot uses SQLite database (`meals_bot.db`) with two tables:
- `family_members`: Stores family member information
- `meal_responses`: Stores meal preferences by week

## Troubleshooting

### Common Issues:

1. **Bot not responding:**
   - Check if bot token is correct
   - Verify bot is not blocked by users
   - Check server logs for errors

2. **Surveys not sending:**
   - Ensure scheduler is running
   - Check if family members are active
   - Verify timezone settings

3. **Database errors:**
   - Check file permissions
   - Ensure SQLite is installed
   - Verify database file is writable

### Logs:
- Check application logs for detailed error messages
- Use `heroku logs --tail` for Heroku deployments
- Check system logs for VPS deployments

## Security Notes

- Keep your bot token secret
- Only share admin privileges with trusted family members
- Regularly backup your database
- Monitor bot usage and responses

## Customization

You can customize:
- Survey timing (change in `schedule_weekly_surveys()`)
- Meal types (modify `self.meal_types`)
- Days of the week (modify `self.days`)
- Message templates
- Database schema

## Support

For issues or questions:
1. Check the logs first
2. Verify environment variables
3. Test bot commands manually
4. Check Telegram Bot API status
