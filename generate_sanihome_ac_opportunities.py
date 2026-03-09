#!/usr/bin/env python3
"""
Sanihome AC Cleaning Opportunities Generator
Manually generates Sanihome AC cleaning opportunities every Monday
"""

import json
import subprocess
import datetime
import time
from pathlib import Path

def generate_sanihome_ac_opportunities():
    """Generate Sanihome AC cleaning opportunities"""
    
    # Sample Sanihome AC cleaning opportunities
    opportunities = [
        {
            "id": 1,
            "title": "Sanihome AC Cleaning - Quarterly Service Due",
            "description": "Sanihome customers due for quarterly AC cleaning and disinfection service",
            "service_type": "AC Cleaning",
            "client_type": "residential",
            "client_count": 25,
            "estimated_value": 12500,
            "priority": "medium",
            "notes": "Focus on customers who haven't had AC cleaning service in 3+ months"
        },
        {
            "id": 2,
            "title": "Sanihome AC Deep Cleaning - Pre-Summer Prep",
            "description": "Pre-summer AC deep cleaning for Sanihome customers - prepare for hot weather",
            "service_type": "AC Deep Cleaning",
            "client_type": "residential", 
            "client_count": 18,
            "estimated_value": 18000,
            "priority": "high",
            "notes": "Target customers before summer season starts. Emphasize improved cooling efficiency"
        },
        {
            "id": 3,
            "title": "Sanihome AC Cleaning - Missed Service Reactivation",
            "description": "Reactivate Sanihome customers who missed their scheduled AC cleaning service",
            "service_type": "AC Cleaning",
            "client_type": "residential",
            "client_count": 32,
            "estimated_value": 19200,
            "priority": "medium",
            "notes": "Customers who cancelled or postponed AC cleaning in the last 6 months"
        }
    ]
    
    return opportunities

def format_sanihome_summary(opportunities):
    """Format Sanihome opportunities for frontdesk"""
    
    # WhatsApp format for JV
    summary = f"🏠 *Sanihome AC Cleaning Opportunities* 🧽\n"
    summary += f"Week of {datetime.datetime.now().strftime('%B %d, %Y')}\n\n"
    
    for i, opp in enumerate(opportunities, 1):
        summary += f"*{i}. {opp['title']}*\n"
        summary += f"📝 {opp['description']}\n"
        summary += f"👥 {opp['client_count']} clients | 💰 AED {opp['estimated_value']:,}\n"
        summary += f"⚡ Priority: {opp['priority'].upper()}\n"
        summary += f"💡 Notes: {opp['notes']}\n\n"
    
    total_clients = sum(opp['client_count'] for opp in opportunities)
    total_value = sum(opp['estimated_value'] for opp in opportunities)
    
    summary += f"*Total for this week:*\n"
    summary += f"• {len(opportunities)} opportunity batches\n"
    summary += f"• {total_clients} potential clients\n"
    summary += f"• AED {total_value:,} estimated value\n\n"
    summary += f"Please start calling these Sanihome customers for AC cleaning this week.\n"
    summary += f"I'll check back on Thursday to see progress."
    
    return summary

