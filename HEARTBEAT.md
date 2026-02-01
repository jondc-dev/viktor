# HEARTBEAT.md

## 📞 Phone Queue (PRIORITY - CHECK FIRST)
1. Read `~/.vonage/phone-queue.json`
2. For EACH message in `incoming` array:
   - Process the request with full memory/tools access
   - **Respond like a human** — casual, polite, warm. Not robotic.
   - Keep it short (1-2 sentences max, it's spoken aloud)
   - Use natural filler words occasionally ("yeah", "sure", "hmm")
   - Add response to `outgoing` array with the same `id`
   - Remove from `incoming` array
3. Write updated queue back to file

The caller is waiting on the line, so respond quickly but thoroughly.
Use your full capabilities - exec, web search, memory, everything.

## 📰 Local News Check (1-2x daily)
Scan Dubai/UAE news for context. Use `web_fetch` on:
- https://gulfnews.com/uae (Gulf News)
- https://www.khaleejtimes.com/uae (Khaleej Times)

Look for:
- Traffic/transport updates (road closures, metro changes)
- Weather alerts
- Major events happening in Dubai
- Government announcements
- Anything relevant to JV or Saniservice

Track in `memory/heartbeat-state.json` under `lastChecks.news`.

## 🚗 Traffic Alert (Weekdays 4:30-5:00 PM)
If it's a weekday between 4:30-5:00 PM Dubai time:
1. Check if JV or team members are at/near the Saniservice office (Al Quoz)
2. If yes, proactively remind them:
   - "Hey, it's almost 5 PM — traffic on SZR is about to get heavy. If you're heading home, might want to leave now or wait until 7:30 PM."
3. Peak traffic window: 5-7 PM (can add 15-20 min to commute)
4. Track in `memory/heartbeat-state.json` under `lastChecks.trafficAlert` (only alert once per day)

**Office → JLT times:**
- Before 5 PM: ~18 min
- 5-7 PM: 30-40 min (worst)
- After 7:30 PM: ~20 min

## 💾 Git + Google Drive Backup (HABIT - 6x daily)
Every ~4 heartbeats (roughly every 2 hours), check and run backups:

1. **Git commit & push** (if there are changes):
```bash
cd ~/clawd && git add -A && git status --short
# If changes exist, commit with descriptive message and push
```

2. **Google Drive backup** (runs via cron, but verify):
```bash
~/clawd/scripts/backup-to-drive.sh
```

Track in `memory/heartbeat-state.json` under `lastChecks.backup`.

**Cron schedule:** 6 AM, 10 AM, 2 PM, 6 PM, 10 PM, 2 AM
**Install cron:** `crontab ~/clawd/scripts/crontab.txt`

## 🧠 Vector Memory Sync (PERIODIC)
Every ~6 heartbeats (roughly every 3 hours), run:
```bash
~/clawd/scripts/vector-reindex.sh
```
Track last sync in `memory/heartbeat-state.json` under `lastChecks.vectorSync`.
