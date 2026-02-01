/**
 * Viktor Voice Server v8 - Hybrid (Kyutai STT + ElevenLabs TTS)
 * 
 * 1. Call comes in → greet
 * 2. Stream raw audio via WebSocket → Kyutai STT with semantic VAD
 * 3. VAD signals done → add to queue → wake agent
 * 4. Agent processes → writes response
 * 5. ElevenLabs TTS → play to caller
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Config
const CONFIG_PATH = path.join(process.env.HOME, '.vonage', 'config.json');
const QUEUE_PATH = path.join(process.env.HOME, '.vonage', 'phone-queue.json');
const KYUTAI_VENV = path.join(process.env.HOME, 'clawd', 'kyutai-test', 'venv');

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
const wss = new WebSocket.Server({ server, path: '/socket' });

// Known callers
const knownCallers = {
  '971543062826': 'JV',
  '+971543062826': 'JV',
  '971508885210': 'Franz',
  '+971508885210': 'Franz',
};

// Active calls - track audio buffers and STT processes
const activeCalls = new Map();

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

// ElevenLabs TTS (unchanged)
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

// Kyutai STT with semantic VAD
async function transcribeWithKyutai(audioBuffer) {
  return new Promise((resolve, reject) => {
    const tempFile = path.join(__dirname, 'audio', `temp-${Date.now()}.wav`);
    
    // Write audio buffer to temp WAV file (Vonage sends 16-bit PCM at 16kHz)
    const wavHeader = createWavHeader(audioBuffer.length, 16000, 1, 16);
    fs.writeFileSync(tempFile, Buffer.concat([wavHeader, audioBuffer]));
    
    // Run Kyutai STT
    const python = path.join(KYUTAI_VENV, 'bin', 'python');
    const proc = spawn(python, [
      '-m', 'moshi_mlx.run_inference',
      '--hf-repo', 'kyutai/stt-1b-en_fr-mlx',
      tempFile,
      '--temp', '0'
    ], {
      env: { ...process.env, PATH: `${KYUTAI_VENV}/bin:${process.env.PATH}` }
    });
    
    let output = '';
    let error = '';
    
    proc.stdout.on('data', (data) => { output += data.toString(); });
    proc.stderr.on('data', (data) => { error += data.toString(); });
    
    proc.on('close', (code) => {
      // Cleanup temp file
      try { fs.unlinkSync(tempFile); } catch {}
      
      if (code === 0) {
        // Extract transcription (last non-empty line that's not Info)
        const lines = output.split('\n').filter(l => l.trim() && !l.includes('[Info]') && !l.includes('steps:'));
        const transcription = lines[lines.length - 1]?.trim() || '';
        console.log(`[Kyutai] Transcribed: "${transcription}"`);
        resolve(transcription);
      } else {
        console.error('[Kyutai] Error:', error);
        reject(new Error(error));
      }
    });
  });
}

// Create WAV header
function createWavHeader(dataLength, sampleRate, channels, bitsPerSample) {
  const header = Buffer.alloc(44);
  const byteRate = sampleRate * channels * bitsPerSample / 8;
  const blockAlign = channels * bitsPerSample / 8;
  
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + dataLength, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitsPerSample, 34);
  header.write('data', 36);
  header.writeUInt32LE(dataLength, 40);
  
  return header;
}

// Pre-cache common responses
let greetingUrl, timeoutUrl, thinkingUrl;
(async () => {
  greetingUrl = await speak("Hey, it's Viktor. What do you need?", 'greeting');
  timeoutUrl = await speak("Still there?", 'timeout');
  thinkingUrl = await speak("One moment.", 'thinking');
  console.log('Audio cached');
})();

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'viktor-v8-hybrid' }));

// Answer call - connect to WebSocket for audio streaming
app.get('/answer', async (req, res) => {
  const caller = req.query.from;
  const uuid = req.query.uuid;
  console.log(`\n=== Call from ${caller} (${uuid}) ===`);
  
  const name = knownCallers[caller];
  const audioUrl = name 
    ? await speak(`Hey ${name}, what's up?`, `greet-${Date.now()}`)
    : greetingUrl;
  
  // Initialize call state
  activeCalls.set(uuid, {
    caller,
    name: name || caller,
    audioBuffer: Buffer.alloc(0),
    silenceStart: null,
    lastAudioTime: Date.now(),
    msgId: null
  });
  
  res.json([
    { action: 'stream', streamUrl: [audioUrl] },
    { 
      action: 'connect',
      endpoint: [{
        type: 'websocket',
        uri: `wss://${NGROK_URL.replace('https://', '')}/socket`,
        'content-type': 'audio/l16;rate=16000',
        headers: { 'X-Call-UUID': uuid }
      }]
    }
  ]);
});

// WebSocket handling for audio streaming
wss.on('connection', (ws, req) => {
  const uuid = req.headers['x-call-uuid'];
  console.log(`[WS] Connected: ${uuid}`);
  
  const call = activeCalls.get(uuid);
  if (!call) {
    console.log(`[WS] Unknown call: ${uuid}`);
    ws.close();
    return;
  }
  
  let silenceThreshold = 1500; // ms of silence to consider "done" (semantic VAD will improve this)
  let minAudioLength = 500; // minimum audio to process (ms)
  
  ws.on('message', async (data) => {
    if (Buffer.isBuffer(data)) {
      // Accumulate audio
      call.audioBuffer = Buffer.concat([call.audioBuffer, data]);
      call.lastAudioTime = Date.now();
      
      // Simple energy-based silence detection as backup
      // (Kyutai's semantic VAD will be the real decision maker)
      const energy = calculateEnergy(data);
      
      if (energy < 100) {
        if (!call.silenceStart) call.silenceStart = Date.now();
      } else {
        call.silenceStart = null;
      }
      
      // Check if we have enough silence after speech
      const audioLengthMs = (call.audioBuffer.length / 2) / 16; // 16kHz, 16-bit
      const silenceDuration = call.silenceStart ? Date.now() - call.silenceStart : 0;
      
      if (silenceDuration > silenceThreshold && audioLengthMs > minAudioLength) {
        console.log(`[WS] Processing ${audioLengthMs.toFixed(0)}ms of audio after ${silenceDuration}ms silence`);
        
        // Process the audio
        const audioToProcess = call.audioBuffer;
        call.audioBuffer = Buffer.alloc(0);
        call.silenceStart = null;
        
        try {
          const transcription = await transcribeWithKyutai(audioToProcess);
          
          if (transcription && transcription.length > 2) {
            // Add to queue
            const msgId = crypto.randomUUID();
            call.msgId = msgId;
            addToIncoming(msgId, call.caller, transcription);
            
            // Send "thinking" audio while we wait
            ws.send(JSON.stringify({
              event: 'playAudio',
              audioUrl: thinkingUrl
            }));
            
            // Wait for response
            const response = await getResponse(msgId, 30000);
            
            if (response) {
              console.log(`[Viktor] ${response}`);
              const audioUrl = await speak(response, `resp-${Date.now()}`);
              ws.send(JSON.stringify({
                event: 'playAudio',
                audioUrl: audioUrl
              }));
            } else {
              const fallback = await speak("Sorry, I'm taking too long. Can you ask again?", `fallback-${Date.now()}`);
              ws.send(JSON.stringify({
                event: 'playAudio',
                audioUrl: fallback
              }));
            }
          }
        } catch (e) {
          console.error('[WS] Transcription error:', e.message);
        }
      }
    }
  });
  
  ws.on('close', () => {
    console.log(`[WS] Disconnected: ${uuid}`);
    activeCalls.delete(uuid);
  });
});

// Calculate audio energy (RMS)
function calculateEnergy(buffer) {
  let sum = 0;
  for (let i = 0; i < buffer.length; i += 2) {
    const sample = buffer.readInt16LE(i);
    sum += sample * sample;
  }
  return Math.sqrt(sum / (buffer.length / 2));
}

// Fallback speech endpoint (if WebSocket fails)
app.post('/speech', async (req, res) => {
  const speech = req.body.speech;
  const caller = req.body.from || 'unknown';
  
  if (speech?.results?.[0]?.text) {
    const text = speech.results[0].text;
    const name = knownCallers[caller] || caller;
    console.log(`[Fallback STT] ${name}: ${text}`);
    
    const msgId = crypto.randomUUID();
    addToIncoming(msgId, caller, text);
    
    res.json([
      { action: 'stream', streamUrl: [thinkingUrl] },
      { action: 'notify', payload: { msgId }, eventUrl: [`${NGROK_URL}/check-response`] }
    ]);
  } else {
    res.json([
      { action: 'stream', streamUrl: [timeoutUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 2, language: 'en-US' }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  }
});

app.post('/check-response', async (req, res) => {
  const msgId = req.body.payload?.msgId;
  
  if (!msgId) {
    res.json([{ action: 'talk', text: 'Sorry, something went wrong.', voiceName: 'Brian' }]);
    return;
  }
  
  const response = await getResponse(msgId, 30000);
  
  if (response) {
    const audioUrl = await speak(response, `resp-${Date.now()}`);
    res.json([
      { action: 'stream', streamUrl: [audioUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US' }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  } else {
    res.json([
      { action: 'talk', text: "Sorry, I'm taking too long. Try again.", voiceName: 'Brian' },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US' }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  }
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
    if (['greeting.mp3', 'timeout.mp3', 'thinking.mp3'].includes(f)) return;
    const p = path.join(dir, f);
    if (now - fs.statSync(p).mtimeMs > 600000) fs.unlinkSync(p);
  });
}, 300000);

server.listen(PORT, () => {
  console.log(`\n🎙️ Viktor v8 (Hybrid: Kyutai STT + ElevenLabs TTS)`);
  console.log(`📞 ${config.phoneNumber}`);
  console.log(`🌐 ${NGROK_URL}`);
  console.log(`🔊 WebSocket: wss://${NGROK_URL.replace('https://', '')}/socket\n`);
});