def format_sanihome_email_html(opportunity):
    """Format a single Sanihome opportunity as HTML email"""
    
    # Map priority to color
    priority_color = {
        'high': '#ff0000',
        'medium': '#ff9800', 
        'low': '#4CAF50'
    }.get(opportunity['priority'], '#ff9800')
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Opportunity: {opportunity['title']}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, sans-serif;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="background-color: #ffffff; max-width: 600px;">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #001F3F; color: #ffffff; padding: 15px 20px; font-size: 18px; font-weight: bold;">
                            Saniservice · Frontdesk Opportunities
                        </td>
                    </tr>
                    
                    <!-- Title -->
                    <tr>
                        <td style="padding: 20px 20px 0 20px;">
                            <h1 style="font-size: 20px; margin: 0; color: #333333; font-weight: bold;">{opportunity['title']}</h1>
                        </td>
                    </tr>
                    
                    <!-- Greeting -->
                    <tr>
                        <td style="padding: 15px 20px;">
                            <p style="margin: 0 0 10px 0; color: #333333; font-size: 14px; line-height: 1.5;">Hi JV de Castro,</p>
                            <p style="margin: 0; color: #333333; font-size: 14px; line-height: 1.5;">A new opportunity has been identified for the frontdesk team. Please review the details below and start reaching out to the assigned clients.</p>
                        </td>
                    </tr>
                    
                    <!-- Details Table -->
                    <tr>
                        <td style="padding: 0 20px;">
                            <table role="presentation" cellpadding="8" cellspacing="0" border="1" bordercolor="#dddddd" style="width: 100%; border-collapse: collapse; font-size: 14px;">
                                <tr style="background-color: #f9f9f9;">
                                    <th style="text-align: left; width: 30%; font-weight: bold; color: #333333;">Opportunity</th>
                                    <td style="text-align: left; color: #333333;">{opportunity['title']}</td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Type</th>
                                    <td style="text-align: left; color: #333333;">{opportunity['service_type']} · {opportunity['client_type'].title()}</td>
                                </tr>
                                <tr style="background-color: #f9f9f9;">
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Priority</th>
                                    <td style="text-align: left; color: {priority_color}; font-weight: bold;">{opportunity['priority'].upper()}</td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Clients</th>
                                    <td style="text-align: left; color: #333333;">{opportunity['client_count']} to contact</td>
                                </tr>
                                <tr style="background-color: #f9f9f9;">
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Segment</th>
                                    <td style="text-align: left; color: #333333;">{opportunity['client_type'].title()}</td>
                                </tr>
                                <tr>
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Est. Value</th>
                                    <td style="text-align: left; color: #333333;">AED {opportunity['estimated_value']:,}</td>
                                </tr>
                                <tr style="background-color: #f9f9f9;">
                                    <th style="text-align: left; font-weight: bold; color: #333333;">Channel</th>
                                    <td style="text-align: left; color: #333333;">Call</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Opportunity Details Section -->
                    <tr>
                        <td style="padding: 15px 20px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="background-color: #ADD8E6; padding: 15px; border-radius: 4px;">
                                        <h2 style="font-size: 16px; margin: 0 0 10px 0; color: #333333; font-weight: bold;">Opportunity Details</h2>
                                        <p style="margin: 0; color: #333333; font-size: 14px; line-height: 1.5;">{opportunity['description']}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Notes Section -->
                    <tr>
                        <td style="padding: 0 20px 15px 20px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td style="background-color: #FFFFE0; padding: 15px; border-radius: 4px;">
                                        <h2 style="font-size: 16px; margin: 0 0 10px 0; color: #333333; font-weight: bold;">📝 Notes & Action Items</h2>
                                        <p style="margin: 0; color: #333333; font-size: 14px; line-height: 1.5;">{opportunity['notes']}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Button -->
                    <tr>
                        <td style="padding: 10px 20px 20px 20px; text-align: center;">
                            <a href="https://mcc.saniservice.com/wp-admin/admin.php?page=frontdesk-opportunities&project_id={opportunity['id']}" style="display: inline-block; background-color: #4CAF50; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 14px;">View Clients & Start Calling →</a>
                        </td>
                    </tr>
                    
                    <!-- How it works -->
                    <tr>
                        <td style="padding: 0 20px;">
                            <p style="margin: 0 0 10px 0; color: #666666; font-size: 13px;">You'll be prompted to log in if not already authenticated.</p>
                            <p style="margin: 0 0 20px 0; color: #333333; font-size: 13px;"><em>How it works:</em> View client list → Call or WhatsApp each client → Mark outcome (Won / Lost / No Reply) → Add notes → Schedule callbacks</p>
                        </td>
                    </tr>
                    
                    <!-- Signature -->
                    <tr>
                        <td style="padding: 0 20px 20px 20px;">
                            <p style="margin: 0; color: #333333; font-size: 14px;">Best regards,<br><strong>Viktor</strong> · Frontdesk Services Specialist</p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 0 20px 20px 20px;">
                            <p style="margin: 0; color: #666666; font-size: 12px;"><em>Automated notification from Sanihome AC Opportunities System</em> <a href="https://mcc.saniservice.com" style="color: #4CAF50;">https://mcc.saniservice.com</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html_content

