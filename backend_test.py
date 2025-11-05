#!/usr/bin/env python3
"""
Connexa Admin Panel v7.0 - Comprehensive Backend Testing
Tests all 6 testing modes and core functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# Use localhost for backend testing
BASE_URL = "http://localhost:8001/api"

class ConnexaBackendTester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log(self, message, level="INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)
        
        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=test_headers, timeout=30)
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - {name} (Status: {response.status_code})", "PASS")
                result = {
                    "test": name,
                    "status": "PASSED",
                    "status_code": response.status_code,
                    "response": response.json() if response.text else {}
                }
            else:
                self.log(f"❌ FAILED - {name} (Expected {expected_status}, got {response.status_code})", "FAIL")
                result = {
                    "test": name,
                    "status": "FAILED",
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200] if response.text else ""
                }
            
            self.test_results.append(result)
            return success, response.json() if response.text and success else {}
            
        except Exception as e:
            self.log(f"❌ FAILED - {name} (Error: {str(e)})", "ERROR")
            result = {
                "test": name,
                "status": "ERROR",
                "error": str(e)
            }
            self.test_results.append(result)
            return False, {}
    
    def test_login(self):
        """Test admin login"""
        self.log("=" * 60)
        self.log("TESTING AUTHENTICATION")
        self.log("=" * 60)
        
        success, response = self.run_test(
            "Admin Login (admin/admin)",
            "POST",
            "auth/login",
            200,
            data={"username": "admin", "password": "admin"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Token obtained: {self.token[:20]}...", "SUCCESS")
            return True
        else:
            self.log("❌ Login failed - cannot proceed with tests", "CRITICAL")
            return False
    
    def test_nodes_crud(self):
        """Test basic nodes CRUD operations"""
        self.log("=" * 60)
        self.log("TESTING NODES CRUD")
        self.log("=" * 60)
        
        # Get nodes
        success, response = self.run_test(
            "Get Nodes List",
            "GET",
            "nodes?page=1&limit=10",
            200
        )
        
        if success:
            total_nodes = response.get('total', 0)
            self.log(f"📊 Total nodes in database: {total_nodes}", "INFO")
            
            if total_nodes > 0:
                nodes = response.get('nodes', [])
                if nodes:
                    node_id = nodes[0]['id']
                    self.log(f"📝 Sample node ID for testing: {node_id}", "INFO")
                    
                    # Get single node
                    self.run_test(
                        f"Get Node by ID ({node_id})",
                        "GET",
                        f"nodes/{node_id}",
                        200
                    )
                    
                    return node_id
        
        return None
    
    def test_statistics(self):
        """Test statistics endpoint"""
        self.log("=" * 60)
        self.log("TESTING STATISTICS")
        self.log("=" * 60)
        
        success, response = self.run_test(
            "Get Statistics",
            "GET",
            "statistics",
            200
        )
        
        if success:
            self.log(f"📊 Statistics: {json.dumps(response, indent=2)}", "INFO")
    
    def test_ping_light(self, node_ids):
        """Test PING LIGHT - быстрая проверка TCP портов"""
        self.log("=" * 60)
        self.log("TESTING PING LIGHT (TCP Port Check)")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 3 nodes
        test_nodes = node_ids[:3]
        
        success, response = self.run_test(
            f"Ping Light Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/ping-light-test-batch-progress",
            200,
            data={
                "node_ids": test_nodes,
                "timeout": 2
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 30
                for attempt in range(max_attempts):
                    time.sleep(2)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check Ping Light Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ Ping Light completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            if success_count == 0:
                                self.log("⚠️ WARNING: 0 успешных тестов - это проблема!", "WARN")
                                return False
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ Ping Light test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for Ping Light results", "WARN")
                return False
        
        return False
    
    def test_ping_ok(self, node_ids):
        """Test PING OK - полная проверка с авторизацией"""
        self.log("=" * 60)
        self.log("TESTING PING OK (Full PPTP Auth)")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 3 nodes
        test_nodes = node_ids[:3]
        
        success, response = self.run_test(
            f"Ping OK Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/ping-test-batch-progress",
            200,
            data={
                "node_ids": test_nodes,
                "timeout": 10
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 40
                for attempt in range(max_attempts):
                    time.sleep(3)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check Ping OK Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ Ping OK completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            if success_count == 0:
                                self.log("⚠️ WARNING: 0 успешных тестов", "WARN")
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ Ping OK test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for Ping OK results", "WARN")
                return False
        
        return False
    
    def test_speed_test(self, node_ids):
        """Test SPEED TEST"""
        self.log("=" * 60)
        self.log("TESTING SPEED TEST")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 2 nodes (speed tests are slower)
        test_nodes = node_ids[:2]
        
        success, response = self.run_test(
            f"Speed Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/speed-test-batch-progress",
            200,
            data={
                "node_ids": test_nodes,
                "sample_kb": 512,
                "timeout": 15
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 50
                for attempt in range(max_attempts):
                    time.sleep(3)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check Speed Test Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ Speed Test completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            # Check if speed data is present
                            speeds = [r.get('speed') for r in results if r.get('speed')]
                            if speeds:
                                self.log(f"📊 Speed results: {speeds}", "INFO")
                            else:
                                self.log("⚠️ WARNING: No speed data in results", "WARN")
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ Speed Test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for Speed Test results", "WARN")
                return False
        
        return False
    
    def test_geo_test(self, node_ids):
        """Test GEO TEST"""
        self.log("=" * 60)
        self.log("TESTING GEO TEST")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 3 nodes
        test_nodes = node_ids[:3]
        
        success, response = self.run_test(
            f"GEO Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/geo-test-batch",
            200,
            data={
                "node_ids": test_nodes
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 30
                for attempt in range(max_attempts):
                    time.sleep(2)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check GEO Test Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ GEO Test completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            # Check if coordinates are present
                            coords = [r.get('coordinates') for r in results if r.get('coordinates')]
                            if coords:
                                self.log(f"📍 Coordinates found: {coords}", "INFO")
                            else:
                                self.log("⚠️ WARNING: No coordinates in results", "WARN")
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ GEO Test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for GEO Test results", "WARN")
                return False
        
        return False
    
    def test_fraud_test(self, node_ids):
        """Test FRAUD TEST"""
        self.log("=" * 60)
        self.log("TESTING FRAUD TEST (IPQS)")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 3 nodes
        test_nodes = node_ids[:3]
        
        success, response = self.run_test(
            f"Fraud Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/fraud-test-batch",
            200,
            data={
                "node_ids": test_nodes
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 30
                for attempt in range(max_attempts):
                    time.sleep(2)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check Fraud Test Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ Fraud Test completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            # Check if fraud scores are present
                            fraud_scores = [r.get('fraud_score') for r in results if r.get('fraud_score') is not None]
                            risk_levels = [r.get('risk_level') for r in results if r.get('risk_level')]
                            
                            if fraud_scores:
                                self.log(f"🔍 Fraud scores: {fraud_scores}", "INFO")
                            if risk_levels:
                                self.log(f"⚠️ Risk levels: {risk_levels}", "INFO")
                            
                            if not fraud_scores and not risk_levels:
                                self.log("⚠️ WARNING: No fraud data in results", "WARN")
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ Fraud Test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for Fraud Test results", "WARN")
                return False
        
        return False
    
    def test_geo_fraud_combined(self, node_ids):
        """Test GEO+FRAUD COMBINED TEST"""
        self.log("=" * 60)
        self.log("TESTING GEO+FRAUD COMBINED TEST")
        self.log("=" * 60)
        
        if not node_ids:
            self.log("⚠️ No nodes to test", "WARN")
            return False
        
        # Test with first 3 nodes
        test_nodes = node_ids[:3]
        
        success, response = self.run_test(
            f"GEO+Fraud Test ({len(test_nodes)} nodes)",
            "POST",
            "manual/geo-fraud-test-batch",
            200,
            data={
                "node_ids": test_nodes
            }
        )
        
        if success:
            session_id = response.get('session_id')
            if session_id:
                self.log(f"🔄 Session started: {session_id}", "INFO")
                
                # Poll for results
                max_attempts = 40
                for attempt in range(max_attempts):
                    time.sleep(2)
                    
                    progress_success, progress_data = self.run_test(
                        f"Check GEO+Fraud Progress (attempt {attempt+1})",
                        "GET",
                        f"progress/{session_id}",
                        200
                    )
                    
                    if progress_success:
                        status = progress_data.get('status')
                        processed = progress_data.get('processed_items', 0)
                        total = progress_data.get('total_items', 0)
                        
                        self.log(f"📊 Progress: {processed}/{total} ({status})", "INFO")
                        
                        if status == 'completed':
                            results = progress_data.get('results', [])
                            success_count = sum(1 for r in results if r.get('success'))
                            self.log(f"✅ GEO+Fraud Test completed: {success_count}/{len(results)} успешно", "SUCCESS")
                            
                            # Check if both geo and fraud data are present
                            coords = [r.get('coordinates') for r in results if r.get('coordinates')]
                            fraud_scores = [r.get('fraud_score') for r in results if r.get('fraud_score') is not None]
                            
                            if coords:
                                self.log(f"📍 Coordinates: {coords}", "INFO")
                            if fraud_scores:
                                self.log(f"🔍 Fraud scores: {fraud_scores}", "INFO")
                            
                            if not coords or not fraud_scores:
                                self.log("⚠️ WARNING: Missing geo or fraud data", "WARN")
                            
                            return True
                        
                        elif status == 'failed':
                            self.log("❌ GEO+Fraud Test failed", "ERROR")
                            return False
                
                self.log("⏱️ Timeout waiting for GEO+Fraud results", "WARN")
                return False
        
        return False
    
    def test_import_nodes(self):
        """Test node import functionality"""
        self.log("=" * 60)
        self.log("TESTING NODE IMPORT")
        self.log("=" * 60)
        
        # Sample PPTP data
        sample_data = """5.161.93.53 admin admin
