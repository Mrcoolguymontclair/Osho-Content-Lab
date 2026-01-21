# Automatic Quota Reset & Channel Resume System

**Status:** [OK] Fully Implemented & Tested
**Date:** January 11, 2026

---

## Overview

The system now automatically handles API quota exhaustion and channel resumption **without any manual intervention**. When API quotas run out, channels pause automatically and resume automatically when quotas reset at midnight.

---

## How It Works

### 1. **Quota Monitoring** (Every Hour)

The daemon runs a background worker that checks API quotas every hour:

```
 Quota Monitor
   → Checks API quotas: Groq, YouTube, Pexels
   → Checks if it's midnight (quota reset time)
   → Auto-resets quotas at midnight
   → Auto-resumes paused channels after reset
```

### 2. **Quota Exhaustion Detection**

When an error occurs, the system automatically detects quota-related errors:

**Quota Keywords Detected:**
- `quota`
- `rate limit`
- `limit exceeded`
- `too many requests`
- `429` (HTTP status code)

**API Detection:**
- **Groq errors:** Contains "groq" or "llama"
- **YouTube errors:** Contains "youtube" or "google"
- **Pexels errors:** Contains "pexels"

When detected:
```
[WARNING] GROQ quota exhausted at 2026-01-11 18:30:00
   Will auto-resume at next quota reset (midnight)
```

### 3. **Channel Pausing**

When quota is exhausted:
- Channel marked as `is_active = 0`
- Error logged to database
- System continues monitoring

### 4. **Automatic Reset at Midnight**

At midnight (or whenever quota reset time is reached):
```
[REFRESH] QUOTA RESET - 2026-01-12 00:00:00
[OK] GROQ quota reset
[OK] YOUTUBE quota reset
[OK] PEXELS quota reset
```

### 5. **Automatic Channel Resume**

After quota reset:
```
[REFRESH] Quota reset detected - resuming 1 paused channel(s)...
   [OK] Resumed: RankRiot

[OK] All systems resumed
```

---

## API Quotas Tracked

| API | Daily Limit | Reset Time |
|-----|-------------|------------|
| **Groq** | 100,000 tokens | Midnight PT |
| **YouTube** | 10,000 units | Midnight PT |
| **Pexels** | 20,000/month (~667/day) | Monthly |

---

## Database Schema

### `api_quotas` Table

```sql
CREATE TABLE api_quotas (
    id INTEGER PRIMARY KEY,
    api_name TEXT UNIQUE,           -- groq, youtube, pexels
    quota_limit INTEGER,            -- daily limit
    quota_used INTEGER,             -- current usage
    quota_remaining INTEGER,        -- remaining quota
    last_reset TIMESTAMP,           -- when last reset
    next_reset TIMESTAMP,           -- when next reset
    is_exhausted BOOLEAN,           -- currently exhausted?
    exhausted_at TIMESTAMP,         -- when exhausted
    auto_resume BOOLEAN DEFAULT 1   -- auto-resume enabled?
)
```

---

## Manual Operations

### Check Current Quota Status

```bash
sqlite3 channels.db "SELECT api_name, quota_remaining, is_exhausted, next_reset FROM api_quotas;"
```

### Manually Reset a Quota

```python
from quota_manager import reset_quota

reset_quota('groq')  # Reset Groq quota
reset_quota('youtube')  # Reset YouTube quota
reset_quota('pexels')  # Reset Pexels quota
```

### Manually Resume Channels

```python
from quota_manager import auto_resume_paused_channels

auto_resume_paused_channels()
```

### Force Quota Reset (All APIs)

```python
from quota_manager import reset_all_quotas

reset_all_quotas()
```

---

## Testing

Run the test suite to verify functionality:

```bash
python3 test_quota_reset.py
```

**Expected Output:**
```
[OK] TEST PASSED - Automatic quota reset and channel resume working!

What this means:
  • When API quotas are exhausted, channels pause automatically
  • At midnight, quotas reset automatically
  • Paused channels resume automatically after quota reset
  • No manual intervention needed!
```

---

## Daemon Integration

