/**
 * Viktor Voice Server v7 - Queue + System Event Wake
 * 
 * 1. Call comes in → greet
 * 2. Caller speaks → add to queue → trigger system event
 * 3. Main agent wakes → processes queue → writes response
 * 4. Server polls outgoing → speaks response
 */

const express = require('express');
const http = require('http');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Config
const CONFIG_PATH = path.join(process.env.HOME, '.vonage', 'config.json');
const QUEUE_PATH = path.join(process.env.HOME, '.vonage', 'phone-queue.json');

const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

function getKeychainPassword(service, account) {
  try {
    return execSync(`security find-generic-password -s "${service}" -a "${account}" -w`, { encoding: 'utf8' }).trim();
  } catch (e) { return null; }
}

const ELEVENLABS_API_KEY = getKeychainPassword('elevenlabs-api-key', 'elevenlabs');
const ELEVENLABS_VOICE_ID = getKeychainPassword('elevenlabs-voice-id', 'elevenlabs');

const PORT = 3000;
const NGROK_URL = config.ngrokUrl;

const app = express();
app.use(express.json());
app.use('/audio', express.static(path.join(__dirname, 'audio')));
fs.mkdirSync(path.join(__dirname, 'audio'), { recursive: true });

const server = http.createServer(app);

// Known callers
const knownCallers = {
  '971543062826': 'JV',
  '+971543062826': 'JV',
  '971508885210': 'Franz',
  '+971508885210': 'Franz',
  '97143215505': 'JV'
};

// Queue operations
function readQueue() {
  try { return JSON.parse(fs.readFileSync(QUEUE_PATH, 'utf8')); }
  catch { return { incoming: [], outgoing: [] }; }
}

function writeQueue(queue) {
  fs.writeFileSync(QUEUE_PATH, JSON.stringify(queue, null, 2));
}

function addToIncoming(id, caller, text) {
  const queue = readQueue();
  queue.incoming.push({ id, caller, text, timestamp: new Date().toISOString() });
  writeQueue(queue);
  console.log(`[Queue] Added: ${id}`);
  
  // Trigger system event to wake main agent
  try {
    execSync(`clawdbot system event --text "Phone: process queue" --mode now`, { 
      timeout: 5000,
      stdio: 'ignore'
    });
    console.log(`[Wake] Triggered system event`);
  } catch (e) {
    console.log(`[Wake] Failed:`, e.message);
  }
}

function getResponse(id, timeoutMs = 45000) {
  return new Promise((resolve) => {
    const start = Date.now();
    const poll = setInterval(() => {
      const queue = readQueue();
      const idx = queue.outgoing.findIndex(m => m.id === id);
      
      if (idx !== -1) {
        const response = queue.outgoing[idx].text;
        queue.outgoing.splice(idx, 1);
        writeQueue(queue);
        clearInterval(poll);
        console.log(`[Queue] Got response for ${id}`);
        resolve(response);
      } else if (Date.now() - start > timeoutMs) {
        clearInterval(poll);
        console.log(`[Queue] Timeout for ${id}`);
        resolve(null);
      }
    }, 500);
  });
}

