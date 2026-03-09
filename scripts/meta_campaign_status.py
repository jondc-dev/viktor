#!/usr/bin/env python3
"""
Check Meta Ads campaign status and details
"""

import requests
import json
from datetime import datetime

def get_campaign_details():
    """Get detailed campaign information"""
    
    ad_account_id = "act_726886276488702"
    access_token = "EAAOyW0zd9X0BQ42UUvY0NInCBj3uZBcnGcmpLvLtpZBNzM3iLK0lzZBIopxxBJzrztUruFdku3OtZBJs7mZAIu8OYvPPdeJAodt06lvd8YFKeRZA3DGFW57AsRZB74eZAoYGEH3fHZAAjf1MJjs7UjHi7jlZCpaZCzzzeIZBsuWeFqMdJIjp87HScSgpuLACYNfuZACytSgZDZD"
    
    # Get all campaigns with details
    campaigns_url = f"https://graph.facebook.com/v18.0/{ad_account_id}/campaigns"
    params = {
        'access_token': access_token,
        'fields': 'name,status,effective_status,daily_budget,lifetime_budget,objective,created_time',
        'limit': 50
    }
    
    try:
        response = requests.get(campaigns_url, params=params)
        data = response.json()
        
        print("📋 META ADS CAMPAIGN STATUS")
        print("=" * 50)
        
        if 'data' in data:
            active_count = 0
            paused_count = 0
            
            for campaign in data['data']:
                name = campaign.get('name', 'Unknown')
                status = campaign.get('effective_status', 'Unknown')
                objective = campaign.get('objective', 'Unknown')
                daily_budget = campaign.get('daily_budget', 'N/A')
                created = campaign.get('created_time', 'Unknown')
                
                if status == 'ACTIVE':
                    active_count += 1
                    status_icon = "🟢"
                elif status in ['PAUSED', 'ADSET_PAUSED', 'CAMPAIGN_PAUSED']:
                    paused_count += 1
                    status_icon = "🔴"
                else:
                    status_icon = "⚪"
                
                print(f"{status_icon} {name}")
                print(f"   Status: {status}")
                print(f"   Objective: {objective}")
                if daily_budget != 'N/A':
                    budget_aed = float(daily_budget) / 100 * 3.67  # Convert to AED
                    print(f"   Daily Budget: AED {budget_aed:.2f}")
                print(f"   Created: {created}")
                print()
            
            print(f"SUMMARY: {active_count} Active, {paused_count} Paused")
            
            # Check if any campaigns need attention
            if active_count == 0:
                print("\n⚠️  ALERT: No active campaigns running!")
                print("All campaigns are paused - no leads will be generated.")
            elif active_count < 3:
                print(f"\n⚠️  Only {active_count} campaigns active - consider scaling up")
            else:
                print(f"\n✅ Good number of active campaigns ({active_count})")
                
        else:
            print("❌ No campaign data found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_campaign_details()