The quota monitor runs automatically when the daemon starts:

```python
# In youtube_daemon.py

# Start Quota Monitor (checks every hour, resets at midnight)
quota_thread = threading.Thread(
    target=quota_monitor_worker,
    daemon=True,
    name="QuotaMonitor"
)
quota_thread.start()
```

**Monitor Output:**
```
 Starting Quota Monitor...
   → Checks API quotas every hour
   → Auto-resets quotas at midnight
   → Auto-resumes paused channels when quotas reset
[OK] Quota monitor active
```

---

## Logs

### When Quota Exhausts

```
[12:30:45] [WARNING] [CH2] [quota] Groq API quota exhausted - will auto-resume at midnight
[WARNING] GROQ quota exhausted at 2026-01-11 12:30:45
   Will auto-resume at next quota reset (midnight)
```

### When Quota Resets

```
[REFRESH] QUOTA RESET - 2026-01-12 00:00:00
[OK] GROQ quota reset at 2026-01-12 00:00:00
[OK] YOUTUBE quota reset at 2026-01-12 00:00:00
[OK] PEXELS quota reset at 2026-01-12 00:00:00
```

### When Channel Resumes

```
[REFRESH] Quota reset detected - resuming 1 paused channel(s)...
   [OK] Resumed: RankRiot
[00:00:12] [INFO] [CH2] [auto_resume] Channel auto-resumed after quota reset
[OK] All systems resumed
```

---

## Troubleshooting

### Channel not resuming after quota reset?

**Check logs table:**
```bash
sqlite3 channels.db "SELECT * FROM logs WHERE category LIKE '%quota%' ORDER BY timestamp DESC LIMIT 10;"
```

**Check quota status:**
```bash
python3 -c "from quota_manager import get_quota_status_summary; import json; print(json.dumps(get_quota_status_summary(), indent=2))"
```

### Force immediate resume:

```bash
python3 -c "from quota_manager import reset_all_quotas, auto_resume_paused_channels; reset_all_quotas(); auto_resume_paused_channels()"
```

### Manually reactivate channel:

```bash
sqlite3 channels.db "UPDATE channels SET is_active = 1 WHERE name = 'RankRiot';"
```

---

## What Happens When Quotas Run Out?

### [ERROR] Before (Manual Intervention Required)

1. Groq API quota exhausted
2. Video generation fails repeatedly
3. Channel accumulates errors
4. Channel pauses after 20 errors
5. **User must manually check next day**
6. **User must manually restart daemon**
7. **User must manually reactivate channel**

### [OK] After (Fully Automatic)

1. Groq API quota exhausted
2. System detects quota error
3. Quota marked as exhausted in database
4. Channel continues with fallback (if available)
5. **At midnight: Quota resets automatically**
6. **Channel resumes automatically**
7. **No manual intervention needed!**

---

## Benefits

[OK] **Zero Downtime**: System resumes automatically at midnight
[OK] **No Manual Checks**: No need to check if quotas reset
[OK] **No Manual Restarts**: Daemon handles everything
[OK] **Smart Detection**: Automatically detects quota errors
[OK] **Multi-API Support**: Handles Groq, YouTube, and Pexels
[OK] **Graceful Degradation**: Channels pause instead of crashing
[OK] **Complete Logging**: All quota events logged to database

---

## Files

| File | Purpose |
|------|---------|
| `quota_manager.py` | Core quota tracking and reset logic |
| `youtube_daemon.py` | Integrated quota monitoring worker |
| `test_quota_reset.py` | Test suite for quota system |
| `AUTO_QUOTA_RESET.md` | This documentation |

---

## Future Enhancements

Potential improvements:

- [ ] Slack/Email notifications when quota exhausted
- [ ] Quota usage tracking and predictions
- [ ] Per-channel quota limits
- [ ] Priority system (some channels continue with reduced quota)
- [ ] Quota usage analytics dashboard
- [ ] Smart scheduling based on quota availability

---

**Last Updated:** 2026-01-11
**Status:** [OK] Production Ready
**Tested:** [OK] All tests passing
