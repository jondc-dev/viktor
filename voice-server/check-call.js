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

// Check the last call
fetch('https://api.nexmo.com/v1/calls/286b5cab-14cc-4ba5-bbfa-cf2f2a4355ef', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => console.log(JSON.stringify(data, null, 2)))
.catch(err => console.error('Error:', err.message));
