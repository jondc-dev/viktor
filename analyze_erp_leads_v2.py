#!/usr/bin/env python3
import csv
import re

def parse_erp_data(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    header = lines[0].strip().split('\t')
    print(f"Header ({len(header)} fields): {header}")
    
    # Based on inspection, the data seems misaligned.
    # Let's try to intelligently parse each row
    leads = []
    
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        if not line:
            continue
            
        fields = line.split('\t')
        
        # Basic lead info - first few fields are usually consistent
        lead_id = fields[0] if len(fields) > 0 else ''
        name = fields[1] if len(fields) > 1 else ''
        
        # Try to find the status
        status = None
        amount = None
        date = None
        
        # Look for status patterns
        for j, field in enumerate(fields):
            if not field:
                continue
                
            # Check for status indicators
            if 'Quotation - waiting for approval' in field:
                status = 'Quotation - waiting for approval'
                # Check nearby fields for amount
                for k in range(max(0, j-3), min(len(fields), j+4)):
                    if k != j and fields[k] and re.match(r'^\d+\.?\d*$', fields[k].strip()):
                        # Make sure it's not a phone number (too long)
                        if len(fields[k].strip()) < 10:  # Amounts are usually short
                            amount = fields[k].strip()
                            break
                break
            elif 'Service scheduled' in field:
                status = 'Service scheduled'
                # For service scheduled, amount is often in a specific position
                if j + 2 < len(fields) and fields[j+2] and re.match(r'^\d+\.?\d*$', fields[j+2].strip()):
                    amount = fields[j+2].strip()
                break
        
        # Try to find date (looking for 2026-03 pattern)
        for field in fields:
            if field and '2026-03-' in field:
                date = field
                break
        
        # If no date found in fields, check the end of the row
        if not date and fields:
            # Check last few fields
            for field in fields[-3:]:
                if field and '2026-03-' in field:
                    date = field
                    break
        
        leads.append({
            'row': i,
            'lead_id': lead_id,
            'name': name,
            'status': status,
            'amount': amount,
            'date': date,
            'raw_fields': fields
        })
    
    return leads

def analyze_leads(leads):
    # Filter for 'Quotation - waiting for approval'
    waiting_approval = [l for l in leads if l['status'] == 'Quotation - waiting for approval']
    
    print(f"\nTotal leads: {len(leads)}")
    print(f"Leads with 'Quotation - waiting for approval': {len(waiting_approval)}")
    
    # Filter for March 1-6
    march_1_6_leads = []
    for lead in waiting_approval:
        if lead['date'] and lead['date'].startswith('2026-03-'):
            try:
                day = int(lead['date'].split('-')[2])
                if 1 <= day <= 6:
                    march_1_6_leads.append(lead)
            except (IndexError, ValueError):
                pass
    
    print(f"Leads from March 1-6, 2026: {len(march_1_6_leads)}")
    
    # Calculate total amount
    total_amount = 0
    leads_with_amount = 0
    
    for lead in march_1_6_leads:
        if lead['amount']:
            try:
                total_amount += float(lead['amount'])
                leads_with_amount += 1
            except ValueError:
                pass
    
    print(f"\nLeads with amount data: {leads_with_amount}/{len(march_1_6_leads)}")
    print(f"Total quoted amount: {total_amount}")
    
    # Display details
    print("\nDetailed breakdown:")
    for lead in march_1_6_leads:
        print(f"Row {lead['row']}: ID={lead['lead_id']}, Name={lead['name']}, Date={lead['date']}, Amount={lead['amount']}")
    
    # Also check all leads to see if any have amounts
    print("\n\nChecking all leads for amounts (not just waiting for approval):")
    all_amounts = []
    for lead in leads:
        if lead['amount']:
            all_amounts.append((lead['row'], lead['status'], lead['amount'], lead['date']))
    
    if all_amounts:
        print("Leads with amount values:")
        for row, status, amount, date in all_amounts:
            print(f"Row {row}: Status={status}, Amount={amount}, Date={date}")
    else:
        print("No leads have amount values in the data")

if __name__ == '__main__':
    leads = parse_erp_data('leads_export.csv')
    analyze_leads(leads)