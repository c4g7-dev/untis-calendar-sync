# Setup Guide

Complete step-by-step instructions for setting up WebUntis to Google Calendar sync.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Google Calendar API Setup](#google-calendar-api-setup)
4. [WebUntis Configuration](#webuntis-configuration)
5. [First Sync](#first-sync)
6. [Automation Setup](#automation-setup)
7. [Verification](#verification)

## System Requirements

### Software
- Linux/macOS/WSL
- Python 3.8 or higher
- Git
- Chrome or Chromium browser

### Accounts
- WebUntis account with valid credentials
- Google account with Calendar access

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/untis-calendar-sync.git
cd untis-calendar-sync
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python3 --version
pip list | grep google-api
pip list | grep selenium
```

## Google Calendar API Setup

### Step 1: Create Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name: "WebUntis Calendar Sync"
4. Click "Create"

### Step 2: Enable Calendar API

1. In the project dashboard, go to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click "Enable"

### Step 3: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External
   - App name: "WebUntis Sync"
   - Support email: your email
   - Scopes: Skip (we'll add later)
   - Test users: Add your email
4. Application type: "Desktop app"
5. Name: "WebUntis Desktop Client"
6. Click "Create"

### Step 4: Download Credentials

1. Click the download icon next to your new OAuth 2.0 Client ID
2. Save the file as `credentials.json` in the project root
3. Verify file structure matches `credentials.json.example`

## WebUntis Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` and fill in your details:

```bash
UNTIS_SCHOOL='YourSchoolName'      # e.g., 'Example High School'
UNTIS_USERNAME='your.username'      # Your WebUntis username
UNTIS_PASSWORD='your_password'      # Your WebUntis password
UNTIS_WEEKS=4                       # Number of weeks to sync (1-8)
UNTIS_HEADLESS=true                 # Run browser in background
```

### 3. Find Your School Name

Your school name is in the WebUntis URL:
```
https://[SERVER].webuntis.com/WebUntis/?school=[SCHOOL_NAME]
```

Example:
```
https://neilo.webuntis.com/WebUntis/?school=Example+School
→ UNTIS_SCHOOL='Example School'
```

### 4. Test Configuration

```bash
source .env
echo "School: $UNTIS_SCHOOL"
echo "User: $UNTIS_USERNAME"
echo "Weeks: $UNTIS_WEEKS"
```

## First Sync

### 1. Make Scripts Executable

```bash
chmod +x *.sh *.py
```

### 2. Run Full Sync

```bash
./run_full_sync.sh
```

This will:
1. Open browser for Google authentication (first time only)
2. Log into WebUntis
3. Extract schedule data
4. Create calendar events

### 3. Authenticate with Google

On first run:
1. Browser opens automatically
2. Log in to your Google account
3. Click "Allow" to grant calendar access
4. Close browser when done

Token is saved to `token.pickle` for future use.

### 4. Verify Extraction

Check extracted data:

```bash
ls -lh weekly_data/
cat weekly_data/week_1.json | python3 -m json.tool | less
```

### 5. Check Calendar

Open Google Calendar and verify events were created.

Look for:
- Orange colored events
- Subject names as titles
- Room locations
- 10-minute reminder

## Automation Setup

### Option 1: Cron (Linux/macOS)

```bash
# Open crontab
crontab -e

# Add this line (adjust path):
*/30 * * * * /full/path/to/untis-calendar-sync/auto_sync.sh >> /full/path/to/logs/cron.log 2>&1
```

Save and exit.

### Option 2: systemd Timer (Linux)

Create `/etc/systemd/system/untis-sync.service`:

```ini
[Unit]
Description=WebUntis Calendar Sync
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/untis-calendar-sync
ExecStart=/path/to/untis-calendar-sync/auto_sync.sh
StandardOutput=append:/path/to/logs/cron.log
StandardError=append:/path/to/logs/cron.log
```

Create `/etc/systemd/system/untis-sync.timer`:

```ini
[Unit]
Description=Run WebUntis sync every 30 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl enable untis-sync.timer
sudo systemctl start untis-sync.timer
```

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Name: "WebUntis Calendar Sync"
4. Trigger: Daily, repeat every 30 minutes
5. Action: Start a program
6. Program: `C:\path\to\python.exe`
7. Arguments: `C:\path\to\auto_sync.sh`
8. Finish

## Verification

### Check Sync Status

```bash
./check_status.sh
```

Expected output:
```
System Status
=============
CRONTAB: Active
STATUS SERVER: Running
SYNC STATUS:
  Last Sync: 2025-10-23 23:00:00
  Next in: 27 minutes
  Weeks: 4 | Lessons: 67
```

### View Logs

```bash
# Latest sync log
tail -f logs/full_sync_*.log

# Cron log
tail -f logs/cron.log

# All logs
ls -lth logs/
```

### Test Duplicate Prevention

Run sync twice:

```bash
./run_full_sync.sh
# Wait for completion
./run_full_sync.sh
```

Second run should show:
```
✓ Neu erstellt: 0
⊘ Übersprungen (Duplikate): 67
```

### Start Dashboard

```bash
python3 status_server.py
```

Open browser: `http://localhost:8080/dashboard`

## Troubleshooting

### "Module not found" Error

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Google Auth Fails

1. Delete `token.pickle`
2. Run `./run_full_sync.sh` again
3. Re-authenticate in browser

### WebUntis Login Fails

1. Verify credentials in `.env`
2. Test login manually on WebUntis website
3. Check school name format

### No Events Created

1. Check parsed data: `cat parsed_lessons_all_weeks.json`
2. Verify Calendar ID in `auth.py`
3. Check Google Calendar API quota

### Selenium/Chrome Issues

```bash
# Install Chrome/Chromium
sudo apt update
sudo apt install chromium-browser

# Or on macOS
brew install --cask google-chrome
```

### Duplicate Events

```bash
python3 remove_duplicates.py
```

## Next Steps

1. **Customize Colors**: Edit `untis_sync_improved.py` line 448
2. **Adjust Reminders**: Edit `untis_sync_improved.py` line 451
3. **Change Sync Frequency**: Edit crontab timing
4. **Monitor Dashboard**: Keep `status_server.py` running

## Support

- Read the [README](README.md) for detailed documentation
- Check [GitHub Issues](https://github.com/YOUR_USERNAME/untis-calendar-sync/issues)
- Review logs in `logs/` directory

## Security Notes

- Never commit `.env` file
- Never commit `credentials.json`
- Never commit `token.pickle`
- Keep these files secure and private
- Use `.gitignore` properly

## Maintenance

### Update Dependencies

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Clean Old Logs

```bash
find logs/ -name "*.log" -mtime +30 -delete
```

### Backup Configuration

```bash
cp .env .env.backup
cp credentials.json credentials.json.backup
```

### Reset Everything

```bash
# Stop automation
crontab -r

# Clear data
rm -rf weekly_data/*.json
rm -f parsed_lessons_all_weeks.json
rm -f sync_status.json
rm -f token.pickle

# Start fresh
./run_full_sync.sh
```
