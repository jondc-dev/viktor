#!/usr/bin/env python3
"""
Sanihome AC Opportunities Follow-up
Checks progress on Sanihome AC opportunities and generates new ones when complete
"""

import json
import subprocess
import datetime
from pathlib import Path

def get_latest_opportunities_file():
    """Get the most recent opportunities file"""
    
    files = list(Path("/Users/victor/clawd/memory").glob("sanihome-ac-opportunities-*.json"))
    if not files:
        return None
    
    return max(files, key=lambda x: x.stat().st_mtime)

def check_progress():
    """Check the status of current opportunities"""
    
    latest_file = get_latest_opportunities_file()
    if not latest_file:
        print("No Sanihome opportunities file found")
        return None
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def send_follow_up_message(current_data):
    """Send follow-up message to check progress"""
    
    opportunities = current_data.get('opportunities', [])
    week_start = current_data.get('week_start', 'Unknown')
    
    message = f"🏠 *Sanihome AC Opportunities - Follow-up*\n\n"
    message += f"Week of {week_start}\n\n"
    message += f"📋 *Status Check:*\n"
    message += f"• Total opportunities sent: {len(opportunities)}\n"
    message += f"• Total clients: {sum(opp.get('client_count', 0) for opp in opportunities)}\n"
    message += f"• Total value: AED {sum(opp.get('estimated_value', 0) for opp in opportunities):,}\n\n"
    message += f"*Questions for frontdesk team:*\n"
    message += f"1. How many Sanihome customers have you contacted so far?\n"
    message += f"2. How many have booked AC cleaning services?\n"
    message += f"3. Do you need more opportunities or should we wait?\n\n"
    message += f"Please reply with progress update. Thanks!"
    
    try:
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',
            '--message', message
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Follow-up message sent to JV")
        else:
            print(f"Error sending follow-up: {result.stderr}")
            
    except Exception as e:
        print(f"Error sending follow-up: {e}")

def should_generate_new_opportunities():
    """Check if we should generate new opportunities based on response"""
    
    # This would ideally check for a response file or database entry
    # For now, we'll assume manual confirmation is needed
    return False

def main():
    """Main function for follow-up"""
    
    # Check if it's Thursday (3 days after Monday)
    today = datetime.datetime.now().weekday()
    if today != 3:  # 3 = Thursday
        print("Follow-up is scheduled for Thursdays only.")
        return
    
    print("Checking Sanihome AC opportunities progress...")
    
    current_data = check_progress()
    if not current_data:
        print("No current opportunities to follow up on")
        return
    
    # Check if follow-up is needed
    if not current_data.get('follow_up_needed', False):
        print("Follow-up not needed for current opportunities")
        return
    
    # Send follow-up message
    send_follow_up_message(current_data)
    
    print("\n✅ Follow-up message sent!")
    print("Waiting for response before generating new opportunities...")

if __name__ == "__main__":
    main()