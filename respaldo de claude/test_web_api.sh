#!/bin/bash

# Web App Automated Testing Script
# Tests Yesswera Web Application API endpoints

API_URL="http://192.168.100.3:3000"
TEST_RESULTS="test_results_$(date +%Y%m%d_%H%M%S).log"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       YESSWERA WEB APP - AUTOMATED TESTING SUITE              ║"
echo "║                                                                ║"
echo "║  Testing: $API_URL"
echo "║  Date: $(date)"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
TOTAL=0

# Function to test HTTP response
test_endpoint() {
    local test_num=$1
    local test_name=$2
    local method=$3
    local endpoint=$4
    local data=$5
    local expected_code=$6

    TOTAL=$((TOTAL + 1))

    echo -e "${BLUE}[TEST $test_num]${NC} $test_name"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "$expected_code"* ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} (HTTP $http_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} (Expected HTTP $expected_code, got $http_code)"
        echo "  Response: $body"
        FAILED=$((FAILED + 1))
    fi

    echo ""
}

# Test 1: Server is responding
echo -e "${YELLOW}═══ BASIC CONNECTIVITY TESTS ═══${NC}"
test_endpoint "1" "Web server responds" "GET" "/" "200"

# Test 2: HTML content
echo -e "${YELLOW}═══ CONTENT TESTS ═══${NC}"
echo "[TEST 2] HTML Content Validation"
html=$(curl -s "$API_URL/")
if echo "$html" | grep -q "Yesswera" && echo "$html" | grep -q "Iniciar Sesión"; then
    echo -e "  ${GREEN}✅ PASS${NC} (HTML contains expected elements)"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} (HTML missing expected content)"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))
echo ""

# Test 3: Login with valid credentials (example)
echo -e "${YELLOW}═══ AUTHENTICATION TESTS ═══${NC}"
echo "[TEST 3] Login Endpoint Exists"
login_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test123"}' \
    "$API_URL/login")

if echo "$login_response" | grep -q "token\|message\|error"; then
    echo -e "  ${GREEN}✅ PASS${NC} (Login endpoint responds)"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠️  WARNING${NC} (Login endpoint not responding as expected)"
    echo "  Response: $login_response"
fi
TOTAL=$((TOTAL + 1))
echo ""

# Test 4: Test with empty credentials
echo "[TEST 4] Login with Empty Email"
empty_email=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"","password":"test123"}' \
    "$API_URL/login")
echo "  Response: $empty_email"
TOTAL=$((TOTAL + 1))
echo ""

# Test 5: Invalid method
echo "[TEST 5] Invalid HTTP Method on Login"
invalid_method=$(curl -s -X PUT \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test123"}' \
    -o /dev/null -w "%{http_code}" \
    "$API_URL/login")
echo -e "  HTTP Response Code: $invalid_method"
TOTAL=$((TOTAL + 1))
echo ""

# Test 6: Content-Type header
echo "[TEST 6] Content-Type Header"
html_type=$(curl -s -I "$API_URL/" | grep -i "Content-Type")
echo -e "  ${YELLOW}Content-Type:${NC} $html_type"
if echo "$html_type" | grep -q "text/html"; then
    echo -e "  ${GREEN}✅ PASS${NC} (Correct content type)"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} (Incorrect content type)"
    FAILED=$((FAILED + 1))
fi
TOTAL=$((TOTAL + 1))
echo ""

# Test 7: Response time
echo "[TEST 7] Response Time Test"
start=$(date +%s%N)
curl -s "$API_URL/" > /dev/null
end=$(date +%s%N)
response_time=$(( (end - start) / 1000000 ))
echo -e "  Response time: ${BLUE}${response_time}ms${NC}"
if [ "$response_time" -lt 1000 ]; then
    echo -e "  ${GREEN}✅ PASS${NC} (Response time acceptable)"
    PASSED=$((PASSED + 1))
else
    echo -e "  ${YELLOW}⚠️  WARNING${NC} (Slow response time)"
fi
TOTAL=$((TOTAL + 1))
echo ""

# Test 8: CORS headers (if applicable)
echo "[TEST 8] Security Headers"
headers=$(curl -s -I "$API_URL/" | grep -i "X-\|Access-Control-\|Content-Security")
if [ -z "$headers" ]; then
    echo -e "  ${YELLOW}⚠️  No security headers found${NC} (May be expected)"
else
    echo -e "  ${GREEN}✅ Security headers present:${NC}"
    echo "$headers" | sed 's/^/    /'
fi
TOTAL=$((TOTAL + 1))
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      TEST SUMMARY                             ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║"
echo "║  Total Tests:      $TOTAL"
echo "║  Passed:           $(printf "%-3d" $PASSED) ${GREEN}✅${NC}"
echo "║  Failed:           $(printf "%-3d" $FAILED) ${RED}❌${NC}"
pass_rate=$((PASSED * 100 / TOTAL))
echo "║  Pass Rate:        $pass_rate%"
echo "║"
echo "║  Test Log:         $TEST_RESULTS"
echo "║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Detailed recommendations
echo -e "${YELLOW}═══ NEXT STEPS ═══${NC}"
echo ""
echo "1. Manual Testing:"
echo "   - Open browser to: $API_URL"
echo "   - Test login with valid credentials"
echo "   - Verify session persistence"
echo "   - Test logout functionality"
echo ""
echo "2. Backend Integration:"
echo "   - Verify backend is returning proper responses"
echo "   - Check user credentials are configured"
echo "   - Validate token generation"
echo ""
echo "3. Frontend Debugging:"
echo "   - Check browser console for JavaScript errors"
echo "   - Verify localStorage token storage"
echo "   - Test on different browsers"
echo ""
echo "4. Mobile App Preparation:"
echo "   - Once web app passes all manual tests"
echo "   - Proceed with Android APK compilation"
echo "   - Use EAS Build (Recommended)"
echo ""

# Save results
{
    echo "YESSWERA WEB APP - TEST RESULTS"
    echo "=================================="
    echo "Date: $(date)"
    echo "API URL: $API_URL"
    echo ""
    echo "Results:"
    echo "  Total: $TOTAL"
    echo "  Passed: $PASSED"
    echo "  Failed: $FAILED"
    echo "  Pass Rate: $pass_rate%"
} > "$TEST_RESULTS"

echo -e "${BLUE}Results saved to: $TEST_RESULTS${NC}"
echo ""
