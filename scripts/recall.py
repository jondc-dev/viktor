#!/usr/bin/env python3
"""
Multi-Source FAISS Recall Script for Viktor
Quick recall across all FAISS memories with source filtering.
"""

import sys
import json
from pathlib import Path

# Add vector-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "vector-memory"))

from memory_store import VectorMemory


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Search Viktor\'s FAISS vector memory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  recall.py "María Elena"                    # Search all memories
  recall.py --backstory "Father Miguel"      # Search only backstory
  recall.py --daily "email configuration"    # Search only daily archives
  recall.py --memory "ISO certification"     # Search only memory archives
  recall.py --json "Messi" > results.json    # JSON output
        '''
    )
    
    parser.add_argument('query', help='Search query')
    parser.add_argument('--backstory', action='store_true', help='Search only backstory chunks')
    parser.add_argument('--daily', action='store_true', help='Search only daily memory archives')
    parser.add_argument('--memory', action='store_true', help='Search only MEMORY.md archives')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('-k', '--top-k', type=int, default=10, help='Number of results to return (default: 10)')
    parser.add_argument('--min-score', type=float, default=0.3, help='Minimum similarity score (default: 0.3)')
    
    args = parser.parse_args()
    
    # Load vector memory
    vm = VectorMemory()
    
    if vm.index.ntotal == 0:
        print("No memories in FAISS index yet.", file=sys.stderr)
        sys.exit(1)
    
    # Perform search
    results = vm.search(args.query, k=args.top_k, min_score=args.min_score)
    
    if not results:
        if not args.json:
            print(f"No results found for query: {args.query}")
        else:
            print(json.dumps({"query": args.query, "results": []}))
        return
    
    # Filter by source if requested
    if args.backstory:
        results = [r for r in results if r['source'].startswith('backstory:')]
    elif args.daily:
        results = [r for r in results if r['source'].startswith('daily_memory:')]
    elif args.memory:
        results = [r for r in results if r['source'].startswith('memory_archive:')]
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Output
    if args.json:
        output = {
            "query": args.query,
            "filter": "backstory" if args.backstory else "daily" if args.daily else "memory" if args.memory else "all",
            "count": len(results),
            "results": results
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        filter_type = "backstory" if args.backstory else "daily archives" if args.daily else "memory archives" if args.memory else "all memories"
        print(f"Search: '{args.query}' in {filter_type}")
        print(f"Found {len(results)} results (min_score={args.min_score})")
        print("="*60)
        
        for i, result in enumerate(results, 1):
            score = result['score']
            source = result['source']
            timestamp = result['timestamp'][:10]  # Just the date
            text = result['text']
            
            # Truncate text for display
            if len(text) > 300:
                text = text[:300] + "..."
            
            print(f"\n[{i}] Score: {score:.3f} | Source: {source} | Date: {timestamp}")
            print("-" * 60)
            print(text)
        
        print("\n" + "="*60)
        print(f"Showing top {len(results)} of {vm.index.ntotal} total memories")


if __name__ == "__main__":
    main()
