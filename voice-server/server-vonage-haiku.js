/**
 * Viktor Voice Server v10 - Vonage ASR → DeepSeek Direct → ElevenLabs TTS
 * 
 * Best of both worlds:
 * - Vonage ASR for reliable real-time transcription
 * - Direct DeepSeek calls for fast responses (no queue)
 * - ElevenLabs for quality TTS
 */

const express = require('express');
const http = require('http');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Config
const CONFIG_PATH = path.join(process.env.HOME, '.vonage', 'config.json');
const AUTH_PATH = path.join(process.env.HOME, '.clawdbot', 'agents', 'main', 'agent', 'auth-profiles.json');
const MEMORY_DIR = path.join(process.env.HOME, 'clawd', 'memory');
const WORKSPACE_DIR = path.join(process.env.HOME, 'clawd');

const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const auth = JSON.parse(fs.readFileSync(AUTH_PATH, 'utf8'));

// Load memory context for DeepSeek
function loadMemoryContext() {
  let context = '';
  
  // Read MEMORY.md
  try {
    const memoryPath = path.join(WORKSPACE_DIR, 'MEMORY.md');
    if (fs.existsSync(memoryPath)) {
      const content = fs.readFileSync(memoryPath, 'utf8');
      // Take last 2000 chars to keep it manageable
      context += '## Long-term Memory:\n' + content.slice(-2000) + '\n\n';
    }
  } catch (e) {}
  
  // Read today's notes
  const today = new Date().toISOString().split('T')[0];
  try {
    const todayPath = path.join(MEMORY_DIR, `${today}.md`);
    if (fs.existsSync(todayPath)) {
      const content = fs.readFileSync(todayPath, 'utf8');
      context += '## Today\'s Notes:\n' + content.slice(-1500) + '\n\n';
    }
  } catch (e) {}
  
  // Read yesterday's notes
  const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
  try {
    const yesterdayPath = path.join(MEMORY_DIR, `${yesterday}.md`);
    if (fs.existsSync(yesterdayPath)) {
      const content = fs.readFileSync(yesterdayPath, 'utf8');
      context += '## Yesterday\'s Notes:\n' + content.slice(-1000) + '\n';
    }
  } catch (e) {}
  
  return context;
}

function getKeychainPassword(service, account) {
  try {
    return execSync(`security find-generic-password -s "${service}" -a "${account}" -w`, { encoding: 'utf8' }).trim();
  } catch (e) { return null; }
}

const DEEPSEEK_API_KEY = auth.deepseek?.apiKey || process.env.DEEPSEEK_API_KEY || getKeychainPassword('deepseek-api-key', 'deepseek');
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
};

// Active conversations (for context)
const conversations = new Map();

// Phone-optimized system prompt (built dynamically with memory)
function buildSystemPrompt() {
  const memoryContext = loadMemoryContext();
  
  return `You are Viktor, Frontdesk Services Specialist at Saniservice. You're answering a phone call.

CRITICAL RULES:
- Keep responses SHORT (1-2 sentences max) — this is spoken aloud
- Be natural and conversational, not robotic
- Use casual language appropriate for a phone call
- Never use markdown, bullet points, or formatting
- If asked about time, date, or weather, give a direct answer
- You have access to your memory/notes below — use them to stay consistent with your chat persona

Current time: ${new Date().toLocaleString('en-US', { timeZone: 'Asia/Dubai' })}

---
${memoryContext}`;
}

// Tool definitions
const TOOLS = [
  {
    type: 'function',
    function: {
      name: 'get_time',
      description: 'Get current date and time in Dubai',
      parameters: { type: 'object', properties: {}, required: [] }
    }
  },
  {
    type: 'function',
    function: {
      name: 'get_weather',
      description: 'Get current weather for a location',
      parameters: {
        type: 'object',
        properties: { location: { type: 'string', description: 'City name (default: Dubai)' } },
        required: []
      }
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

// Call DeepSeek directly
async function callDeepSeek(callerName, userMessage, conversationHistory = []) {
  const messages = [
    { role: 'system', content: buildSystemPrompt() },
    ...conversationHistory,
    { role: 'user', content: `[${callerName} on phone]: ${userMessage}` }
  ];
  
  console.log(`[DeepSeek] "${userMessage}"`);
  const start = Date.now();
  
  try {
    let response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        max_tokens: 150,
        tools: TOOLS,
        messages
      })
    });
    
    let data = await response.json();
    
    // Handle tool use (one iteration)
    if (data.choices?.[0]?.message?.tool_calls) {
      const toolCall = data.choices[0].message.tool_calls[0];
      if (toolCall) {
        const toolInput = JSON.parse(toolCall.function.arguments || '{}');
        const toolResult = await executeTool(toolCall.function.name, toolInput);
        
        messages.push(data.choices[0].message);
        messages.push({ 
          role: 'tool',
          tool_call_id: toolCall.id,
          content: toolResult
        });
        
        response = await fetch('https://api.deepseek.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${DEEPSEEK_API_KEY}`
          },
          body: JSON.stringify({
            model: 'deepseek-chat',
            max_tokens: 150,
            tools: TOOLS,
            messages
          })
        });
        
        data = await response.json();
      }
    }
    
    const text = data.choices?.[0]?.message?.content || "Sorry, can you say that again?";
    
    console.log(`[DeepSeek] ${Date.now() - start}ms: "${text}"`);
    
    const assistantMessage = data.choices?.[0]?.message;
    return {
      text,
      history: [...messages.slice(1), ...(assistantMessage ? [assistantMessage] : [])]
    };
    
  } catch (e) {
    console.error('[DeepSeek] Error:', e.message);
    return { text: "Sorry, can you say that again?", history: conversationHistory };
  }
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
    if (!res.ok) return null;
    const audioPath = path.join(__dirname, 'audio', `${fileId}.mp3`);
    fs.writeFileSync(audioPath, Buffer.from(await res.arrayBuffer()));
    return `${NGROK_URL}/audio/${fileId}.mp3`;
  } catch (e) {
    console.error('[TTS]', e.message);
    return null;
  }
}