def send_to_frontdesk(opportunities):
    """Send Sanihome opportunities to frontdesk team"""
    
    # Format for WhatsApp (markdown) - send all opportunities in one message
    whatsapp_summary = format_sanihome_summary(opportunities)
    
    try:
        # Send to JV first via WhatsApp
        result = subprocess.run([
            'python3', '/Users/victor/clawd/message.py', 'send',
            '--channel', 'whatsapp',
            '--to', '+971543062826',
            '--message', whatsapp_summary
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Sent Sanihome opportunities to JV via WhatsApp")
        else:
            print(f"Error sending to JV: {result.stderr}")
            
        # Get email password from keychain
        keychain_result = subprocess.run(['python3', '/Users/victor/clawd/keychain.py', 'get', 'saniservice_email'], 
                                       capture_output=True, text=True)
        email_pass = keychain_result.stdout.strip() if keychain_result.returncode == 0 else None
        
        if not email_pass:
            print("Could not retrieve email password from keychain")
            return
        
        # Set environment variable for email client
        env = os.environ.copy()
        env['EMAIL_PASS'] = email_pass
        
        # Send individual emails for each opportunity
        for i, opportunity in enumerate(opportunities, 1):
            # Format individual opportunity as HTML
            email_html = format_sanihome_email_html(opportunity)
            
            # Send to JV
            email_result_jv = subprocess.run([
                'python3', '/Users/victor/clawd/scripts/email_client.py', 'send',
                'jv@saniservice.com',
                f'Sanihome AC Opportunity: {opportunity["title"]}',
                email_html
            ], capture_output=True, text=True, env=env)
            
            if email_result_jv.returncode == 0:
                print(f"Sent opportunity {i} to JV via email")
            else:
                print(f"Email error to JV for opportunity {i}: {email_result_jv.stderr}")
            
            # Send to frontdesk team
            email_result = subprocess.run([
                'python3', '/Users/victor/clawd/scripts/email_client.py', 'send',
                'frontdesk@saniservice.com',
                f'Sanihome AC Opportunity: {opportunity["title"]}',
                email_html
            ], capture_output=True, text=True, env=env)
            
            if email_result.returncode == 0:
                print(f"Sent opportunity {i} to frontdesk@saniservice.com")
            else:
                print(f"Email error to frontdesk for opportunity {i}: {email_result.stderr}")
            
            # Small delay between emails to avoid rate limiting
            time.sleep(2)
            
    except Exception as e:
        print(f"Error sending opportunities: {e}")

def save_opportunities(opportunities):
    """Save opportunities to track progress"""
    
    week_start = datetime.datetime.now().strftime('%Y-%m-%d')
    filepath = Path(f"/Users/victor/clawd/memory/sanihome-ac-opportunities-{week_start}.json")
    
    data = {
        "week_start": week_start,
        "generated_date": datetime.datetime.now().isoformat(),
        "status": "sent",
        "opportunities": opportunities,
        "follow_up_needed": True,
        "follow_up_date": (datetime.datetime.now() + datetime.timedelta(days=3)).strftime('%Y-%m-%d')  # Thursday check
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Opportunities saved to {filepath}")
    return filepath

def main():
    """Main function to generate and send Sanihome AC opportunities"""
    
    # Check if it's Monday
    today = datetime.datetime.now().weekday()
    if today != 0:  # 0 = Monday
        print("Today is not Monday. Sanihome opportunities are only generated on Mondays.")
        return
    
    print("Generating Sanihome AC cleaning opportunities for Monday...")
    opportunities = generate_sanihome_ac_opportunities()
    
    if opportunities:
        print(f"Generated {len(opportunities)} Sanihome AC opportunities")
        
        # Send to frontdesk
        send_to_frontdesk(opportunities)
        
        # Save for tracking
        save_opportunities(opportunities)
        
        print("\n✅ Sanihome opportunities sent successfully!")
        print("I'll check back on Thursday to see their progress.")
        
    else:
        print("No opportunities generated")

if __name__ == "__main__":
    main()