24.199.103.217 admin admin
68.183.141.27 admin admin"""
        
        success, response = self.run_test(
            "Import Nodes (3 sample nodes)",
            "POST",
            "nodes/import",
            200,
            data={
                "data": sample_data,
                "protocol": "pptp"
            }
        )
        
        if success:
            added = response.get('report', {}).get('added', 0)
            self.log(f"📥 Import result: {added} nodes added", "INFO")
            return True
        
        return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        self.log("=" * 80)
        self.log("CONNEXA ADMIN PANEL v7.0 - COMPREHENSIVE BACKEND TESTING")
        self.log("=" * 80)
        
        # Step 1: Login
        if not self.test_login():
            self.log("❌ CRITICAL: Cannot login - stopping tests", "CRITICAL")
            return False
        
        # Step 2: Test CRUD
        node_id = self.test_nodes_crud()
        
        # Step 3: Test Statistics
        self.test_statistics()
        
        # Step 4: Get node IDs for testing
        success, response = self.run_test(
            "Get All Node IDs",
            "GET",
            "nodes/all-ids",
            200
        )
        
        node_ids = []
        if success:
            node_ids = response.get('node_ids', [])
            self.log(f"📋 Found {len(node_ids)} nodes for testing", "INFO")
        
        if not node_ids:
            self.log("⚠️ No nodes found - importing sample nodes", "WARN")
            self.test_import_nodes()
            
            # Try again
            success, response = self.run_test(
                "Get All Node IDs (after import)",
                "GET",
                "nodes/all-ids",
                200
            )
            if success:
                node_ids = response.get('node_ids', [])
        
        if not node_ids:
            self.log("❌ CRITICAL: No nodes available for testing", "CRITICAL")
            return False
        
        # Step 5: Test all 6 testing modes
        self.test_ping_light(node_ids)
        self.test_ping_ok(node_ids)
        self.test_speed_test(node_ids)
        self.test_geo_test(node_ids)
        self.test_fraud_test(node_ids)
        self.test_geo_fraud_combined(node_ids)
        
        # Final summary
        self.log("=" * 80)
        self.log("TEST SUMMARY")
        self.log("=" * 80)
        self.log(f"Total Tests: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "SUCCESS")
        self.log(f"Failed: {self.tests_run - self.tests_passed}", "ERROR")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%", "INFO")
        
        # Save results
        results_file = "/app/test_reports/backend_test_results_v7.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": self.tests_run,
                "passed": self.tests_passed,
                "failed": self.tests_run - self.tests_passed,
                "success_rate": f"{(self.tests_passed/self.tests_run*100):.1f}%",
                "test_results": self.test_results
            }, f, indent=2)
        
        self.log(f"📄 Results saved to: {results_file}", "INFO")
        
        return self.tests_passed == self.tests_run

def main():
    tester = ConnexaBackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
