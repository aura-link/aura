#!/bin/bash

echo "=== Testing Login ==="
LOGIN_RESPONSE=$(curl -s -X POST http://192.168.100.2:3000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"juan@test.com","password":"testPassword123"}')

echo "$LOGIN_RESPONSE" | python3 -m json.tool

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
USER_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

echo ""
echo "Token: ${TOKEN:0:30}..."
echo "User ID: $USER_ID"

echo ""
echo "=== Testing Get All Orders ==="
curl -s -X GET "http://192.168.100.2:3000/api/orders/user/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo ""
echo "=== Testing Get Active Orders ==="
curl -s -X GET "http://192.168.100.2:3000/api/orders/user/$USER_ID/active" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool
