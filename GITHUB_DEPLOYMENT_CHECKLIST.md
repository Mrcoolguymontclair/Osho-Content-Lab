# GitHub Deployment Checklist

## Pre-Deployment

### 1. Clean Up Sensitive Data
- [ ] Remove any API keys from code
- [ ] Remove database files (`channels.db`)
- [ ] Remove video/audio files
- [ ] Remove music MP3s (keep structure)
- [ ] Check no hardcoded secrets

### 2. Verify Files
- [ ] `.gitignore` properly configured
- [ ] `requirements.txt` complete
- [ ] `packages.txt` (for ffmpeg)
- [ ] `README.md` comprehensive
- [ ] `DEPLOYMENT.md` clear
- [ ] `setup.sh` executable

### 3. Test Locally
```bash
# Clean install test
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run new_vid_gen.py
```

## Deployment Steps

### Step 1: Push to GitHub

```bash
# Stage all files
git add .

# Commit
git commit -m "Initial deployment: YouTube Shorts automation with AI learning"

# Push
git push origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click "New app"
3. Select repository
4. Main file: `new_vid_gen.py`
5. Add secrets:
```toml
GROQ_API_KEY = "your_key"
PEXELS_API_KEY = "your_key"
```
6. Deploy

### Step 3: Test Deployment

- [ ] UI loads correctly
- [ ] Can add channel
- [ ] OAuth works
- [ ] Settings save
- [ ] Dashboard displays

## Post-Deployment

### Update Repository
```bash
git add .
git commit -m "Update: [description]"
git push origin main
```

### Monitor
- Check Streamlit Cloud logs
- Verify no errors
- Test all features

## Full Automation (VPS)

If deploying to VPS for full automation:

### 1. Server Setup
```bash
# SSH to server
ssh user@your-server

# Clone repo
git clone https://github.com/yourusername/youtube-shorts-automation.git
cd youtube-shorts-automation

# Run setup
chmod +x setup.sh
./setup.sh
```

### 2. Configure Secrets
```bash
nano .streamlit/secrets.toml
# Add your API keys
```

### 3. Start Services
```bash
# Streamlit UI
nohup streamlit run new_vid_gen.py --server.port 8501 &

# Daemon
nohup python3 youtube_daemon.py &
```

### 4. Verify
- Access UI: http://your-server-ip:8501
- Check daemon: `ps aux | grep youtube_daemon`
- Monitor logs: `tail -f daemon.log`

## Troubleshooting

### Streamlit Cloud
- **Issue**: App won't start
  - Check logs in Streamlit dashboard
  - Verify requirements.txt
  - Check for import errors

- **Issue**: Secrets not working
  - Re-enter in Streamlit dashboard
  - Check TOML formatting

### VPS Deployment
- **Issue**: FFmpeg not found
  ```bash
  apt install ffmpeg  # Ubuntu
  brew install ffmpeg # macOS
  ```

- **Issue**: Port 8501 not accessible
  ```bash
  # Check firewall
  ufw allow 8501
  ```

- **Issue**: Daemon stops
  ```bash
  # Check logs
  tail -f daemon.log
  
  # Restart
  python3 youtube_daemon.py
  ```

## Quick Commands

### Git
```bash
# Status
git status

# Stage all
git add .

# Commit
git commit -m "message"

# Push
git push origin main

# Pull latest
git pull origin main
```

### Server Management
```bash
# Check running processes
ps aux | grep -E "streamlit|daemon"

# Kill process
pkill -f streamlit
pkill -f youtube_daemon

# Restart
nohup streamlit run new_vid_gen.py --server.port 8501 &
nohup python3 youtube_daemon.py &

# View logs
tail -f streamlit.log
tail -f daemon.log
```

### Database
```bash
# Check channels
sqlite3 channels.db "SELECT id, name, status FROM channels"

# Check recent videos
sqlite3 channels.db "SELECT title, status FROM videos ORDER BY id DESC LIMIT 5"

# Check errors
sqlite3 channels.db "SELECT message FROM logs WHERE level='error' ORDER BY timestamp DESC LIMIT 10"
```

## Support

- Documentation: See markdown files in repo
- Issues: GitHub Issues
- Updates: `git pull origin main`

---

**Ready to deploy!** 🚀
