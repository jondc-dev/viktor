#!/usr/bin/env python3
"""
Meta Ads Daily Performance Report Generator
Fetches yesterday's performance data and current campaign status
"""

import requests
import json
from datetime import datetime, timedelta
import os

def get_meta_ads_data():
    """Fetch Meta Ads performance data"""
    
    # API credentials from memory/meta-api-credentials.md
    ad_account_id = "act_726886276488702"
    access_token = "EAAOyW0zd9X0BQ42UUvY0NInCBj3uZBcnGcmpLvLtpZBNzM3iLK0lzZBIopxxBJzrztUruFdku3OtZBJs7mZAIu8OYvPPdeJAodt06lvd8YFKeRZA3DGFW57AsRZB74eZAoYGEH3fHZAAjf1MJjs7UjHi7jlZCpaZCzzzeIZBsuWeFqMdJIjp87HScSgpuLACYNfuZACytSgZDZD"
    
    # Calculate date range (yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    date_preset = "yesterday"
    
    # Insights endpoint
    insights_url = f"https://graph.facebook.com/v18.0/{ad_account_id}/insights"
    
    # Parameters for insights
    insights_params = {
        'access_token': access_token,
        'date_preset': date_preset,
        'fields': 'spend,impressions,clicks,actions,action_values,campaign_name',
        'level': 'campaign',
        'time_increment': 1
    }
    
    # Campaigns endpoint for current status
    campaigns_url = f"https://graph.facebook.com/v18.0/{ad_account_id}/campaigns"
    campaign_params = {
        'access_token': access_token,
        'fields': 'name,status,effective_status,daily_budget,lifetime_budget',
        'effective_status': '["ACTIVE","PAUSED"]'  # Only active and paused campaigns
    }
    
    try:
        # Fetch insights data
        print("Fetching insights data...")
        insights_response = requests.get(insights_url, params=insights_params)
        insights_data = insights_response.json()
        
        # Fetch campaigns data
        print("Fetching campaigns data...")
        campaigns_response = requests.get(campaigns_url, params=campaign_params)
        campaigns_data = campaigns_response.json()
        
        return {
            'insights': insights_data,
            'campaigns': campaigns_data,
            'date': yesterday.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_metrics(insights_data):
    """Calculate key performance metrics"""
    
    total_spend = 0
    total_impressions = 0
    total_clicks = 0
    total_leads = 0
    
    if 'data' in insights_data:
        for campaign in insights_data['data']:
            total_spend += float(campaign.get('spend', 0))
            total_impressions += int(campaign.get('impressions', 0))
            total_clicks += int(campaign.get('clicks', 0))
            
            # Count leads from actions
            if 'actions' in campaign:
                for action in campaign['actions']:
                    if action.get('action_type') in ['lead', 'leadgen', 'offsite_conversion.lead']:
                        total_leads += int(action.get('value', 0))
    
    # Calculate derived metrics
    cpc = total_spend / total_clicks if total_clicks > 0 else 0
    cpl = total_spend / total_leads if total_leads > 0 else 0
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    return {
        'total_spend': round(total_spend, 2),
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'total_leads': total_leads,
        'cpc': round(cpc, 2),
        'cpl': round(cpl, 2),
        'ctr': round(ctr, 2)
    }

def generate_report():
    """Generate the daily Meta Ads report"""
    
    print("Generating Meta Ads Daily Report...")
    data = get_meta_ads_data()
    
    if not data:
        return "❌ Error: Could not fetch Meta Ads data. Please check API credentials and account status."
    
    insights = data['insights']
    campaigns = data['campaigns']
    report_date = data['date']
    
    # Calculate metrics
    metrics = calculate_metrics(insights)
    
    # Convert spend to AED (assuming USD, rough conversion)
    aed_rate = 3.67
    total_spend_aed = metrics['total_spend'] * aed_rate
    cpl_aed = metrics['cpl'] * aed_rate
    
    # Budget target
    daily_budget_aed = 100
    budget_status = "✅ Within budget" if total_spend_aed <= daily_budget_aed else "⚠️ Over budget"
    
    # Generate report text
    report = f"""📊 **Daily Meta Ads Report - {report_date}**

**YESTERDAY'S PERFORMANCE:**
• Total Spend: ${metrics['total_spend']} (AED {total_spend_aed:.2f})
• Impressions: {metrics['total_impressions']:,}
• Clicks: {metrics['total_clicks']:,}
• CTR: {metrics['ctr']}%
• Leads Generated: {metrics['total_leads']}
• Cost Per Lead: ${metrics['cpl']} (AED {cpl_aed:.2f})

**CURRENT CAMPAIGNS:**
"""
    
    # Add campaign details
    if 'data' in campaigns:
        active_campaigns = [c for c in campaigns['data'] if c.get('effective_status') == 'ACTIVE']
        paused_campaigns = [c for c in campaigns['data'] if c.get('effective_status') == 'PAUSED']
        
        report += f"• Active: {len(active_campaigns)} campaigns\n"
        report += f"• Paused: {len(paused_campaigns)} campaigns\n\n"
        
        if active_campaigns:
            report += "**ACTIVE CAMPAIGNS:**\n"
            for campaign in active_campaigns[:5]:  # Show top 5
                name = campaign.get('name', 'Unknown')
                daily_budget = campaign.get('daily_budget', 'N/A')
                if daily_budget != 'N/A':
                    daily_budget_aed = float(daily_budget) / 100 * aed_rate  # Budget in cents
                    report += f"• {name} (Budget: AED {daily_budget_aed:.2f}/day)\n"
                else:
                    report += f"• {name}\n"
    
    report += f"""
**BUDGET STATUS:**
• Daily Budget Target: AED {daily_budget_aed}
• Yesterday's Spend: AED {total_spend_aed:.2f}
• Budget Utilization: {(total_spend_aed/daily_budget_aed*100):.1f}%
• Status: {budget_status}

**RECOMMENDATIONS:**
"""
    
    # Add recommendations based on performance
    if metrics['total_leads'] < 3:
        report += "• ⚠️ Low lead volume - consider increasing budget or optimizing targeting\n"
    elif metrics['total_leads'] > 5:
        report += "• ✅ Good lead volume - maintain current strategy\n"
    
    if metrics['cpl'] > 15:  # High CPL in USD
        report += "• ⚠️ High cost per lead - review targeting and creative\n"
    elif metrics['cpl'] < 8:
        report += "• ✅ Good cost efficiency - consider scaling\n"
    
    if total_spend_aed > daily_budget_aed:
        report += "• 🚨 Budget exceeded - pause high-cost campaigns immediately\n"
    
    report += "\n**ATTRIBUTION UPDATE:**\n• Meta leads should now show correct source in CRM\n• Cross-check with your lead quality feedback"
    
    return report

if __name__ == "__main__":
    report = generate_report()
    print(report)