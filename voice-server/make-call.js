const jwt = require('jsonwebtoken');
const { readFileSync } = require('fs');
const path = require('path');

const privateKey = readFileSync(path.join(process.env.HOME, '.vonage', 'private.key'), 'utf8');
const applicationId = 'dc9e7010-d853-411c-b0f2-bd561faa258a';

const now = Math.floor(Date.now() / 1000);
const token = jwt.sign({
  application_id: applicationId,
  iat: now,
  exp: now + 3600,
  jti: Math.random().toString(36).substring(2)
}, privateKey, { algorithm: 'RS256' });

console.log('Calling +971561885789...');

const NGROK_URL = 'https://musaceous-apryl-subrhombic.ngrok-free.dev';

fetch('https://api.nexmo.com/v1/calls', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    to: [{ type: 'phone', number: '971561885789' }],
    from: { type: 'phone', number: '97142289386' },
    ncco: [
      { action: 'stream', streamUrl: [`${NGROK_URL}/audio/outbound-brave.mp3`] }
    ]
  })
})
.then(r => r.json())
.then(data => console.log('Result:', JSON.stringify(data, null, 2)))
.catch(err => console.error('Error:', err.message));
