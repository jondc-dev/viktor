#!/usr/bin/env python3
"""
Headless Browser Tool for Viktor
Playwright-based web automation without requiring OpenClaw browser extension.

Created: 2026-02-18
Replaces Chrome extension dependency with autonomous headless browser.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required dependencies not installed.", file=sys.stderr)
    print("Run: scripts/setup_browser.sh", file=sys.stderr)
    sys.exit(1)

# Configuration
BROWSER_PROFILES_DIR = Path.home() / ".viktor" / "browser-profiles"
SESSIONS_FILE = Path.home() / ".viktor" / "browser-sessions.json"
DEFAULT_TIMEOUT = 30000  # 30 seconds for navigation
SELECTOR_TIMEOUT = 10000  # 10 seconds for selectors
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

# Ensure directories exist
BROWSER_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)


class BrowserSession:
    """Manages persistent browser sessions."""
    
    def __init__(self):
        self.sessions = self._load_sessions()
    
    def _load_sessions(self) -> Dict:
        """Load sessions from file."""
        if SESSIONS_FILE.exists():
            try:
                return json.loads(SESSIONS_FILE.read_text())
            except Exception:
                return {}
        return {}
    
    def _save_sessions(self):
        """Save sessions to file."""
        SESSIONS_FILE.write_text(json.dumps(self.sessions, indent=2))
    
    def start(self, profile: str = "default") -> str:
        """Start a new session."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.sessions[session_id] = {
            "profile": profile,
            "started": datetime.now().isoformat(),
            "url": "about:blank"
        }
        self._save_sessions()
        return session_id
    
    def list(self) -> List[Dict]:
        """List all active sessions."""
        return [{"id": sid, **data} for sid, data in self.sessions.items()]
    
    def stop(self, session_id: str) -> bool:
        """Stop a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False
    
    def get(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        return self.sessions.get(session_id)
    
    def update_url(self, session_id: str, url: str):
        """Update session URL."""
        if session_id in self.sessions:
            self.sessions[session_id]["url"] = url
            self._save_sessions()


class BrowserTool:
    """Main browser automation tool."""
    
    def __init__(self, headed: bool = False, json_output: bool = False):
        self.headed = headed
        self.json_output = json_output
        self.session_manager = BrowserSession()
    
    def _output(self, data: Any):
        """Output data in requested format."""
        if self.json_output:
            print(json.dumps(data, indent=2))
        else:
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"{key}: {value}")
            elif isinstance(data, list):
                for item in data:
                    print(item)
            else:
                print(data)
    
    def _clean_text(self, html: str, raw: bool = False) -> str:
        """Convert HTML to clean text."""
        if raw:
            return html
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _get_profile_dir(self, profile: str) -> Path:
        """Get profile directory path."""
        return BROWSER_PROFILES_DIR / profile
    
    def _launch_browser(self, profile: Optional[str] = None) -> tuple[Browser, BrowserContext, Page]:
        """Launch browser with optional profile."""
        playwright = sync_playwright().start()
        
        if profile:
            profile_dir = self._get_profile_dir(profile)
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            context = playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=not self.headed,
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.pages[0] if context.pages else context.new_page()
            return None, context, page
        else:
            browser = playwright.chromium.launch(headless=not self.headed)
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            return browser, context, page
    
    def navigate(self, url: str, raw: bool = False) -> Dict:
        """Navigate to URL and return page content."""
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            title = page.title()
            content = page.content()
            text = self._clean_text(content, raw)
            
            result = {
                "url": url,
                "title": title,
                "content": text if not raw else content
            }
            
            self._output(result)
            return result
            
        except PlaywrightTimeout:
            error = {"error": f"Timeout navigating to {url}"}
            self._output(error)
            return error
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def search(self, query: str) -> Dict:
        """Perform Google search and return results."""
        browser, context, page = self._launch_browser()
        
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            page.goto(search_url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            
            # Extract search results
            results = []
            
            # Try to find search result elements
            search_results = page.query_selector_all('div.g')
            
            for result in search_results[:10]:  # Top 10 results
                try:
                    title_elem = result.query_selector('h3')
                    link_elem = result.query_selector('a')
                    snippet_elem = result.query_selector('div[data-sncf], div.VwiC3b')
                    
                    if title_elem and link_elem:
                        title = title_elem.inner_text()
                        url = link_elem.get_attribute('href')
                        snippet = snippet_elem.inner_text() if snippet_elem else ""
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                except Exception:
                    continue
            
            output = {
                "query": query,
                "results": results
            }
            
            self._output(output)
            return output
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def screenshot(self, url: str, output_path: Optional[str] = None) -> Dict:
        """Take screenshot of URL."""
        if not output_path:
            output_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.screenshot(path=output_path, full_page=True)
            
            result = {
                "url": url,
                "screenshot": output_path
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def click(self, url: str, selector: str) -> Dict:
        """Click element on page."""
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.click(selector, timeout=SELECTOR_TIMEOUT)
            
            # Wait for any navigation or changes
            page.wait_for_timeout(1000)
            
            result = {
                "url": url,
                "selector": selector,
                "status": "clicked"
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def fill(self, url: str, selector: str, value: str) -> Dict:
        """Fill form field on page."""
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.fill(selector, value, timeout=SELECTOR_TIMEOUT)
            
            result = {
                "url": url,
                "selector": selector,
                "status": "filled"
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def extract(self, url: str, selector: Optional[str] = None, raw: bool = False) -> Dict:
        """Extract text content from page or element."""
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            
            if selector:
                element = page.query_selector(selector)
                if element:
                    content = element.inner_html()
                else:
                    return {"error": f"Selector '{selector}' not found"}
            else:
                content = page.content()
            
            text = self._clean_text(content, raw)
            
            result = {
                "url": url,
                "selector": selector or "full_page",
                "content": text
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def pdf(self, url: str, output_path: Optional[str] = None) -> Dict:
        """Save page as PDF."""
        if not output_path:
            output_path = f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.pdf(path=output_path)
            
            result = {
                "url": url,
                "pdf": output_path
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def execute(self, url: str, js_code: str) -> Dict:
        """Execute JavaScript on page and return result."""
        browser, context, page = self._launch_browser()
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            result_value = page.evaluate(js_code)
            
            result = {
                "url": url,
                "result": result_value
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    # Session commands
    
    def session_start(self, profile: str = "default") -> Dict:
        """Start a persistent browser session."""
        session_id = self.session_manager.start(profile)
        
        result = {
            "session_id": session_id,
            "profile": profile,
            "status": "started"
        }
        
        self._output(result)
        return result
    
    def session_list(self) -> Dict:
        """List active sessions."""
        sessions = self.session_manager.list()
        
        result = {
            "sessions": sessions
        }
        
        self._output(result)
        return result
    
    def session_stop(self, session_id: str) -> Dict:
        """Stop a session."""
        success = self.session_manager.stop(session_id)
        
        result = {
            "session_id": session_id,
            "status": "stopped" if success else "not_found"
        }
        
        self._output(result)
        return result
    
    def session_navigate(self, session_id: str, url: str, raw: bool = False) -> Dict:
        """Navigate within a session."""
        session = self.session_manager.get(session_id)
        if not session:
            error = {"error": f"Session '{session_id}' not found"}
            self._output(error)
            return error
        
        browser, context, page = self._launch_browser(profile=session['profile'])
        
        try:
            page.goto(url, timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            title = page.title()
            content = page.content()
            text = self._clean_text(content, raw)
            
            self.session_manager.update_url(session_id, url)
            
            result = {
                "session_id": session_id,
                "url": url,
                "title": title,
                "content": text if not raw else content
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def session_click(self, session_id: str, selector: str) -> Dict:
        """Click within a session."""
        session = self.session_manager.get(session_id)
        if not session:
            error = {"error": f"Session '{session_id}' not found"}
            self._output(error)
            return error
        
        browser, context, page = self._launch_browser(profile=session['profile'])
        
        try:
            page.goto(session['url'], timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.click(selector, timeout=SELECTOR_TIMEOUT)
            page.wait_for_timeout(1000)
            
            new_url = page.url
            self.session_manager.update_url(session_id, new_url)
            
            result = {
                "session_id": session_id,
                "selector": selector,
                "status": "clicked",
                "url": new_url
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def session_fill(self, session_id: str, selector: str, value: str) -> Dict:
        """Fill form field within a session."""
        session = self.session_manager.get(session_id)
        if not session:
            error = {"error": f"Session '{session_id}' not found"}
            self._output(error)
            return error
        
        browser, context, page = self._launch_browser(profile=session['profile'])
        
        try:
            page.goto(session['url'], timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.fill(selector, value, timeout=SELECTOR_TIMEOUT)
            
            result = {
                "session_id": session_id,
                "selector": selector,
                "status": "filled"
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()
    
    def session_screenshot(self, session_id: str, output_path: Optional[str] = None) -> Dict:
        """Take screenshot within a session."""
        session = self.session_manager.get(session_id)
        if not session:
            error = {"error": f"Session '{session_id}' not found"}
            self._output(error)
            return error
        
        if not output_path:
            output_path = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        browser, context, page = self._launch_browser(profile=session['profile'])
        
        try:
            page.goto(session['url'], timeout=DEFAULT_TIMEOUT, wait_until='networkidle')
            page.screenshot(path=output_path, full_page=True)
            
            result = {
                "session_id": session_id,
                "screenshot": output_path,
                "url": session['url']
            }
            
            self._output(result)
            return result
            
        except Exception as e:
            error = {"error": str(e)}
            self._output(error)
            return error
        finally:
            if browser:
                browser.close()
            else:
                context.close()


def main():
    """CLI interface for browser tool."""
    parser = argparse.ArgumentParser(description="Headless Browser Tool for Viktor")
    parser.add_argument('--headed', action='store_true', help='Run browser in headed mode (visible)')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Navigate
    nav_parser = subparsers.add_parser('navigate', help='Navigate to URL')
    nav_parser.add_argument('url', help='URL to navigate to')
    nav_parser.add_argument('--raw', action='store_true', help='Return raw HTML instead of clean text')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Google search')
    search_parser.add_argument('query', help='Search query')
    
    # Screenshot
    screenshot_parser = subparsers.add_parser('screenshot', help='Take screenshot')
    screenshot_parser.add_argument('url', help='URL to screenshot')
    screenshot_parser.add_argument('--output', help='Output file path')
    
    # Click
    click_parser = subparsers.add_parser('click', help='Click element')
    click_parser.add_argument('url', help='URL')
    click_parser.add_argument('selector', help='CSS selector')
    
    # Fill
    fill_parser = subparsers.add_parser('fill', help='Fill form field')
    fill_parser.add_argument('url', help='URL')
    fill_parser.add_argument('selector', help='CSS selector')
    fill_parser.add_argument('value', help='Value to fill')
    
    # Extract
    extract_parser = subparsers.add_parser('extract', help='Extract text content')
    extract_parser.add_argument('url', help='URL')
    extract_parser.add_argument('--selector', help='CSS selector (optional)')
    extract_parser.add_argument('--raw', action='store_true', help='Return raw HTML')
    
    # PDF
    pdf_parser = subparsers.add_parser('pdf', help='Save as PDF')
    pdf_parser.add_argument('url', help='URL')
    pdf_parser.add_argument('--output', help='Output file path')
    
    # Execute
    execute_parser = subparsers.add_parser('execute', help='Execute JavaScript')
    execute_parser.add_argument('url', help='URL')
    execute_parser.add_argument('js_code', help='JavaScript code to execute')
    
    # Session commands
    session_parser = subparsers.add_parser('session', help='Session management')
    session_subparsers = session_parser.add_subparsers(dest='session_command', help='Session commands')
    
    # Session start
    session_start_parser = session_subparsers.add_parser('start', help='Start session')
    session_start_parser.add_argument('--profile', default='default', help='Profile name')
    
    # Session list
    session_subparsers.add_parser('list', help='List sessions')
    
    # Session stop
    session_stop_parser = session_subparsers.add_parser('stop', help='Stop session')
    session_stop_parser.add_argument('id', help='Session ID')
    
    # Session navigate
    session_nav_parser = session_subparsers.add_parser('navigate', help='Navigate in session')
    session_nav_parser.add_argument('id', help='Session ID')
    session_nav_parser.add_argument('url', help='URL')
    session_nav_parser.add_argument('--raw', action='store_true', help='Return raw HTML')
    
    # Session click
    session_click_parser = session_subparsers.add_parser('click', help='Click in session')
    session_click_parser.add_argument('id', help='Session ID')
    session_click_parser.add_argument('selector', help='CSS selector')
    
    # Session fill
    session_fill_parser = session_subparsers.add_parser('fill', help='Fill in session')
    session_fill_parser.add_argument('id', help='Session ID')
    session_fill_parser.add_argument('selector', help='CSS selector')
    session_fill_parser.add_argument('value', help='Value to fill')
    
    # Session screenshot
    session_screenshot_parser = session_subparsers.add_parser('screenshot', help='Screenshot session')
    session_screenshot_parser.add_argument('id', help='Session ID')
    session_screenshot_parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize tool
    tool = BrowserTool(headed=args.headed, json_output=args.json)
    
    try:
        if args.command == 'navigate':
            tool.navigate(args.url, raw=args.raw)
        
        elif args.command == 'search':
            tool.search(args.query)
        
        elif args.command == 'screenshot':
            tool.screenshot(args.url, output_path=args.output)
        
        elif args.command == 'click':
            tool.click(args.url, args.selector)
        
        elif args.command == 'fill':
            tool.fill(args.url, args.selector, args.value)
        
        elif args.command == 'extract':
            tool.extract(args.url, selector=args.selector, raw=args.raw)
        
        elif args.command == 'pdf':
            tool.pdf(args.url, output_path=args.output)
        
        elif args.command == 'execute':
            tool.execute(args.url, args.js_code)
        
        elif args.command == 'session':
            if not args.session_command:
                session_parser.print_help()
                sys.exit(1)
            
            if args.session_command == 'start':
                tool.session_start(profile=args.profile)
            
            elif args.session_command == 'list':
                tool.session_list()
            
            elif args.session_command == 'stop':
                tool.session_stop(args.id)
            
            elif args.session_command == 'navigate':
                tool.session_navigate(args.id, args.url, raw=args.raw)
            
            elif args.session_command == 'click':
                tool.session_click(args.id, args.selector)
            
            elif args.session_command == 'fill':
                tool.session_fill(args.id, args.selector, args.value)
            
            elif args.session_command == 'screenshot':
                tool.session_screenshot(args.id, output_path=args.output)
    
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
