/**
 * Viktor Voice Server v9 - Direct Haiku
 * 
 * Flow: Audio → Kyutai STT → Haiku Direct → ElevenLabs TTS → Vonage Stream API
 * No queue, no round-trip. Maximum speed.
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const jwt = require('jsonwebtoken');

// Config
const CONFIG_PATH = path.join(process.env.HOME, '.vonage', 'config.json');
const AUTH_PATH = path.join(process.env.HOME, '.clawdbot', 'agents', 'main', 'agent', 'auth-profiles.json');
const VONAGE_KEY_PATH = path.join(process.env.HOME, '.vonage', 'private.key');
const KYUTAI_VENV = path.join(process.env.HOME, 'clawd', 'kyutai-test', 'venv');
const MEMORY_DIR = path.join(process.env.HOME, 'clawd', 'memory');

const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const auth = JSON.parse(fs.readFileSync(AUTH_PATH, 'utf8'));
const vonagePrivateKey = fs.readFileSync(VONAGE_KEY_PATH, 'utf8');

function getKeychainPassword(service, account) {
  try {
    return execSync(`security find-generic-password -s "${service}" -a "${account}" -w`, { encoding: 'utf8' }).trim();
  } catch (e) { return null; }
}

const ANTHROPIC_API_KEY = auth.anthropic?.apiKey;
const ELEVENLABS_API_KEY = getKeychainPassword('elevenlabs-api-key', 'elevenlabs');
const ELEVENLABS_VOICE_ID = getKeychainPassword('elevenlabs-voice-id', 'elevenlabs');
const VONAGE_APP_ID = getKeychainPassword('vonage-app-id', 'vonage') || getKeychainPassword('vonage', 'vonage');

const PORT = 3000;
const NGROK_URL = config.ngrokUrl;

const app = express();
app.use(express.json());
app.use('/audio', express.static(path.join(__dirname, 'audio')));
fs.mkdirSync(path.join(__dirname, 'audio'), { recursive: true });

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Known callers
const knownCallers = {
  '971543062826': 'JV',
  '+971543062826': 'JV',
  '971508885210': 'Franz',
  '+971508885210': 'Franz',
};

// Active calls
const activeCalls = new Map();

// Generate Vonage JWT
function generateVonageJWT() {
  const now = Math.floor(Date.now() / 1000);
  return jwt.sign({
    application_id: VONAGE_APP_ID,
    iat: now,
    exp: now + 3600,
    jti: Math.random().toString(36).substring(2)
  }, vonagePrivateKey, { algorithm: 'RS256' });
}

// Play audio into call via Vonage REST API
async function playAudioIntoCall(uuid, audioUrl) {
  const token = generateVonageJWT();
  
  try {
    const res = await fetch(`https://api.nexmo.com/v1/calls/${uuid}/stream`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        stream_url: [audioUrl],
        loop: 1
      })
    });
    
    if (!res.ok) {
      const err = await res.text();
      console.error(`[Vonage] Stream failed: ${res.status} - ${err}`);
      return false;
    }
    
    console.log(`[Vonage] Playing audio into ${uuid}`);
    return true;
  } catch (e) {
    console.error('[Vonage] Stream error:', e.message);
    return false;
  }
}

// Phone-optimized system prompt
const PHONE_SYSTEM_PROMPT = `You are Viktor, Frontdesk Services Specialist at Saniservice. You're answering a phone call.

CRITICAL RULES:
- Keep responses SHORT (1-2 sentences max) — this is spoken aloud
- Be natural and conversational, not robotic
- Use casual language appropriate for a phone call
- If you need to look something up, say "let me check" first
- Never use markdown, bullet points, or formatting
- Never say "I don't have access to" — just try to help

Current time: ${new Date().toLocaleString('en-US', { timeZone: 'Asia/Dubai' })}`;

// Tool definitions for Haiku
const TOOLS = [
  {
    name: 'get_time',
    description: 'Get current date and time in Dubai',
    input_schema: { type: 'object', properties: {}, required: [] }
  },
  {
    name: 'get_weather',
    description: 'Get current weather for a location',
    input_schema: {
      type: 'object',
      properties: { location: { type: 'string', description: 'City name (default: Dubai)' } },
      required: []
    }
  }
];

// Tool implementations
async function executeTool(name, input) {
  console.log(`[Tool] ${name}:`, input);
  
  switch (name) {
    case 'get_time':
      return new Date().toLocaleString('en-US', { 
        timeZone: 'Asia/Dubai',
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
      
    case 'get_weather':
      try {
        const loc = input.location || 'Dubai';
        const result = execSync(`curl -s "wttr.in/${loc}?format=%C+%t+%h"`, { timeout: 5000, encoding: 'utf8' });
        return result.trim();
      } catch (e) {
        return 'Weather service unavailable';
      }
      
    default:
      return 'Unknown tool';
  }
}

// Call Haiku directly
async function callHaiku(callerName, userMessage, conversationHistory = []) {
  const messages = [
    ...conversationHistory,
    { role: 'user', content: `[${callerName} on phone]: ${userMessage}` }
  ];
  
  console.log(`[Haiku] Calling with: "${userMessage}"`);
  const start = Date.now();
  
  try {
    let response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-3-5-haiku-20241022',
        max_tokens: 150,
        system: PHONE_SYSTEM_PROMPT,
        tools: TOOLS,
        messages
      })
    });
    
    let data = await response.json();
    
    // Handle tool use (one iteration max for speed)
    if (data.stop_reason === 'tool_use') {
      const toolUse = data.content.find(c => c.type === 'tool_use');
      if (toolUse) {
        const toolResult = await executeTool(toolUse.name, toolUse.input);
        
        messages.push({ role: 'assistant', content: data.content });
        messages.push({ 
          role: 'user', 
          content: [{ type: 'tool_result', tool_use_id: toolUse.id, content: toolResult }]
        });
        
        response = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01'
          },
          body: JSON.stringify({
            model: 'claude-3-5-haiku-20241022',
            max_tokens: 150,
            system: PHONE_SYSTEM_PROMPT,
            tools: TOOLS,
            messages
          })
        });
        
        data = await response.json();
      }
    }
    
    const textContent = data.content?.find(c => c.type === 'text');
    const text = textContent?.text || "Sorry, I couldn't process that.";
    
    console.log(`[Haiku] Response in ${Date.now() - start}ms: "${text}"`);
    
    return {
      text,
      history: [...messages, { role: 'assistant', content: data.content }]
    };
    
  } catch (e) {
    console.error('[Haiku] Error:', e.message);
    return { text: "Sorry, can you say that again?", history: messages };
  }
}

// Strip ANSI codes
function stripAnsi(str) {
  return str.replace(/\x1b\[[0-9;]*m/g, '');
}

// Kyutai STT
async function transcribeWithKyutai(audioBuffer) {
  return new Promise((resolve, reject) => {
    const tempFile = path.join(__dirname, 'audio', `temp-${Date.now()}.wav`);
    
    const wavHeader = createWavHeader(audioBuffer.length, 16000, 1, 16);
    fs.writeFileSync(tempFile, Buffer.concat([wavHeader, audioBuffer]));
    
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
      try { fs.unlinkSync(tempFile); } catch {}
      
      if (code === 0) {
        // Strip ANSI codes and filter out debug/config lines
        const cleanOutput = stripAnsi(output);
        const lines = cleanOutput.split('\n')
          .map(l => l.trim())
          .filter(l => {
            if (!l) return false;
            if (l.startsWith('{')) return false;  // JSON config
            if (l.includes('Info:')) return false;  // Progress info
            if (l.includes('token per sec')) return false;  // Stats
            if (l.includes('loading')) return false;  // Loading messages
            if (l.includes('warming up')) return false;  // Warmup
            return true;
          });
        
        const transcription = lines.join(' ').trim();
        console.log(`[Kyutai] "${transcription}"`);
        resolve(transcription);
      } else {
        console.error('[Kyutai] Error:', error);
        reject(new Error(error));
      }
    });
  });
}

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

// ElevenLabs TTS
async function speak(text, fileId) {
  try {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}/stream`, {
      method: 'POST',
      headers: { 'Accept': 'audio/mpeg', 'Content-Type': 'application/json', 'xi-api-key': ELEVENLABS_API_KEY },
      body: JSON.stringify({ 
        text, 
        model_id: 'eleven_flash_v2_5', 
        voice_settings: { stability: 0.3, similarity_boost: 0.75, style: 0.4, use_speaker_boost: true } 
      })
    });
    if (!res.ok) {
      console.error('[TTS] Failed:', res.status);
      return null;
    }
    const audioPath = path.join(__dirname, 'audio', `${fileId}.mp3`);
    fs.writeFileSync(audioPath, Buffer.from(await res.arrayBuffer()));
    return `${NGROK_URL}/audio/${fileId}.mp3`;
  } catch (e) {
    console.error('[TTS]', e.message);
    return null;
  }
}

// Log call to memory
function logToMemory(caller, transcript, response) {
  const today = new Date().toISOString().split('T')[0];
  const memFile = path.join(MEMORY_DIR, `${today}.md`);
  const time = new Date().toLocaleTimeString('en-US', { timeZone: 'Asia/Dubai', hour: '2-digit', minute: '2-digit' });
  
  let content = '';
  if (fs.existsSync(memFile)) {
    content = fs.readFileSync(memFile, 'utf8');
  }
  
  if (!content.includes('## Phone Calls')) {
    content += '\n\n## Phone Calls\n';
  }
  
  content += `\n### ${time} - ${caller}\n`;
  content += `**Caller:** ${transcript}\n`;
  content += `**Viktor:** ${response}\n`;
  
  fs.writeFileSync(memFile, content);
}

// Pre-cache audio
let greetingUrl;
(async () => {
  greetingUrl = await speak("Hey, it's Viktor. What do you need?", 'greeting');
  console.log('Audio cached');
})();

function calculateEnergy(buffer) {
  if (buffer.length < 2) return 0;
  let sum = 0;
  const len = buffer.length - (buffer.length % 2);
  for (let i = 0; i < len; i += 2) {
    const sample = buffer.readInt16LE(i);
    sum += sample * sample;
  }
  return Math.sqrt(sum / (len / 2));
}

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'viktor-v9-direct' }));

app.get('/answer', async (req, res) => {
  const caller = req.query.from;
  const uuid = req.query.uuid;
  console.log(`\n=== Call from ${caller} (${uuid}) ===`);
  
  const name = knownCallers[caller];
  const audioUrl = name 
    ? await speak(`Hey ${name}, what's up?`, `greet-${Date.now()}`)
    : greetingUrl;
  
  activeCalls.set(uuid, {
    caller,
    name: name || caller,
    audioBuffer: Buffer.alloc(0),
    silenceStart: null,
    conversationHistory: [],
    processing: false
  });
  
  res.json([
    { action: 'stream', streamUrl: [audioUrl] },
    { 
      action: 'connect',
      endpoint: [{
        type: 'websocket',
        uri: `wss://${NGROK_URL.replace('https://', '')}/socket/${uuid}`,
        'content-type': 'audio/l16;rate=16000'
      }]
    }
  ]);
});

wss.on('connection', (ws, req) => {
  const urlPath = req.url || '';
  const uuid = urlPath.split('/socket/')[1]?.split('?')[0];
  console.log(`[WS] Connected: ${uuid}`);
  
  const call = activeCalls.get(uuid);
  if (!call) {
    console.log(`[WS] No call found for ${uuid}`);
    ws.close();
    return;
  }
  
  call.uuid = uuid;
  const silenceThreshold = 1500;  // Wait longer for speech to finish
  const minAudioLength = 1500;    // Need at least 1.5s of audio
  
  ws.on('message', async (data) => {
    if (!Buffer.isBuffer(data)) return;
    if (call.processing) return; // Don't accumulate while processing
    
    call.audioBuffer = Buffer.concat([call.audioBuffer, data]);
    
    const energy = calculateEnergy(data);
    
    if (energy < 100) {
      if (!call.silenceStart) call.silenceStart = Date.now();
    } else {
      call.silenceStart = null;
    }
    
    const audioLengthMs = (call.audioBuffer.length / 2) / 16;
    const silenceDuration = call.silenceStart ? Date.now() - call.silenceStart : 0;
    
    if (silenceDuration > silenceThreshold && audioLengthMs > minAudioLength && !call.processing) {
      call.processing = true;
      console.log(`[WS] Processing ${audioLengthMs.toFixed(0)}ms audio`);
      
      const audioToProcess = call.audioBuffer;
      call.audioBuffer = Buffer.alloc(0);
      call.silenceStart = null;
      
      try {
        const transcription = await transcribeWithKyutai(audioToProcess);
        
        if (transcription && transcription.length > 3) {
          console.log(`[Speech] Got: "${transcription}"`);
          
          // Direct to Haiku
          const { text, history } = await callHaiku(call.name, transcription, call.conversationHistory);
          call.conversationHistory = history;
          
          // Log to memory
          logToMemory(call.name, transcription, text);
          
          // TTS and play via Vonage API
          const audioUrl = await speak(text, `resp-${Date.now()}`);
          if (audioUrl && uuid) {
            await playAudioIntoCall(uuid, audioUrl);
          }
        }
      } catch (e) {
        console.error('[WS] Error:', e.message);
      }
      
      call.processing = false;
    }
  });
  
  ws.on('close', () => {
    console.log(`[WS] Disconnected: ${uuid}`);
    activeCalls.delete(uuid);
  });
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
    if (f === 'greeting.mp3') return;
    const p = path.join(dir, f);
    try {
      if (now - fs.statSync(p).mtimeMs > 600000) fs.unlinkSync(p);
    } catch {}
  });
}, 300000);

server.listen(PORT, () => {
  console.log(`\n🚀 Viktor v9 (Direct: Kyutai STT → Haiku → ElevenLabs TTS)`);
  console.log(`📞 ${config.phoneNumber}`);
  console.log(`🌐 ${NGROK_URL}`);
  console.log(`⚡ No queue — direct Haiku calls\n`);
});
