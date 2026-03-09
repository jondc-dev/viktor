#!/usr/bin/env python3
import csv
import sys

# Read the CSV file with tab separator
with open('leads_export.csv', 'r', encoding='utf-8') as f:
    # Read all lines
    lines = f.readlines()
    
# Parse the header
header = lines[0].strip().split('\t')
print(f"Header has {len(header)} fields: {header}")

# Find indices of key fields
try:
    lead_stage_idx = header.index('LEAD STAGE')
except ValueError:
    # Try to find it by partial match
    for i, field in enumerate(header):
        if 'STAGE' in field.upper():
            lead_stage_idx = i
            break
    else:
        lead_stage_idx = None

try:
    amount_idx = header.index('AMOUNT')
except ValueError:
    amount_idx = None

try:
    created_at_idx = header.index('CREATED AT')
except ValueError:
    created_at_idx = None

print(f"\nKey field indices: LEAD STAGE={lead_stage_idx}, AMOUNT={amount_idx}, CREATED AT={created_at_idx}")

# Parse data rows
leads_waiting_approval = []
total_quoted_amount = 0
march_1_6_leads = 0

for i, line in enumerate(lines[1:], 1):  # Skip header
    row = line.strip().split('\t')
    
    # Skip empty rows
    if not row or len(row) < 5:
        continue
    
    # Try to find lead stage - it might be in different positions
    lead_stage = None
    amount = None
    created_at = None
    
    # Look for "Quotation - waiting for approval" in any field
    for j, field in enumerate(row):
        if 'Quotation - waiting for approval' in field:
            lead_stage = field
            # Check if next field might be amount
            if j + 1 < len(row) and row[j+1].replace('.', '').isdigit():
                amount = row[j+1]
            break
    
    # If not found that way, try using indices
    if not lead_stage and lead_stage_idx is not None and lead_stage_idx < len(row):
        lead_stage = row[lead_stage_idx]
    
    # Get amount
    if amount_idx is not None and amount_idx < len(row):
        amount_val = row[amount_idx]
        if amount_val and amount_val.replace('.', '').isdigit():
            amount = amount_val
    
    # Get created date
    if created_at_idx is not None and created_at_idx < len(row):
        created_at = row[created_at_idx]
    else:
        # Try to find date in last few fields
        for field in row[-3:]:
            if field and '2026-03-' in field:
                created_at = field
                break
    
    # Check if this is a "Quotation - waiting for approval" lead
    if lead_stage and 'Quotation - waiting for approval' in lead_stage:
        lead_info = {
            'row': i,
            'lead_stage': lead_stage,
            'amount': amount,
            'created_at': created_at,
            'raw_row': row
        }
        leads_waiting_approval.append(lead_info)
        
        # Check if date is March 1-6, 2026
        if created_at and '2026-03-' in created_at:
            try:
                day = int(created_at.split('-')[2])
                if 1 <= day <= 6:
                    march_1_6_leads += 1
                    if amount:
                        try:
                            total_quoted_amount += float(amount)
                        except ValueError:
                            pass
            except (IndexError, ValueError):
                pass

print(f"\nFound {len(leads_waiting_approval)} leads with 'Quotation - waiting for approval' status")
print(f"Out of these, {march_1_6_leads} are from March 1-6, 2026")
print(f"Total quoted amount for March 1-6 leads: {total_quoted_amount}")

print("\nDetailed breakdown of leads waiting for approval:")
for lead in leads_waiting_approval:
    print(f"Row {lead['row']}: Date={lead['created_at']}, Amount={lead['amount']}")

# Also try a different approach: look for amounts in any field for these leads
print("\n\nAlternative analysis: Looking for any numeric values in 'waiting for approval' rows...")
for i, line in enumerate(lines[1:], 1):
    row = line.strip().split('\t')
    
    # Check if this row has "waiting for approval" in any field
    has_waiting_approval = False
    for field in row:
        if 'waiting for approval' in field.lower():
            has_waiting_approval = True
            break
    
    if has_waiting_approval:
        # Look for any numeric values in this row
        amounts = []
        for field in row:
            if field and field.replace('.', '').isdigit():
                amounts.append(field)
        
        if amounts:
            print(f"Row {i} has 'waiting for approval' and numeric values: {amounts}")
        else:
            print(f"Row {i} has 'waiting for approval' but no numeric values")