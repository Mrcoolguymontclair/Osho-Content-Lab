# Raspberry Pi Deployment Guide

Comprehensive guide for deploying Osho Content Lab backend on Raspberry Pi.

**Date:** 2026-01-20
**Status:** FEASIBLE with optimization

---

## Executive Summary

**YES, deploying to Raspberry Pi is reasonable** with proper optimization. Here's the analysis:

### Raspberry Pi 4 (8GB) - RECOMMENDED
- **CPU:** Quad-core ARM Cortex-A72 @ 1.5GHz
- **RAM:** 8GB LPDDR4
- **Storage:** 128GB+ microSD or SSD (recommended)
- **Verdict:** **EXCELLENT CHOICE** ✓

### Raspberry Pi 5 (8GB) - IDEAL
- **CPU:** Quad-core ARM Cortex-A76 @ 2.4GHz
- **RAM:** 8GB LPDDR4X
- **Storage:** NVMe SSD support
- **Verdict:** **BEST CHOICE** ✓✓

### Raspberry Pi 3B+ (1GB) - NOT RECOMMENDED
- Too limited for video processing
- Would struggle with FFmpeg operations

---

## Hardware Requirements

### Minimum Requirements (Pi 4 8GB)
- **CPU:** Quad-core ARM @ 1.5GHz+
- **RAM:** 8GB (video processing is memory-intensive)
- **Storage:** 128GB+ (videos accumulate)
- **Power:** Official 5V 3A USB-C power supply
- **Cooling:** Active cooling (fan + heatsinks)
- **Network:** Ethernet (more reliable than WiFi)

### Recommended Setup (Pi 5 8GB)
- **CPU:** Quad-core ARM @ 2.4GHz+
- **RAM:** 8GB
- **Storage:** 256GB NVMe SSD via M.2 HAT
- **Power:** Official 5V 5A USB-C PD supply
- **Cooling:** Active cooling case (mandatory)
- **Network:** Gigabit Ethernet
- **Extras:** Real-time clock (RTC) module

### Storage Breakdown
```
/home/osho-content-lab/
├── channels.db (50MB)
├── temp/ (2-5GB during generation, cleaned after)
├── output/ (1GB, videos uploaded then cleaned)
├── music/ (100MB)
├── tokens/ (1MB)
├── logs/ (500MB, rotated)
└── [Python + dependencies] (2GB)
```

**Estimated:** 10GB base + 5-10GB working space = **20-30GB total**

---

## Performance Analysis

### Current Workload Characteristics

**Video Generation Process:**
1. **Script Generation** (Groq API) - 2-5 seconds (network-bound)
2. **Clip Search** (Pexels API) - 1-3 seconds (network-bound)
3. **Clip Downloads** (Parallel) - 20-40 seconds (network-bound, now 5x faster)
4. **Video Processing** (FFmpeg) - 30-60 seconds (CPU-bound)
5. **Enhancement** (FFmpeg) - 20-40 seconds (CPU-bound)
6. **Upload** (YouTube API) - 15-30 seconds (network-bound)

**Total:** 90-180 seconds per video (1.5-3 minutes)

### Raspberry Pi 4 Performance Expectations

**FFmpeg on ARM:**
- Hardware H.264 encoding support (VideoCore VI)
- **Expected:** 2-3x slower than x86 desktop
- **Video generation:** 180-360 seconds (3-6 minutes) per video

**With optimization:**
- Use hardware encoding flags
- Reduce quality preset (medium → fast)
- Limit concurrent processing
- **Optimized:** 120-240 seconds (2-4 minutes) per video

**Posting Interval:** Default 4 hours (14,400 seconds)
- Can easily generate video in 4 minutes
- Leaves **99%+ idle time** for other tasks
- **Conclusion:** More than sufficient

### Raspberry Pi 5 Performance

**Faster CPU (60% improvement):**
- Video generation: 90-180 seconds (1.5-3 minutes)
- Comparable to desktop performance
- Can handle faster posting intervals

---

## Bottlenecks & Solutions

### Bottleneck 1: FFmpeg Video Processing
**Issue:** ARM CPU slower than x86 for video encoding

