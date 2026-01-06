# Deployment Guide

## Streamlit Community Cloud Deployment

### Important Notes
- **Streamlit Cloud**: UI-only (no daemon, no video generation)
- **Full Automation**: Requires VPS/cloud server (AWS, DigitalOcean, etc.)

### Deploy UI to Streamlit Cloud

1. **Prepare Repository**
```bash
# Make sure all changes are committed
git add .
git commit -m "Prepare for deployment"
git push origin main
```

2. **Deploy on Streamlit**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Main file: `new_vid_gen.py`
   - Click "Deploy"

3. **Configure Secrets**

In Streamlit dashboard, add secrets (Settings → Secrets):

```toml
GROQ_API_KEY = "gsk_..."
PEXELS_API_KEY = "..."
```

4. **Limitations on Streamlit Cloud**
   - ❌ No daemon (no automatic video generation)
   - ❌ No FFmpeg (videos can't be created)
   - ❌ No persistent database (resets on reboot)
   - ✅ UI works (manual configuration, viewing)
   - ✅ OAuth works (channel authentication)

**Recommendation**: Use Streamlit Cloud for UI + separate server for automation

---

## Full Deployment (VPS/Cloud Server)

For complete automation with video generation.

### Option 1: DigitalOcean Droplet

1. **Create Droplet**
   - Ubuntu 22.04 LTS
   - 2GB RAM minimum (4GB recommended)
   - Choose region close to you

2. **Connect via SSH**
```bash
ssh root@your_droplet_ip
```

3. **Install Dependencies**
```bash
# Update system
apt update && apt upgrade -y

# Install Python and FFmpeg
apt install -y python3 python3-pip ffmpeg

# Install git
apt install -y git
```

4. **Clone Repository**
```bash
cd /root
git clone https://github.com/yourusername/youtube-shorts-automation.git
cd youtube-shorts-automation
```

5. **Install Python Packages**
```bash
pip3 install -r requirements.txt
```

6. **Configure Secrets**
```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

Add:
```toml
GROQ_API_KEY = "your_key"
PEXELS_API_KEY = "your_key"
```

7. **Run Streamlit (Background)**
```bash
nohup streamlit run new_vid_gen.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &
```

8. **Run Daemon (Background)**
```bash
nohup python3 youtube_daemon.py > daemon.log 2>&1 &
```

9. **Access UI**
   - Open browser: `http://your_droplet_ip:8501`
   - Configure firewall to allow port 8501

10. **Keep Running on Reboot**

Create systemd service:

```bash
# Streamlit service
cat > /etc/systemd/system/youtube-ui.service << 'EOL'
[Unit]
Description=YouTube Shorts UI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/youtube-shorts-automation
ExecStart=/usr/bin/python3 -m streamlit run new_vid_gen.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Daemon service
cat > /etc/systemd/system/youtube-daemon.service << 'EOL'
[Unit]
Description=YouTube Shorts Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/youtube-shorts-automation
ExecStart=/usr/bin/python3 youtube_daemon.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Enable and start
systemctl daemon-reload
systemctl enable youtube-ui youtube-daemon
systemctl start youtube-ui youtube-daemon

# Check status
systemctl status youtube-ui
systemctl status youtube-daemon
```

### Option 2: AWS EC2

Similar to DigitalOcean, but:
- Use t2.medium instance (4GB RAM)
- Ubuntu 22.04 AMI
- Configure security group: Allow port 8501
- Follow same installation steps

### Option 3: Docker (Advanced)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "new_vid_gen.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t youtube-shorts .
docker run -d -p 8501:8501 --name youtube-ui youtube-shorts
docker run -d --name youtube-daemon youtube-shorts python3 youtube_daemon.py
```

---

## Post-Deployment Setup

1. **Access UI**
   - Navigate to `http://your_server_ip:8501`

2. **Add Channel**
   - Click "Add New Channel"
   - Configure settings
   - Authenticate with YouTube OAuth

3. **Add Music** (Optional)
   - SSH to server
   - Upload MP3s to `music/` folder
   - Run `python3 add_music.py`

4. **Monitor Logs**
```bash
# Streamlit logs
tail -f streamlit.log

# Daemon logs
tail -f daemon.log

# Database logs
sqlite3 channels.db "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 20"
```

5. **Update Application**
```bash
cd /root/youtube-shorts-automation
git pull origin main
systemctl restart youtube-ui youtube-daemon
```

---

## Security Best Practices

1. **Firewall**
```bash
ufw allow 8501/tcp
ufw allow 22/tcp
ufw enable
```

2. **HTTPS** (Recommended)

Use nginx + Let's Encrypt:
```bash
apt install -y nginx certbot python3-certbot-nginx

# Configure nginx reverse proxy
# Get SSL certificate
certbot --nginx -d yourdomain.com
```

3. **Environment Variables**

Instead of `secrets.toml`, use environment variables:
```bash
export GROQ_API_KEY="your_key"
export PEXELS_API_KEY="your_key"
```

4. **Backup Database**
```bash
# Daily backup cron
crontab -e

# Add:
0 2 * * * cp /root/youtube-shorts-automation/channels.db /root/backups/channels_$(date +\%Y\%m\%d).db
```

---

## Troubleshooting

### Streamlit won't start
```bash
# Check logs
tail -f streamlit.log

# Check port
netstat -tulpn | grep 8501
```

### Daemon not running
```bash
# Check logs
tail -f daemon.log

# Restart
systemctl restart youtube-daemon
```

### Out of memory
```bash
# Check memory
free -h

# Increase swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### FFmpeg errors
```bash
# Verify installation
ffmpeg -version
which ffmpeg

# Reinstall if needed
apt install --reinstall ffmpeg
```

---

## Cost Estimates

### Streamlit Cloud
- **Free tier**: 1 app, limited resources
- **Cost**: $0/month
- **Use case**: UI only, no automation

### DigitalOcean Droplet
- **Basic**: $12/month (2GB RAM)
- **Recommended**: $24/month (4GB RAM)
- **Use case**: Full automation

### AWS EC2
- **t2.medium**: ~$30-35/month
- **Use case**: Full automation

### API Costs
- **Groq**: Free tier available
- **Pexels**: Free (200 requests/hour)
- **YouTube API**: Free (10k quota/day)
- **Harmony Snippets**: Varies by plan

---

## Scaling

### Multiple Channels
System supports unlimited channels per instance.

### Multiple Instances
Run separate instances for different channel groups:
- Instance 1: Channels 1-10
- Instance 2: Channels 11-20
- etc.

### Load Balancing
Not needed unless >50 channels per instance.

---

## Monitoring

### Health Checks
```bash
# Check if processes running
ps aux | grep -E "streamlit|youtube_daemon"

# Check last video generation
sqlite3 channels.db "SELECT * FROM videos ORDER BY id DESC LIMIT 5"

# Check errors
sqlite3 channels.db "SELECT * FROM logs WHERE level='error' ORDER BY timestamp DESC LIMIT 10"
```

### Alerts (Optional)

Set up email alerts for critical errors:
```bash
# Install mailutils
apt install -y mailutils

# Add to daemon error handler
echo "Critical error: $error" | mail -s "YouTube Automation Alert" your@email.com
```

---

## Next Steps

1. ✅ Deploy UI (Streamlit Cloud or VPS)
2. ✅ Deploy Daemon (VPS only)
3. ✅ Configure channels
4. ✅ Add music library
5. ✅ Monitor performance
6. ✅ Scale as needed

**Support**: Check README.md or open GitHub issue
