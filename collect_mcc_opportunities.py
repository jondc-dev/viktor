#!/usr/bin/env python3
"""
Marketing HQ Opportunities Collector
Fetches qualified opportunities from MCC Marketing HQ using Rufus AI validation
"""

import requests
import json
import datetime
import subprocess
from pathlib import Path

def get_mcc_opportunities():
    """Fetch opportunities from Marketing HQ API"""
    
    # MCC API endpoint for marketing opportunities
    api_url = "https://mcc.saniservice.com/wp-json/mcc/v1/marketing-opportunities"
    
    try:
        response = requests.get(api_url, timeout=30)
        if response.status_code == 200:
            opportunities = response.json()
            return opportunities
        else:
            print(f"Error accessing MCC API: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching opportunities: {e}")
        return []

def format_opportunity_summary(opportunities):
    """Format opportunities for frontdesk team"""
    
    if not opportunities:
        return "No new qualified opportunities today."
    
    summary = f"📊 *Qualified Opportunities from Rufus AI*\n"
    summary += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    # Group by service type
    by_service = {}
    for opp in opportunities:
        service = opp.get('service_type', 'General')
        if service not in by_service:
            by_service[service] = []
        by_service[service].append(opp)
    
    for service, opps in by_service.items():
        summary += f"*{service} Opportunities:*\n"
        for opp in opps[:3]:  # Show top 3 per service
            title = opp.get('title', 'No Title')
            count = opp.get('real_client_count', 0)
            value = opp.get('estimated_value', 0)
            summary += f"• {title}\n"
            summary += f"  👥 {count} clients | 💰 AED {value:,}\n\n"
    
    total_clients = sum(opp.get('real_client_count', 0) for opp in opportunities)
    total_value = sum(opp.get('estimated_value', 0) for opp in opportunities)
    
    summary += f"*Total:* {len(opportunities)} opportunities\n"
    summary += f"*Potential Reach:* {total_clients} clients\n"
    summary += f"*Estimated Value:* AED {total_value:,}"
    
    return summary

def send_to_frontdesk(opportunities):
    """Send qualified opportunities to frontdesk team"""
    
    summary = format_opportunity_summary(opportunities)
    
    # Send via WhatsApp to frontdesk team
    try:
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',  # JV first
            '--message', summary
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Opportunities sent to frontdesk successfully")
        else:
            print(f"Error sending: {result.stderr}")
            
    except Exception as e:
        print(f"Error sending message: {e}")

def main():
    """Main function to collect and distribute opportunities"""
    
    print("Fetching qualified opportunities from Marketing HQ...")
    opportunities = get_mcc_opportunities()
    
    if opportunities:
        print(f"Found {len(opportunities)} qualified opportunities")
        
        # Filter for high-value opportunities (real client count > 10)
        high_value_opps = [opp for opp in opportunities if opp.get('real_client_count', 0) > 10]
        
        if high_value_opps:
            print(f"Sending {len(high_value_opps)} high-value opportunities to frontdesk")
            send_to_frontdesk(high_value_opps)
        else:
            print("No high-value opportunities found today")
            
        # Save all opportunities to file for record
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        filepath = Path(f"/Users/victor/clawd/memory/opportunities_{today}.json")
        
        with open(filepath, 'w') as f:
            json.dump(opportunities, f, indent=2)
            
        print(f"All opportunities saved to {filepath}")
        
    else:
        print("No opportunities found today")

if __name__ == "__main__":
    main()