**Solutions:**
1. **Use Hardware Encoding:**
   ```python
   # In constants.py
   VIDEO_CODEC = 'h264_v4l2m2m'  # Hardware encoder on Pi
   VIDEO_PRESET = 'fast'  # Lighter preset
   ```

2. **Optimize FFmpeg:**
   ```bash
   # Install FFmpeg with hardware acceleration
   sudo apt-get install ffmpeg
   ```

3. **Reduce Quality Slightly:**
   ```python
   VIDEO_CRF = 25  # Instead of 23 (minimal quality loss)
   SHORTS_BITRATE = '3M'  # Instead of 4M
   ```

### Bottleneck 2: Parallel Processing
**Issue:** 8GB RAM shared between multiple processes

**Solutions:**
1. **Limit Concurrent Downloads:**
   ```python
   downloader = ParallelDownloader(max_workers=3)  # Instead of 5
   ```

2. **Sequential Video Generation:**
   ```python
   # Process one channel at a time instead of parallel
   ```

3. **Memory Monitoring:**
   ```python
   # Health monitor will alert on high memory
   monitor = get_health_monitor()
   monitor.start()
   ```

### Bottleneck 3: Storage I/O
**Issue:** microSD cards are slow

**Solutions:**
1. **Use SSD Storage:**
   - Boot from microSD, work on USB SSD
   - Or use NVMe HAT (Pi 5)

2. **Configure Temp Directory:**
   ```python
   # Mount SSD at /mnt/ssd
   TEMP_DIR = '/mnt/ssd/temp'
   OUTPUT_DIR = '/mnt/ssd/output'
   ```

3. **Aggressive Cleanup:**
   - Delete temp files immediately after use
   - Upload and delete output videos
   - Rotate logs daily

### Bottleneck 4: Network
**Issue:** WiFi can be unreliable

**Solutions:**
1. **Use Ethernet:** Always prefer wired connection
2. **Retry Logic:** Already implemented (exponential backoff)
3. **Resume Support:** For large uploads

---

## Optimization Configuration

### Create `pi_config.py`

```python
"""
Raspberry Pi optimized configuration.
"""

# Video quality optimized for ARM
VIDEO_CODEC = 'h264_v4l2m2m'  # Hardware encoder
VIDEO_PRESET = 'fast'  # Lighter workload
VIDEO_CRF = 25  # Slightly lower quality
SHORTS_BITRATE = '3M'  # Reduced bitrate
SHORTS_FPS = 30  # Standard FPS

# Parallel processing limits
MAX_DOWNLOAD_WORKERS = 3  # Instead of 5
MAX_CONCURRENT_CHANNELS = 1  # Generate one at a time

# Memory limits
MAX_CACHE_SIZE = 500  # Instead of 1000
MAX_CACHE_MEMORY = 52428800  # 50MB instead of 100MB

# Storage on SSD
TEMP_DIR = '/mnt/ssd/temp'
OUTPUT_DIR = '/mnt/ssd/output'
LOGS_DIR = '/mnt/ssd/logs'

# Aggressive cleanup
CLEANUP_TEMP_IMMEDIATELY = True
DELETE_UPLOADED_VIDEOS = True

# Health monitoring
ENABLE_HEALTH_MONITORING = True
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MEMORY_WARNING_THRESHOLD = 0.85  # Alert at 85%
```

---

## Installation Instructions

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3 python3-pip python3-venv git
sudo apt-get install -y ffmpeg
sudo apt-get install -y libatlas-base-dev  # For NumPy

# Install cooling (if not built-in)
# Ensure fan is running and temps stay < 70°C
```

### 2. Mount SSD (Recommended)

```bash
# Format USB SSD as ext4
sudo mkfs.ext4 /dev/sda1

# Mount
sudo mkdir /mnt/ssd
sudo mount /dev/sda1 /mnt/ssd

