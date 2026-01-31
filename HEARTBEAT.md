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

## 🧠 Vector Memory Sync (PERIODIC)
Every ~6 heartbeats (roughly every 3 hours), run:
```bash
~/clawd/scripts/vector-reindex.sh
```
Track last sync in `memory/heartbeat-state.json` under `lastChecks.vectorSync`.
