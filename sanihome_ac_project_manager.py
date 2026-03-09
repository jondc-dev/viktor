#!/usr/bin/env python3
"""
Sanihome AC Opportunities Project Manager
Manages the weekly Sanihome AC opportunities as a continuing project
"""

import json
import subprocess
import datetime
from pathlib import Path

PROJECT_FILE = "/Users/victor/clawd/memory/sanihome-ac-project.json"

def load_project():
    """Load current project status"""
    if Path(PROJECT_FILE).exists():
        with open(PROJECT_FILE, 'r') as f:
            return json.load(f)
    return None

def save_project(project_data):
    """Save project status"""
    with open(PROJECT_FILE, 'w') as f:
        json.dump(project_data, f, indent=2)

def create_new_week_project():
    """Create a new weekly project"""
    
    week_start = datetime.datetime.now()
    week_number = week_start.isocalendar()[1]
    
    project = {
        "week": week_number,
        "week_start": week_start.strftime('%Y-%m-%d'),
        "status": "active",
        "phase": "generation",  # generation, calling, followup, complete
        "opportunities": [
            {
                "title": "Sanihome AC Cleaning - Quarterly Service Due",
                "description": "Sanihome customers due for quarterly AC cleaning and disinfection service",
                "client_count": 28,
                "estimated_value": 16800,
                "priority": "high",
                "notes": "Focus on customers in Jumeirah, Springs, Meadows areas who haven't had AC cleaning in 3+ months"
            },
            {
                "title": "Sanihome AC Deep Cleaning - Pre-Summer Prep",
                "description": "Deep AC cleaning service before summer heat begins - prepare units for hot weather",
                "client_count": 22,
                "estimated_value": 22000,
                "priority": "high",
                "notes": "Target villas and larger apartments. Emphasize summer preparation and improved cooling efficiency"
            },
            {
                "title": "Sanihome AC Cleaning - Missed Service Reactivation",
                "description": "Reactivate Sanihome customers who missed their scheduled AC cleaning service",
                "client_count": 35,
                "estimated_value": 21000,
                "priority": "medium",
                "notes": "Customers who cancelled or postponed AC cleaning in the last 6 months - perfect time before summer"
            }
        ],
        "schedule": {
            "generation_day": "Monday",
            "first_followup": "Wednesday",
            "second_followup": "Friday",
            "completion_target": "Following Monday"
        },
        "progress": {
            "contacts_made": 0,
            "bookings_confirmed": 0,
            "completion_percentage": 0,
            "notes": []
        },
        "follow_up_needed": True,
        "next_action": "send_opportunities"
    }
    
    return project

def send_opportunities(project):
    """Send opportunities to frontdesk team"""
    
    opportunities = project["opportunities"]
    week_start = project["week_start"]
    
    summary = f"🏠 *Sanihome AC Cleaning Opportunities - Week of {week_start}*\n\n"
    
    for i, opp in enumerate(opportunities, 1):
        summary += f"*{i}. {opp['title']}*\n"
        summary += f"📝 {opp['description']}\n"
        summary += f"👥 {opp['client_count']} clients | 💰 AED {opp['estimated_value']:,}\n"
        summary += f"⚡ Priority: {opp['priority'].upper()}\n"
        summary += f"💡 Notes: {opp['notes']}\n\n"
    
    total_clients = sum(opp['client_count'] for opp in opportunities)
    total_value = sum(opp['estimated_value'] for opp in opportunities)
    
    summary += f"*Weekly Total:* {total_clients} clients, AED {total_value:,}\n\n"
    summary += f"📅 *Schedule:*\n"
    summary += f"• Monday: Opportunities sent\n"
    summary += f"• Wednesday: First follow-up\n"
    summary += f"• Friday: Second follow-up\n"
    summary += f"• Next Monday: New opportunities (if this week complete)\n\n"
    summary += f"Please start calling today. I'll check progress on Wednesday!"
    
    try:
        # Send to JV
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',
            '--message', summary
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Opportunities sent to JV")
        else:
            print(f"❌ Error sending to JV: {result.stderr}")
            
        # Send to frontdesk email
        email_summary = summary.replace('*', '').replace('_', '')
        
        email_result = subprocess.run([
            'python3', '/Users/victor/clawd/scripts/email_client.py', 'send',
            '--to', 'frontdesk@saniservice.com',
            '--subject', f'Sanihome AC Opportunities - Week of {week_start}',
            '--message', email_summary
        ], capture_output=True, text=True)
        
        if email_result.returncode == 0:
            print("✅ Opportunities sent to frontdesk@saniservice.com")
        else:
            print(f"❌ Email error: {email_result.stderr}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error sending opportunities: {e}")
        return False

