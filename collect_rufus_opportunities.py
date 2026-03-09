#!/usr/bin/env python3
"""
Rufus AI Opportunities Collector
Fetches qualified opportunities from Rufus AI (Marketing HQ) and sends to frontdesk
"""

import json
import subprocess
import datetime
import requests
from pathlib import Path

def get_rufus_opportunities():
    """Fetch opportunities from Rufus AI via WordPress REST API or direct database"""
    
    # Try to access via custom REST endpoint first
    endpoints = [
        "https://mcc.saniservice.com/wp-json/mcc/v1/rufus-opportunities",
        "https://mcc.saniservice.com/wp-json/mcc/v1/opportunities",
        "https://mcc.saniservice.com/wp-admin/admin-ajax.php?action=get_rufus_opportunities"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data
        except:
            continue
    
    # If REST API fails, try to access via WordPress CLI or direct query
    try:
        # Use WP-CLI if available
        result = subprocess.run([
            "wp", "db", "query", 
            "SELECT * FROM wp_mcc_rufus_insights WHERE insight_type = 'opportunity' AND status = 'active' ORDER BY FIELD(priority, 'urgent', 'high', 'medium', 'low'), estimated_value DESC LIMIT 50",
            "--skip-column-names",
            "--format=json"
        ], capture_output=True, text=True, cwd="/Users/victor/clawd/MCC")
        
        if result.returncode == 0:
            opportunities = json.loads(result.stdout)
            return opportunities
    except:
        pass
    
    return []

def format_opportunities_summary(opportunities):
    """Format Rufus opportunities for frontdesk team"""
    
    if not opportunities:
        return "No new qualified opportunities from Rufus AI today."
    
    summary = f"📊 *Rufus AI Qualified Opportunities*\n"
    summary += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    # Group by priority
    by_priority = {'urgent': [], 'high': [], 'medium': [], 'low': []}
    
    for opp in opportunities:
        priority = opp.get('priority', 'medium').lower()
        if priority in by_priority:
            by_priority[priority].append(opp)
    
    # Show opportunities by priority
    for priority, opps in by_priority.items():
        if not opps:
            continue
            
        priority_emoji = {'urgent': '🚨', 'high': '🔥', 'medium': '⚡', 'low': '💡'}.get(priority, '•')
        summary += f"*{priority_emoji} {priority.upper()} PRIORITY*\n"
        
        for opp in opps[:3]:  # Show top 3 per priority
            title = opp.get('title', 'No Title')
            client_count = opp.get('client_count', 0)
            estimated_value = float(opp.get('estimated_value', 0))
            description = opp.get('description', '')[:100] + '...' if len(opp.get('description', '')) > 100 else opp.get('description', '')
            
            summary += f"• *{title}*\n"
            summary += f"  👥 {client_count} clients | 💰 AED {estimated_value:,.0f}\n"
            summary += f"  📝 {description}\n\n"
    
    # Calculate totals
    total_opportunities = len(opportunities)
    total_clients = sum(int(opp.get('client_count', 0)) for opp in opportunities)
    total_value = sum(float(opp.get('estimated_value', 0)) for opp in opportunities)
    
    summary += f"*Summary:*\n"
    summary += f"• Total Opportunities: {total_opportunities}\n"
    summary += f"• Total Potential Clients: {total_clients:,}\n"
    summary += f"• Total Estimated Value: AED {total_value:,.0f}"
    
    return summary

def send_to_frontdesk(opportunities):
    """Send qualified opportunities to frontdesk team"""
    
    if not opportunities:
        print("No opportunities to send")
        return
    
    summary = format_opportunities_summary(opportunities)
    
    # Send to JV first, then to frontdesk team
    try:
        # Send to JV
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',
            '--message', summary
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Sent {len(opportunities)} Rufus opportunities to JV")
        else:
            print(f"Error sending to JV: {result.stderr}")
            
        # Also send to frontdesk team email
        frontdesk_summary = summary.replace('*', '').replace('_', '')  # Remove markdown for email
        
        # Send email to frontdesk team
        email_result = subprocess.run([
            'python3', '/Users/victor/clawd/scripts/email_client.py', 'send',
            '--to', 'frontdesk@saniservice.com',
            '--subject', f'Rufus AI Opportunities - {datetime.datetime.now().strftime("%Y-%m-%d")}',
            '--message', frontdesk_summary
        ], capture_output=True, text=True)
        
        if email_result.returncode == 0:
            print(f"Sent opportunities to frontdesk@saniservice.com")
        else:
            print(f"Email error: {email_result.stderr}")
            
    except Exception as e:
        print(f"Error sending opportunities: {e}")

def main():
    """Main function to collect and distribute Rufus AI opportunities"""
    
    print("Fetching qualified opportunities from Rufus AI...")
    opportunities = get_rufus_opportunities()
    
    if opportunities:
        print(f"Found {len(opportunities)} qualified opportunities from Rufus")
        
        # Filter for high-value opportunities (client count > 5 or value > AED 5000)
        high_value_opps = [
            opp for opp in opportunities 
            if int(opp.get('client_count', 0)) > 5 or float(opp.get('estimated_value', 0)) > 5000
        ]
        
        if high_value_opps:
            print(f"Sending {len(high_value_opps)} high-value opportunities to frontdesk")
            send_to_frontdesk(high_value_opps)
        else:
            # Send all opportunities if none meet high-value criteria
            print("Sending all opportunities to frontdesk")
            send_to_frontdesk(opportunities)
            
        # Save all opportunities to file for record
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        filepath = Path(f"/Users/victor/clawd/memory/rufus-opportunities-{today}.json")
        
        with open(filepath, 'w') as f:
            json.dump(opportunities, f, indent=2, default=str)
            
        print(f"All opportunities saved to {filepath}")
        
    else:
        print("No opportunities found from Rufus AI today")

if __name__ == "__main__":
    main()