// Log to memory
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
  
  content += `\n**${time} - ${caller}:** ${transcript}\n`;
  content += `**Viktor:** ${response}\n`;
  
  fs.writeFileSync(memFile, content);
}

// Pre-cache audio
let greetingUrl, timeoutUrl;
(async () => {
  greetingUrl = await speak("Hey, it's Viktor. What do you need?", 'greeting');
  timeoutUrl = await speak("Still there?", 'timeout');
  console.log('Audio cached');
})();

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'viktor-v10-deepseek' }));

app.get('/answer', async (req, res) => {
  const caller = req.query.from;
  const uuid = req.query.uuid;
  console.log(`\n=== Call from ${caller} (${uuid}) ===`);
  
  const name = knownCallers[caller];
  const audioUrl = name 
    ? await speak(`Hey ${name}, what's up?`, `greet-${Date.now()}`)
    : greetingUrl;
  
  // Initialize conversation
  conversations.set(uuid, {
    caller,
    name: name || caller,
    history: []
  });
  
  res.json([
    { action: 'stream', streamUrl: [audioUrl] },
    { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US', maxDuration: 30 }, eventUrl: [`${NGROK_URL}/speech`] }
  ]);
});

app.post('/speech', async (req, res) => {
  const speech = req.body.speech;
  const caller = req.body.from || 'unknown';
  const uuid = req.body.uuid;
  
  const conv = conversations.get(uuid) || { caller, name: knownCallers[caller] || caller, history: [] };
  
  if (speech?.results?.[0]?.text) {
    const text = speech.results[0].text;
    console.log(`[${conv.name}] ${text}`);
    
    // Direct DeepSeek call - no queue!
    const { text: response, history } = await callDeepSeek(conv.name, text, conv.history);
    conv.history = history;
    conversations.set(uuid, conv);
    
    // Log to memory
    logToMemory(conv.name, text, response);
    
    // Generate TTS and respond
    const audioUrl = await speak(response, `resp-${Date.now()}`);
    
    res.json([
      { action: 'stream', streamUrl: [audioUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 1.5, language: 'en-US', maxDuration: 30 }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
    
  } else if (speech?.timeout_reason) {
    res.json([
      { action: 'stream', streamUrl: [timeoutUrl] },
      { action: 'input', type: ['speech'], speech: { endOnSilence: 2, language: 'en-US' }, eventUrl: [`${NGROK_URL}/speech`] }
    ]);
  } else {
    const bye = await speak("Alright, talk later!", `bye-${Date.now()}`);
    res.json([{ action: 'stream', streamUrl: [bye] }]);
    conversations.delete(uuid);
  }
});

app.post('/event', (req, res) => {
  const status = req.body.status;
  console.log(`[Event] ${status}`);
  
  if (status === 'completed') {
    const uuid = req.body.uuid;
    conversations.delete(uuid);
  }
  
  res.status(200).end();
});

// Cleanup old audio
setInterval(() => {
  const dir = path.join(__dirname, 'audio');
  const now = Date.now();
  fs.readdirSync(dir).forEach(f => {
    if (['greeting.mp3', 'timeout.mp3'].includes(f)) return;
    const p = path.join(dir, f);
    try {
      if (now - fs.statSync(p).mtimeMs > 600000) fs.unlinkSync(p);
    } catch {}
  });
}, 300000);

server.listen(PORT, () => {
  console.log(`\n🚀 Viktor v10 (Vonage ASR → DeepSeek Direct → ElevenLabs TTS)`);
  console.log(`📞 ${config.phoneNumber}`);
  console.log(`🌐 ${NGROK_URL}`);
  console.log(`⚡ No queue — direct DeepSeek calls\n`);
});