def send_follow_up(project, follow_up_number):
    """Send follow-up message"""
    
    week_start = project["week_start"]
    progress = project.get("progress", {})
    
    if follow_up_number == 1:
        day = "Wednesday"
        message = f"📞 *Sanihome AC Follow-up #1 - {day}*\n\n"
    else:
        day = "Friday" 
        message = f"📞 *Sanihome AC Follow-up #2 - {day}*\n\n"
    
    message += f"Week of {week_start}\n\n"
    message += f"*Quick Status Check:*\n"
    message += f"• How many Sanihome AC cleaning customers have you contacted so far?\n"
    message += f"• How many AC cleaning bookings confirmed?\n"
    message += f"• Any challenges or questions about AC cleaning services?\n\n"
    
    if progress.get('contacts_made', 0) > 0:
        completion = progress.get('completion_percentage', 0)
        message += f"*Current Progress:* {completion}% complete\n"
        message += f"*Contacts Made:* {progress['contacts_made']}\n"
        message += f"*Bookings Confirmed:* {progress.get('bookings_confirmed', 0)}\n\n"
    
    if follow_up_number == 1:
        message += f"Please reply with your progress. Thanks! 👍"
    else:
        message += f"Please let me know if you need more opportunities or if we should wait until next week."
    
    try:
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',
            '--message', message
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Follow-up #{follow_up_number} sent")
            return True
        else:
            print(f"❌ Error sending follow-up: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending follow-up: {e}")
        return False

def handle_monday():
    """Handle Monday - generate and send new opportunities"""
    
    print("🗓️  Monday: Generating new Sanihome AC opportunities...")
    
    # Check if previous week is complete
    current_project = load_project()
    if current_project and current_project.get('status') == 'active':
        print("⚠️  Previous week still active. Checking if complete...")
        
        # If we haven't heard back, assume it's complete after 2 weeks
        week_start = datetime.datetime.fromisoformat(current_project['week_start'])
        if (datetime.datetime.now() - week_start).days > 14:
            print("Marking previous week as complete (no response after 2 weeks)")
            current_project['status'] = 'complete'
            save_project(current_project)
        else:
            print("Previous week still in progress. Skipping new generation.")
            return
    
    # Create new week project
    new_project = create_new_week_project()
    
    # Send opportunities
    if send_opportunities(new_project):
        new_project['phase'] = 'calling'
        new_project['next_action'] = 'first_followup'
        save_project(new_project)
        print("✅ New week started successfully!")
    else:
        print("❌ Failed to send opportunities")

def handle_wednesday():
    """Handle Wednesday - first follow-up"""
    
    print("🗓️  Wednesday: First follow-up on Sanihome opportunities...")
    
    current_project = load_project()
    if not current_project or current_project.get('status') != 'active':
        print("No active project to follow up on")
        return
    
    if send_follow_up(current_project, 1):
        current_project['phase'] = 'followup'
        current_project['next_action'] = 'second_followup'
        save_project(current_project)
        print("✅ First follow-up completed!")

def handle_friday():
    """Handle Friday - second follow-up"""
    
    print("🗓️  Friday: Second follow-up on Sanihome opportunities...")
    
    current_project = load_project()
    if not current_project or current_project.get('status') != 'active':
        print("No active project to follow up on")
        return
    
    if send_follow_up(current_project, 2):
        current_project['phase'] = 'final_check'
        current_project['next_action'] = 'wait_for_response'
        save_project(current_project)
        print("✅ Second follow-up completed!")
        print("📋 Waiting for response before next Monday...")

def main():
    """Main function - route to appropriate day handler"""
    
    today = datetime.datetime.now().weekday()
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_name = day_names[today]
    
    print(f"🗓️  Today is {day_name}")
    
    if today == 0:  # Monday
        handle_monday()
    elif today == 2:  # Wednesday
        handle_wednesday()
    elif today == 4:  # Friday
        handle_friday()
    else:
        print("No action scheduled for today")

if __name__ == "__main__":
    main()