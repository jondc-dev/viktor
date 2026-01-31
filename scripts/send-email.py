#!/usr/bin/env python3
"""
Send HTML emails with signature for Viktor @ Saniservice
Usage: send-email.py <to> <subject> <body>
"""

import sys
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SIGNATURE_FILE = Path.home() / "clawd" / "email-signature.html"

def get_password():
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "viktor@saniservice.com", "-s", "saniservice-email", "-w"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def send_email(to: str, subject: str, body: str):
    password = get_password()
    
    # Load signature
    signature_html = ""
    if SIGNATURE_FILE.exists():
        # Extract just the table part from the signature (skip the full HTML wrapper)
        full_sig = SIGNATURE_FILE.read_text()
        # Find the signature table
        start = full_sig.find('<table class=MsoNormalTable')
        end = full_sig.find('</table>', start) + 8 if start != -1 else -1
        if start != -1 and end != -1:
            signature_html = full_sig[start:end]
    
    # Create multipart message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = 'Viktor <viktor@saniservice.com>'
    msg['To'] = to
    
    # Plain text version
    plain_text = f"""{body}

Best regards,
Viktor
Front Desk Support Specialist
Saniservice
(+971) 04 2289386
viktor@saniservice.com
www.saniservice.com"""
    
    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #000;">
<p>{body.replace(chr(10), '<br>')}</p>
<p>Best regards,</p>
<br>
<table border="0" cellspacing="0" cellpadding="0" width="608" style="width:456pt;border-collapse:collapse;">
 <tr style="height:1pt">
  <td width="227" style="width:170px;border:none;border-right:solid #ff0000 1pt;padding:0 10px 0 0;height:1pt;vertical-align:top;">
   <a href="http://www.saniservice.com/"><img border="0" width="170" height="90" src="http://saniservice.com/signatures/images/Saniservice%20Logo.png" alt="Saniservice"></a>
  </td>
  <td width="381" style="padding:0 0 0 10px;height:1pt;vertical-align:top;">
   <p style="margin:0 0 2px 0;"><b style="font-family:Garamond,serif;letter-spacing:1.6pt;">Viktor</b></p>
   <p style="margin:0 0 8px 0;font-size:8pt;font-family:Garamond,serif;">Front Desk Support Specialist</p>
   <table border="0" cellspacing="0" cellpadding="0" style="background:white;">
    <tr>
     <td style="padding:2px 5px 2px 0;vertical-align:middle;"><img border="0" width="10" height="11" src="http://saniservice.com/signatures/images/Map.png"></td>
     <td style="font-size:8pt;font-family:Garamond,serif;color:#000;">Suite 115, Al Joud Center, Al Quoz Ind. 1, SZR, Dubai.</td>
    </tr>
    <tr>
     <td style="padding:2px 5px 2px 0;vertical-align:middle;"><img border="0" width="10" height="11" src="http://saniservice.com/signatures/images/phone.png"></td>
     <td style="font-size:8pt;font-family:Garamond,serif;color:#000;">(+971) 04 2289386</td>
    </tr>
    <tr>
     <td style="padding:2px 5px 2px 0;vertical-align:middle;"><img border="0" width="10" height="11" src="http://saniservice.com/signatures/images/mail.png"></td>
     <td style="font-size:8pt;font-family:Garamond,serif;color:#000;">viktor@saniservice.com</td>
    </tr>
    <tr>
     <td style="padding:2px 5px 2px 0;vertical-align:middle;"><img border="0" width="11" height="11" src="http://saniservice.com/signatures/images/Web.png"></td>
     <td style="font-size:8pt;font-family:Garamond,serif;"><a href="http://www.saniservice.com" style="color:#000;text-decoration:none;">www.saniservice.com</a></td>
    </tr>
   </table>
  </td>
 </tr>
</table>
</body>
</html>"""
    
    # Attach both versions (plain first, HTML second - email clients prefer the last one they can render)
    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Send
    with smtplib.SMTP('mail.saniservice.com', 587) as server:
        server.starttls()
        server.login('viktor@saniservice.com', password)
        server.send_message(msg)
    
    print(f"✅ Email sent to {to}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: send-email.py <to> <subject> <body>")
        sys.exit(1)
    
    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    
    send_email(to, subject, body)