# Auto-mount on boot
echo '/dev/sda1 /mnt/ssd ext4 defaults 0 2' | sudo tee -a /etc/fstab
```

### 3. Clone and Setup

```bash
# Clone repository
cd /home/pi
git clone https://github.com/your-repo/Osho-Content-Lab.git
cd Osho-Content-Lab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Configure for Pi
cp pi_config.py backend/config/pi_overrides.py
```

### 4. Configure Environment

```bash
# Create .env file
nano .env
```

Add:
```bash
GROQ_API_KEY=your_key
PEXELS_API_KEY=your_key
ENVIRONMENT=raspberry_pi
TEMP_DIR=/mnt/ssd/temp
OUTPUT_DIR=/mnt/ssd/output
```

### 5. Setup Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/osho-daemon.service
```

Add:
```ini
[Unit]
Description=Osho Content Lab Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Osho-Content-Lab
Environment=PATH=/home/pi/Osho-Content-Lab/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/pi/Osho-Content-Lab/venv/bin/python3 backend/core/daemon_keeper.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable osho-daemon
sudo systemctl start osho-daemon
```

### 6. Monitor System

```bash
# Check status
sudo systemctl status osho-daemon

# View logs
journalctl -u osho-daemon -f

# Check temperature
vcgencmd measure_temp

# Check memory
free -h
```

---

## Frontend Deployment Options

### Option 1: Separate Frontend Server (Recommended)

**Setup:**
- Frontend (Streamlit) on your main computer/laptop
- Backend (daemon) on Raspberry Pi
- Communicate via API or shared database

**Pros:**
- Better performance for UI
- Easy to access from any device
- No impact on video generation

**Implementation:**
```python
# Backend exposes API
# Frontend connects to Pi's IP:port
# Or share database via network
```

### Option 2: Frontend on Pi (Lightweight)

**Setup:**
- Run Streamlit on Pi
- Access via Pi's IP address
- Use lightweight mode

**Pros:**
- All-in-one solution
- No additional hardware needed

**Cons:**
- Uses Pi resources
- Slower UI response

**Implementation:**
```bash
# Run on Pi
streamlit run frontend/new_vid_gen.py --server.port 8501
# Access from other devices: http://PI_IP:8501
```

### Option 3: Headless Mode (Best for Pi)

**Setup:**
- No UI on Pi
- Backend runs autonomously
- Monitor via logs or API

**Pros:**
- Maximum performance
- Minimal resource usage
- True "set and forget"

**Implementation:**
```bash
# Just run daemon
python3 backend/core/daemon_keeper.py

# Check logs remotely
ssh pi@raspberry-pi
tail -f /mnt/ssd/logs/osho_content_lab.log
```

---

## Monitoring and Maintenance

### Temperature Monitoring

```bash
# Add to cron (every 5 minutes)
*/5 * * * * /usr/bin/vcgencmd measure_temp >> /home/pi/temp_log.txt
```

**Safe operating temperature:** < 70°C
**Warning:** 70-80°C (throttling begins)
**Critical:** > 80°C (shut down)

### Storage Monitoring

```bash
# Check disk usage
df -h /mnt/ssd

# Auto-cleanup script
#!/bin/bash
# cleanup.sh
find /mnt/ssd/temp -type f -mtime +1 -delete
find /mnt/ssd/output -type f -mtime +1 -delete
find /mnt/ssd/logs -type f -mtime +7 -delete
```

Add to cron:
```bash
0 3 * * * /home/pi/cleanup.sh
```

### Health Dashboard

```python
# health_dashboard.py - simple Flask/FastAPI dashboard
from backend.utils.health_monitor import get_health_monitor

monitor = get_health_monitor()
report = monitor.get_health_report()
# Display as JSON or HTML
```

---

## Performance Benchmarks

### Expected Performance (Pi 4 8GB + SSD)

| Operation | Desktop | Pi 4 (stock) | Pi 4 (optimized) |
|-----------|---------|--------------|------------------|
| Script Generation | 3s | 3s | 3s |
| Clip Downloads (5) | 30s | 30s | 30s |
| Video Processing | 45s | 120s | 75s |
| Enhancement | 30s | 90s | 60s |
| Upload | 20s | 20s | 20s |
| **Total** | **128s** | **263s** | **188s** |

**Posting Interval:** 4 hours (14,400s)
**Generation Time:** 3.1 minutes
**Capacity:** Can handle posting every 5 minutes if needed

### Expected Performance (Pi 5 8GB + NVMe)

