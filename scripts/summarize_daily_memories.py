#!/usr/bin/env python3
"""
Daily Memory Summarization Script for Viktor
Summarizes daily memory files older than 3 days using rule-based approach.
Archives full text to FAISS + disk before summarizing.
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

# Add vector-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "vector-memory"))

from memory_store import VectorMemory


# Technical keywords that should always be kept
TECHNICAL_KEYWORDS = [
    'api', 'key', 'config', 'password', 'url', 'token', 
    'secret', 'port', 'host', 'endpoint', 'credential',
    'cert', 'ssl', 'auth', 'database', 'server', 'ip'
]


def is_summarized(content: str) -> bool:
    """Check if file is already summarized"""
    return "Full version archived to FAISS" in content or "Summarized on" in content


def should_keep_line(line: str) -> bool:
    """
    Rule-based filter: return True if line should be kept in summary.
    
    KEEPS:
    - Markdown headers (# ## ###)
    - Bold key-value lines (- **Key:** value)
    - Status items (✅ 🔴 ⚠️)
    - Table rows (|)
    - Blockquotes (>)
    - Lines with technical keywords
    - Horizontal rules (---)
    
    DROPS:
    - Regular prose paragraphs
    """
    stripped = line.strip()
    
    # Empty lines - keep
    if not stripped:
        return True
    
    # Headers - keep
    if stripped.startswith('#'):
        return True
    
    # Horizontal rules - keep
    if stripped.startswith('---') or stripped.startswith('==='):
        return True
    
    # List items with bold (- **Key:** value) - keep
    if stripped.startswith('- **') or stripped.startswith('* **'):
        return True
    
    # Status indicators - keep
    if any(emoji in stripped for emoji in ['✅', '🔴', '⚠️', '📌', '🚀', '⏰', '💡']):
        return True
    
    # Table rows - keep
    if '|' in stripped and stripped.count('|') >= 2:
        return True
    
    # Blockquotes - keep
    if stripped.startswith('>'):
        return True
    
    # Lines with technical keywords - keep
    lower = stripped.lower()
    if any(keyword in lower for keyword in TECHNICAL_KEYWORDS):
        return True
    
    # List items (but not bold ones) - drop
    if stripped.startswith('- ') or stripped.startswith('* '):
        # Only keep if it has status emoji or technical content
        if any(emoji in stripped for emoji in ['✅', '🔴', '⚠️']):
            return True
        if any(keyword in lower for keyword in TECHNICAL_KEYWORDS):
            return True
        return False
    
    # Regular paragraphs - drop
    # (If we get here, it's likely prose text)
    return False


def summarize_content(content: str, filename: str) -> str:
    """Apply rule-based summarization"""
    lines = content.split('\n')
    kept_lines = []
    
    for line in lines:
        if should_keep_line(line):
            kept_lines.append(line)
    
    # Build summary
    summary_parts = [
        f"> Full version archived to FAISS + memory/archive/{filename}",
        "",
        "---",
        "",
    ]
    
    summary_parts.extend(kept_lines)
    
    return '\n'.join(summary_parts)


def get_daily_files(memory_dir: Path, days_threshold: int = 3) -> list:
    """
    Get list of daily memory files older than N days.
    Returns list of (path, date) tuples.
    """
    cutoff_date = datetime.now() - timedelta(days=days_threshold)
    daily_files = []
    
    # Pattern: YYYY-MM-DD.md
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})\.md$')
    
    for file in memory_dir.glob('*.md'):
        match = date_pattern.match(file.name)
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                if file_date < cutoff_date:
                    daily_files.append((file, file_date))
            except ValueError:
                continue
    
    return sorted(daily_files, key=lambda x: x[1])


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Summarize daily memory files older than 3 days')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--days', type=int, default=3, help='Summarize files older than N days (default: 3)')
    parser.add_argument('--min-size', type=int, default=500, help='Skip files smaller than N bytes (default: 500)')
    args = parser.parse_args()
    
    # Paths
    memory_dir = Path(__file__).parent.parent / "memory"
    archive_dir = memory_dir / "archive"
    
    if not memory_dir.exists():
        print(f"Error: Memory directory not found at {memory_dir}")
        sys.exit(1)
    
    # Create archive directory
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Scanning for daily memory files older than {args.days} days...")
    daily_files = get_daily_files(memory_dir, args.days)
    
    if not daily_files:
        print("No files to summarize.")
        return
    
    print(f"Found {len(daily_files)} candidate files")
    
    # Initialize FAISS
    vm = None
    if not args.dry_run:
        print("Loading FAISS vector memory...")
        vm = VectorMemory()
    
    # Process each file
    summarized_count = 0
    skipped_count = 0
    
    for file_path, file_date in daily_files:
        date_str = file_date.strftime('%Y-%m-%d')
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = len(content)
        
        # Skip if too small
        if file_size < args.min_size:
            print(f"  ⊘ {date_str} - too small ({file_size} bytes), skipping")
            skipped_count += 1
            continue
        
        # Skip if already summarized
        if is_summarized(content):
            print(f"  ⊘ {date_str} - already summarized, skipping")
            skipped_count += 1
            continue
        
        # Summarize
        summary = summarize_content(content, file_path.name)
        reduction = 100 * (1 - len(summary) / len(content))
        
        print(f"  → {date_str} - {file_size} bytes → {len(summary)} bytes ({reduction:.1f}% reduction)")
        
        if args.dry_run:
            continue
        
        # Archive to FAISS
        source = f"daily_memory:{date_str}"
        if vm.add(content, source=source):
            print(f"    ✓ Archived to FAISS (source: {source})")
        
        # Archive to disk
        archive_file = archive_dir / file_path.name
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    ✓ Backed up to {archive_file}")
        
        # Write summary back to original file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"    ✓ Replaced with summary")
        
        summarized_count += 1
    
    print("\n" + "="*60)
    if args.dry_run:
        print("DRY RUN - No changes made")
        print("="*60)
        print(f"Would summarize {summarized_count} files")
    else:
        print("Summarization Complete")
        print("="*60)
        print(f"Summarized: {summarized_count} files")
    print(f"Skipped: {skipped_count} files")


if __name__ == "__main__":
    main()
