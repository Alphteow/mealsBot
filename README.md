# MealsBot - Family Meal Planning Telegram Bot

A comprehensive Telegram bot that helps coordinate family meal planning by sending weekly surveys to check who needs breakfast, lunch, or dinner from Monday to Sunday.

## Features

- **Weekly Surveys**: Automatically sent every Monday at 9:00 AM
- **Interactive Buttons**: Easy meal selection with visual feedback
- **Family Management**: Automatic family member registration
- **Response Tracking**: View individual and family-wide meal preferences
- **Admin Panel**: Comprehensive management tools
- **Data Persistence**: SQLite database for reliable data storage
- **Real-time Updates**: Change responses anytime before the week starts

## Quick Start

### Option 1: Using the Startup Script (Recommended)
```bash
# Make the script executable and run it
chmod +x start.sh
./start.sh
```

### Option 2: Manual Setup
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your bot token and user ID
   ```

3. **Test your setup:**
   ```bash
   python test_setup.py
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Getting Your Bot Token

1. **Message @BotFather** on Telegram
2. **Create a new bot** with `/newbot`
3. **Follow the instructions** to get your bot token
4. **Get your User ID** by messaging @userinfobot
5. **Add both to your `.env` file**

## Bot Commands

### For Family Members:
- `/start` - Welcome message and registration
- `/help` - Show help information  
- `/survey` - Request a meal survey
- `/my_responses` - View your responses for current week

### For Admin:
- `/admin` - Admin panel with options:
  - View all family responses
  - Manage family members
  - Send survey to everyone
  - View weekly summary

## Deployment Options

### Cloud Platforms (Recommended)

#### Heroku
```bash
# Install Heroku CLI and login
heroku create your-meals-bot
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set ADMIN_USER_ID=your_user_id
git push heroku main
```

#### Railway
1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy automatically

#### DigitalOcean App Platform
1. Create app from GitHub repository
2. Set environment variables
3. Deploy

### Docker Deployment
```bash
# Using Docker Compose
docker-compose up -d

# Or using Docker directly
docker build -t mealsbot .
docker run -e BOT_TOKEN=your_token -e ADMIN_USER_ID=your_id mealsbot
```

### VPS/Server Deployment
```bash
# Clone and setup
git clone your-repo-url
cd mealsBot
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN=your_bot_token
export ADMIN_USER_ID=your_user_id

# Run with PM2
npm install -g pm2
pm2 start main.py --name mealsbot --interpreter python3
pm2 startup
pm2 save
```

## Database

The bot uses SQLite with two main tables:
- `family_members`: Stores family member information
- `meal_responses`: Stores meal preferences by week

Database file: `meals_bot.db` (created automatically)

## Configuration

### Environment Variables
- `BOT_TOKEN`: Your Telegram bot token (required)
- `ADMIN_USER_ID`: Your Telegram user ID (required)

### Customization Options
- **Survey timing**: Modify `schedule_weekly_surveys()` in `main.py`
- **Meal types**: Change `self.meal_types` array
- **Days**: Modify `self.days` array
- **Message templates**: Edit message strings in methods

## Testing

Run the test script to verify your setup:
```bash
python test_setup.py
```

This will check:
- Environment variables
- Package imports
- Bot connection
- Database initialization

## How It Works

1. **Family members** use `/start` to register
2. **Every Monday at 9:00 AM**, surveys are sent automatically
3. **Interactive buttons** let users select meals for each day
4. **Responses are saved** to the database in real-time
5. **Admin can view** summaries and manage the family
6. **House chef** gets organized meal planning data

## Troubleshooting

### Common Issues:

**Bot not responding:**
- Check bot token is correct
- Verify bot isn't blocked by users
- Check server logs for errors

**Surveys not sending:**
- Ensure scheduler is running
- Check family members are active
- Verify timezone settings

**Database errors:**
- Check file permissions
- Ensure SQLite is installed
- Verify database file is writable

### Getting Help:
1. Check application logs first
2. Run `python test_setup.py`
3. Verify environment variables
4. Test bot commands manually

## Security Notes

- Keep your bot token secret
- Only share admin privileges with trusted family members
- Regularly backup your database
- Monitor bot usage and responses

## Future Enhancements

Potential features to add:
- Email notifications for meal summaries
- Recipe suggestions based on preferences
- Analytics and meal planning insights
- Customizable survey timing
- Multiple family groups support

## License

This project is open source. Feel free to modify and distribute.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

**Made with love for families who love good food and good planning!**