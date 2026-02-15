#!/usr/bin/env python3
"""
Memory Rotation Script for Viktor
Rotates MEMORY.md keeping permanent sections + last 14 days of dated entries.
Archives older sections to FAISS + disk backup at memory/archive/.
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add vector-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "vector-memory"))

from memory_store import VectorMemory


# Permanent sections (keywords to identify sections that should never be archived)
PERMANENT_KEYWORDS = [
    "Who I Am",
    "Key People",
    "My Contact Info",
    "Communication Preferences",
    "Company Info",
    "ISO Certifications",
    "JV de Castro",
    "Thomas",
    "Franz",
    "Frontdesk Team",
    "Spatial Memory",
]


def parse_memory_file(content: str) -> dict:
    """
    Parse MEMORY.md into sections.
    Returns dict with 'permanent', 'dated_entries', 'other'
    """
    sections = {
        'permanent': [],
        'dated_entries': [],
        'other': []
    }
    
    # Split by markdown headers (## or ###)
    lines = content.split('\n')
    current_section = []
    current_header = None
    
    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            # Save previous section
            if current_section:
                section_text = '\n'.join(current_section).strip()
                categorize_section(section_text, current_header, sections)
            
            # Start new section
            current_header = line
            current_section = [line]
        else:
            current_section.append(line)
    
    # Save last section
    if current_section:
        section_text = '\n'.join(current_section).strip()
        categorize_section(section_text, current_header, sections)
    
    return sections


def categorize_section(text: str, header: str, sections: dict):
    """Categorize a section as permanent, dated, or other"""
    if not text:
        return
    
    # Check if it's a permanent section
    if header:
        for keyword in PERMANENT_KEYWORDS:
            if keyword.lower() in header.lower():
                sections['permanent'].append(text)
                return
    
    # Check if it's a dated entry (## YYYY-MM-DD or ### YYYY-MM-DD)
    if header:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', header)
        if date_match:
            date_str = date_match.group(1)
            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d')
                sections['dated_entries'].append({
                    'date': entry_date,
                    'text': text
                })
                return
            except ValueError:
                pass
    
    # Otherwise, it's "other"
    sections['other'].append(text)


def filter_dated_entries(dated_entries: list, cutoff_days: int = 14) -> tuple:
    """
    Split dated entries into recent (keep) and old (archive).
    Returns (recent_entries, old_entries)
    """
    cutoff_date = datetime.now() - timedelta(days=cutoff_days)
    
    recent = []
    old = []
    
    for entry in dated_entries:
        if entry['date'] >= cutoff_date:
            recent.append(entry)
        else:
            old.append(entry)
    
    # Sort by date
    recent.sort(key=lambda x: x['date'])
    old.sort(key=lambda x: x['date'])
    
    return recent, old


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Rotate MEMORY.md, archiving old entries to FAISS')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--days', type=int, default=14, help='Keep entries from last N days (default: 14)')
    args = parser.parse_args()
    
    # Paths
    memory_path = Path(__file__).parent.parent / "MEMORY.md"
    archive_dir = Path(__file__).parent.parent / "memory" / "archive"
    
    if not memory_path.exists():
        print(f"Error: MEMORY.md not found at {memory_path}")
        sys.exit(1)
    
    # Create archive directory if needed
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading {memory_path}")
    with open(memory_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse memory file
    print("Parsing memory sections...")
    sections = parse_memory_file(content)
    
    print(f"  Permanent sections: {len(sections['permanent'])}")
    print(f"  Dated entries: {len(sections['dated_entries'])}")
    print(f"  Other sections: {len(sections['other'])}")
    
    # Filter dated entries
    recent_entries, old_entries = filter_dated_entries(sections['dated_entries'], args.days)
    
    print(f"\nFiltering with cutoff of {args.days} days:")
    print(f"  Recent entries (keep): {len(recent_entries)}")
    print(f"  Old entries (archive): {len(old_entries)}")
    
    if not old_entries:
        print("\nNo old entries to archive. MEMORY.md is up to date.")
        return
    
    # Build new MEMORY.md content
    new_content_parts = []
    
    # Add permanent sections
    for section in sections['permanent']:
        new_content_parts.append(section)
        new_content_parts.append('')  # blank line
    
    # Add other sections
    for section in sections['other']:
        new_content_parts.append(section)
        new_content_parts.append('')
    
    # Add recent dated entries
    for entry in recent_entries:
        new_content_parts.append(entry['text'])
        new_content_parts.append('')
    
    new_content = '\n'.join(new_content_parts).strip() + '\n'
    
    # Build archive content
    archive_parts = []
    for entry in old_entries:
        archive_parts.append(entry['text'])
        archive_parts.append('')
    
    archive_content = '\n'.join(archive_parts).strip() + '\n'
    
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes made")
        print("="*60)
        print(f"\nWould archive {len(old_entries)} old entries:")
        for entry in old_entries[:5]:  # Show first 5
            date_str = entry['date'].strftime('%Y-%m-%d')
            preview = entry['text'][:100].replace('\n', ' ')
            print(f"  [{date_str}] {preview}...")
        if len(old_entries) > 5:
            print(f"  ... and {len(old_entries) - 5} more")
        
        print(f"\nNew MEMORY.md would be {len(new_content)} bytes (currently {len(content)} bytes)")
        print(f"Archive content: {len(archive_content)} bytes")
        return
    
    # Archive to FAISS
    print("\nArchiving to FAISS...")
    vm = VectorMemory()
    source = "memory_archive:MEMORY.md"
    
    for entry in old_entries:
        if vm.add(entry['text'], source=source):
            date_str = entry['date'].strftime('%Y-%m-%d')
            print(f"  ✓ Archived entry from {date_str}")
    
    # Save archive to disk
    timestamp = datetime.now().strftime('%Y-%m-%d')
    archive_file = archive_dir / f"memory_archive_{timestamp}.md"
    
    print(f"\nSaving disk backup to {archive_file}")
    with open(archive_file, 'w', encoding='utf-8') as f:
        f.write(f"# Memory Archive - {timestamp}\n\n")
        f.write(f"Archived {len(old_entries)} entries from MEMORY.md\n\n")
        f.write("---\n\n")
        f.write(archive_content)
    
    # Write new MEMORY.md
    print(f"Writing new MEMORY.md ({len(new_content)} bytes)")
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("\n" + "="*60)
    print("Memory Rotation Complete")
    print("="*60)
    print(f"Archived {len(old_entries)} old entries")
    print(f"Kept {len(recent_entries)} recent entries")
    print(f"Kept {len(sections['permanent'])} permanent sections")
    print(f"FAISS source tag: {source}")
    print(f"Disk backup: {archive_file}")


if __name__ == "__main__":
    main()
