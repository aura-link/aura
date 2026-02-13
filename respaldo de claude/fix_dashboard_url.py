with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "r") as f:
    content = f.read()

# Fix the malformed URL
content = content.replace('/orders//take${orderId}', '/orders/${orderId}/take')

with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "w") as f:
    f.write(content)

print("URL corregida")