| Operation | Time |
|-----------|------|
| Script Generation | 3s |
| Clip Downloads | 25s |
| Video Processing | 50s |
| Enhancement | 35s |
| Upload | 20s |
| **Total** | **133s (2.2 min)** |

**Comparable to desktop performance!**

---

## Cost Analysis

### Hardware Costs

**Raspberry Pi 4 Setup:**
- Pi 4 8GB: $75
- Power Supply: $10
- Case with Fan: $15
- 256GB microSD: $30
- 256GB USB SSD: $30
- **Total: $160**

**Raspberry Pi 5 Setup:**
- Pi 5 8GB: $80
- Power Supply: $12
- Active Cooler: $8
- 256GB NVMe SSD: $35
- M.2 HAT: $15
- **Total: $150**

### Operating Costs

**Power Consumption:**
- Pi 4: 6-8W active, 3W idle
- Average: 5W (mostly idle)
- Annual cost: $5-10 (at $0.12/kWh)

**Compare to Desktop:**
- Desktop: 150-300W
- Annual cost: $150-300
- **Savings: $140-290/year**

---

## Pros and Cons

### Pros ✓

1. **Low Power:** $5-10/year vs $150-300 for desktop
2. **Always On:** Perfect for 24/7 automation
3. **Quiet:** Silent or near-silent operation
4. **Compact:** Fits anywhere
5. **Reliable:** No moving parts (with SSD)
6. **Affordable:** <$200 complete setup
7. **Remote Access:** Easy SSH management
8. **Sufficient Power:** Handles workload easily

### Cons ✗

1. **Slower Processing:** 2-3x slower than desktop
2. **Limited RAM:** 8GB max (vs 32GB+ desktop)
3. **ARM Architecture:** Some software compatibility issues
4. **Cooling Required:** Must monitor temperature
5. **SD Card Limitations:** Need SSD for reliability
6. **No Upgrades:** Can't upgrade RAM/CPU later

---

## Recommended Configuration

### For Your Use Case

**Backend on Raspberry Pi 5 8GB:**
- NVMe SSD for storage
- Active cooling
- Ethernet connection
- Headless mode (no UI)
- Systemd service for auto-start

**Frontend on Your Computer:**
- Run Streamlit UI locally
- Connect to Pi backend via network
- Or use web-based monitoring dashboard

**Result:**
- $150 one-time cost
- $10/year operating cost
- Professional 24/7 automation
- Remote access from anywhere
- Quiet and reliable

---

## Migration Path

### Phase 1: Reorganize (Current)
- Separate frontend/backend code
- Test on current system
- Ensure everything works

### Phase 2: Prepare Pi
- Order Raspberry Pi 5 + accessories
- Install OS and dependencies
- Setup SSD storage

### Phase 3: Deploy Backend
- Copy backend code to Pi
- Configure for ARM optimization
- Start daemon with systemd

### Phase 4: Connect Frontend
- Run frontend locally or remotely
- Connect to Pi backend
- Test full workflow

### Phase 5: Optimize
- Monitor performance
- Tune configuration
- Adjust posting intervals

---

## Conclusion

**Raspberry Pi deployment is HIGHLY RECOMMENDED for your use case.**

### Why It Works

1. **Workload is mostly network-bound** (API calls, uploads)
2. **Long posting intervals** (4 hours) give plenty of processing time
3. **Modern Pi 5 has excellent performance** (comparable to desktop)
4. **Cost-effective** ($150 vs $500+ desktop)
5. **Low power** (24/7 operation practical)
6. **All improvements support Pi** (parallel downloads, caching, error handling)

### Best Setup

**Recommended:** Raspberry Pi 5 8GB + NVMe SSD + Your Computer for Frontend

**Performance:** Will generate videos in 2-3 minutes (plenty fast for 4-hour interval)
**Cost:** $150 hardware + $10/year power
**Reliability:** Excellent with proper cooling
**Scalability:** Can handle multiple channels easily

**Verdict:** Go for it! 🎯

---

**Next Steps:**
1. Run reorganization script
2. Test new structure
3. Order Raspberry Pi 5 kit
4. Follow installation guide
5. Deploy and enjoy 24/7 automation!

---
