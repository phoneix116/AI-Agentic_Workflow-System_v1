#!/usr/bin/env python3
"""
Email Widget Button Validation Tests
Tests all frontend buttons and their corresponding backend endpoints.
"""

import requests
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
DEMO_EMAIL = "demo.user@local.dev"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class EmailWidgetTester:
    """Tests email widget functionality"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[Dict] = []
        self.auth_token: Optional[str] = None
        self.test_email_id: Optional[str] = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log with color coding"""
        colors = {
            "INFO": BLUE,
            "SUCCESS": GREEN,
            "FAILED": RED,
            "WARNING": YELLOW,
        }
        color = colors.get(level, RESET)
        prefix = f"{BOLD}[{level}]{RESET}"
        print(f"{color}{prefix} {message}{RESET}")
    
    def get_dev_token(self) -> Optional[str]:
        """Get development token for testing"""
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/health/dev/token",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("data", {}).get("token")
                if token:
                    self.log(f"Dev token acquired for user: demo.user@local.dev", "SUCCESS")
                    return token
        except Exception as e:
            self.log(f"Failed to get dev token: {str(e)}", "WARNING")
        return None
    
    def test_result(self, test_name: str, passed: bool, details: str = ""):
        """Record and display test result"""
        if passed:
            self.passed += 1
            self.log(f"✓ {test_name}", "SUCCESS")
            if details:
                print(f"  {details}")
        else:
            self.failed += 1
            self.log(f"✗ {test_name}", "FAILED")
            if details:
                print(f"  {details}")
            self.errors.append({
                "test": test_name,
                "details": details,
            })
    
    def test_endpoint(
        self, 
        name: str, 
        method: str, 
        endpoint: str, 
        expected_status: int = 200,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Tuple[bool, Optional[dict], int]:
        """Test an API endpoint"""
        url = f"{BASE_URL}{endpoint}"
        try:
            if headers is None:
                headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                return False, None, 0
            
            status_ok = response.status_code == expected_status
            try:
                body = response.json()
            except:
                body = {"text": response.text}
            
            detail = f"Status: {response.status_code} (expected {expected_status})"
            self.test_result(
                name,
                status_ok,
                detail
            )
            
            return status_ok, body, response.status_code
            
        except Exception as e:
            self.test_result(name, False, f"Exception: {str(e)}")
            return False, None, 0
    
    def run_all_tests(self):
        """Run all email widget tests"""
        self.log("=" * 60, "INFO")
        self.log("Email Widget Button Validation", "INFO")
        self.log("=" * 60, "INFO")
        
        # Get auth token
        self.auth_token = self.get_dev_token()
        if not self.auth_token:
            self.log("WARNING: Could not obtain dev token - running unauthenticated tests", "WARNING")
        
        # Test 1: Check endpoint availability
        self.log("\n1. Checking Backend Endpoint Availability", "INFO")
        self._test_endpoints_available()
        
        # Test 2: Refresh button (GET /emails/list)
        self.log("\n2. Testing Refresh Button (GET /emails/list)", "INFO")
        self._test_refresh_endpoint()
        
        # Test 3: Urgent button (GET /emails/urgent)
        self.log("\n3. Testing Urgent Button (GET /emails/urgent)", "INFO")
        self._test_urgent_endpoint()
        
        # Test 4: Summary button (POST /emails/summarize)
        self.log("\n4. Testing Summary Button (POST /emails/summarize)", "INFO")
        self._test_summary_endpoint()
        
        # Test 5: Email action buttons
        self.log("\n5. Testing Email Action Buttons", "INFO")
        self._test_action_endpoints()
        
        # Test 6: Response validation
        self.log("\n6. Validating Response Formats", "INFO")
        self._test_response_formats()
        
        # Print summary
        self._print_summary()
    
    def _test_endpoints_available(self):
        """Check basic endpoint availability"""
        endpoints = [
            ("/emails/list", "GET", "Email list"),
            ("/emails/urgent", "GET", "Urgent emails"),
            ("/emails/summarize", "POST", "Email summary"),
            ("/emails/health", "GET", "Email service health"),
        ]
        
        for endpoint, method, desc in endpoints:
            passed, _, status = self.test_endpoint(
                f"Endpoint available: {desc}",
                method,
                endpoint,
            )
            # Status 401 is ok for unauthenticated endpoints
            if status in (200, 401):
                self.test_result(
                    f"Endpoint available: {desc}",
                    True,
                    f"Status: {status}"
                )
    
    def _test_refresh_endpoint(self):
        """Test refresh button endpoint"""
        passed, body, status = self.test_endpoint(
            "GET /emails/list (Refresh button)",
            "GET",
            "/emails/list?limit=8&offset=0",
            200,
        )
        
        if passed and body:
            # Validate response structure
            has_emails = "emails" in body
            has_count = "total_count" in body
            
            if has_emails and has_count:
                self.test_result(
                    "Refresh response format valid",
                    True,
                    f"Found {body.get('total_count', 0)} emails"
                )
                if isinstance(body.get("emails"), list) and len(body["emails"]) > 0:
                    self.test_email_id = body["emails"][0].get("id")
            else:
                self.test_result(
                    "Refresh response format valid",
                    False,
                    f"Missing fields: emails={has_emails}, total_count={has_count}"
                )
    
    def _test_urgent_endpoint(self):
        """Test urgent button endpoint"""
        passed, body, status = self.test_endpoint(
            "GET /emails/urgent (Urgent button)",
            "GET",
            "/emails/urgent",
            200,
        )
        
        if passed and body:
            # Validate response structure
            has_urgent = "urgent_emails" in body or "critical_emails" in body
            
            if has_urgent:
                count = len(body.get("urgent_emails", []))
                self.test_result(
                    "Urgent response format valid",
                    True,
                    f"Found {count} urgent emails"
                )
            else:
                self.test_result(
                    "Urgent response format valid",
                    False,
                    f"Response structure: {list(body.keys())}"
                )
    
    def _test_summary_endpoint(self):
        """Test summary button endpoint"""
        payload = {
            "limit": 10,
            "include_urgent_only": False,
        }
        
        passed, body, status = self.test_endpoint(
            "POST /emails/summarize (Summary button)",
            "POST",
            "/emails/summarize",
            200,
            payload,
        )
        
        if passed and body:
            # Validate response structure
            has_summary = "summary" in body
            
            if has_summary:
                summary = body.get("summary")
                has_text = "summary_text" in summary if isinstance(summary, dict) else False
                
                if has_text:
                    self.test_result(
                        "Summary response format valid",
                        True,
                        "Summary text generated"
                    )
                else:
                    self.test_result(
                        "Summary response format valid",
                        False,
                        f"Summary type: {type(summary)}"
                    )
            else:
                self.test_result(
                    "Summary response format valid",
                    False,
                    f"Response structure: {list(body.keys())}"
                )
    
    def _test_action_endpoints(self):
        """Test individual email action buttons"""
        if not self.test_email_id:
            self.log("No test email ID available - skipping action tests", "WARNING")
            return
        
        email_id = self.test_email_id
        
        # Test mark-as-read
        passed, _, _ = self.test_endpoint(
            f"POST /emails/{email_id}/mark-as-read (Mark as Read)",
            "POST",
            f"/emails/{email_id}/mark-as-read",
            200,
        )
        
        # Test archive
        passed, _, _ = self.test_endpoint(
            f"POST /emails/{email_id}/archive (Archive)",
            "POST",
            f"/emails/{email_id}/archive",
            200,
        )
        
        # Test delete
        passed, _, _ = self.test_endpoint(
            f"POST /emails/{email_id}/delete (Delete)",
            "POST",
            f"/emails/{email_id}/delete",
            200,
        )
        
        # Test snooze
        passed, _, _ = self.test_endpoint(
            f"POST /emails/{email_id}/snooze?hours=1 (Snooze)",
            "POST",
            f"/emails/{email_id}/snooze?hours=1",
            200,
        )
    
    def _test_response_formats(self):
        """Validate response format compliance"""
        self.log("Checking response formats...", "INFO")
        
        # Test list response format
        passed, body, _ = self.test_endpoint(
            "Validate list response format",
            "GET",
            "/emails/list?limit=1",
            200,
        )
        
        if passed and body and body.get("emails"):
            email = body["emails"][0]
            required_fields = ["id", "subject", "from_address", "timestamp", "is_unread"]
            missing = [f for f in required_fields if f not in email]
            
            if not missing:
                self.test_result(
                    "Email metadata has required fields",
                    True,
                    f"All {len(required_fields)} fields present"
                )
            else:
                self.test_result(
                    "Email metadata has required fields",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
    
    def _print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 60, "INFO")
        self.log("Test Summary", "INFO")
        self.log("=" * 60, "INFO")
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{BOLD}Results:{RESET}")
        print(f"  {GREEN}✓ Passed: {self.passed}{RESET}")
        print(f"  {RED}✗ Failed: {self.failed}{RESET}")
        print(f"  Total: {total}")
        print(f"  Success Rate: {percentage:.1f}%\n")
        
        if self.errors:
            print(f"{BOLD}Failed Tests:{RESET}")
            for error in self.errors:
                print(f"  • {error['test']}")
                if error['details']:
                    print(f"    {error['details']}")
            print()
        
        # Exit with appropriate code
        sys.exit(0 if self.failed == 0 else 1)

def main():
    """Run email widget tests"""
    tester = EmailWidgetTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error: {str(e)}{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
