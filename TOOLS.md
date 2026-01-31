# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

---

## Email

- **Address:** viktor@saniservice.com
- **Server:** mail.saniservice.com
- **Client:** himalaya CLI (config at `~/.config/himalaya/config.toml`)
- **Password:** Stored in macOS Keychain (service: `saniservice-email`)

I manage email autonomously — reading, replying, and handling inquiries as the Frontdesk Services Specialist.

**Email Format:** HTML with signature
- Signature file: `/Users/victor/clawd/email-signature.html`
- Always end emails with "Best regards," followed by the HTML signature

---

## What Else Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

---

## Voice Messages
- **When receiving:** If someone sends a voice message, reply with a voice message
- **TTS:** ElevenLabs Flash v2.5, voice ID `c6SfcYrb2t09NHXiT80T`
- **Format:** Always convert to OGG/Opus before sending (WhatsApp requires this)
  - Generate MP3 from ElevenLabs, then: `ffmpeg -i input.mp3 -c:a libopus -b:a 64k output.ogg`
- **Transcription:** Local Whisper (`/opt/homebrew/bin/whisper`)

---

Add whatever helps me do my job. This is my cheat sheet.