// TTS
async function speak(text, fileId) {
  try {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}/stream`, {
      method: 'POST',
      headers: { 'Accept': 'audio/mpeg', 'Content-Type': 'application/json', 'xi-api-key': ELEVENLABS_API_KEY },
      body: JSON.stringify({ text, model_id: 'eleven_flash_v2_5', voice_settings: { stability: 0.3, similarity_boost: 0.75, style: 0.4, use_speaker_boost: true } })
    });
    if (!res.ok) return null;
    const audioPath = path.join(__dirname, 'audio', `${fileId}.mp3`);
    fs.writeFileSync(audioPath, Buffer.from(await res.arrayBuffer()));
    return `${NGROK_URL}/audio/${fileId}.mp3`;
  } catch (e) {
    console.error('[TTS]', e.message);
    return null;
  }
}

// Pre-cache
let greetingUrl, timeoutUrl, thinkingUrl;
(async () => {
  greetingUrl = await speak("Hey, it's Viktor. What do you need?", 'greeting');
  timeoutUrl = await speak("Still there?", 'timeout');
  thinkingUrl = await speak("One moment.", 'thinking');
  console.log('Audio cached');
})();

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'viktor-v7' }));

app.get('/answer', async (req, res) => {
  const caller = req.query.from;
  console.log(`\n=== Call from ${caller} ===`);
  
  const name = knownCallers[caller];
  const audioUrl = name 
    ? await speak(`Hey ${name}, what's up?`, `greet-${Date.now()}`)
    : greetingUrl;
  
  res.json([
    { action: 'stream', streamUrl: [audioUrl] },
    { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US', maxDuration: 30 }, eventUrl: [`${NGROK_URL}/speech`] }
  ]);
});

// Store pending responses for calls
const pendingResponses = new Map();

app.post('/speech', async (req, res) => {
  const speech = req.body.speech;
  const caller = req.body.from || 'unknown';
  const callId = req.body.uuid;
  
  if (speech?.results?.[0]?.text) {
    const text = speech.results[0].text;
    const name = knownCallers[caller] || caller;
    console.log(`[${name}] ${text}`);
    
    const msgId = crypto.randomUUID();
    addToIncoming(msgId, caller, text);
    
    // Store the pending message ID for this call
    pendingResponses.set(callId, msgId);
    
    // Respond immediately with "thinking" then check for response
    res.json([
      { action: 'stream', streamUrl: [thinkingUrl] },
      { action: 'notify', payload: { msgId }, eventUrl: [`${NGROK_URL}/check-response`] }
    ]);
    return;
    
  } else if (speech?.timeout_reason) {
    res.json([
      { action: 'stream', streamUrl: [timeoutUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 2, language: 'en-US' }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  } else {
    const bye = await speak("Alright, talk later!", `bye-${Date.now()}`);
    res.json([{ action: 'stream', streamUrl: [bye] }]);
  }
});

// Check for response after notify
app.post('/check-response', async (req, res) => {
  const msgId = req.body.payload?.msgId;
  const callId = req.body.uuid;
  
  if (!msgId) {
    console.log('[CheckResponse] No msgId');
    res.json([{ action: 'talk', text: 'Sorry, something went wrong.', voiceName: 'Brian' }]);
    return;
  }
  
  console.log(`[CheckResponse] Waiting for ${msgId}`);
  
  // Poll for response (shorter timeout since we already said "one moment")
  const response = await getResponse(msgId, 30000);
  
  if (response) {
    console.log(`[Viktor] ${response}`);
    const audioUrl = await speak(response, `resp-${Date.now()}`);
    
    res.json([
      { action: 'stream', streamUrl: [audioUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US', maxDuration: 30 }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  } else {
    console.log(`[CheckResponse] Timeout for ${msgId}`);
    res.json([
      { action: 'talk', text: "Sorry, I'm taking too long. Try asking again.", voiceName: 'Brian' },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US', maxDuration: 30 }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  }
  
  pendingResponses.delete(callId);
});

app.post('/event', (req, res) => {
  console.log(`[Event] ${req.body.status}`);
  res.status(200).end();
});

// Cleanup old audio
setInterval(() => {
  const dir = path.join(__dirname, 'audio');
  const now = Date.now();
  fs.readdirSync(dir).forEach(f => {
    if (['greeting.mp3', 'timeout.mp3'].includes(f)) return;
    const p = path.join(dir, f);
    if (now - fs.statSync(p).mtimeMs > 600000) fs.unlinkSync(p);
  });
}, 300000);

server.listen(PORT, () => {
  console.log(`\n🎙️ Viktor v7 (Queue + Wake)`);
  console.log(`📞 ${config.phoneNumber}`);
  console.log(`🌐 ${NGROK_URL}\n`);
});
