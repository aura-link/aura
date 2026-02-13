with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "r") as f:
    content = f.read()

# Add redirect logic in the first useEffect, right after checking user/token
old_useeffect = '''useEffect(() => {
    if (!user || !token) {
      setActiveOrder(null);
      return;
    }

    const checkActiveOrder = async () => {'''

new_useeffect = '''useEffect(() => {
    if (!user || !token) {
      setActiveOrder(null);
      return;
    }

    // Redirect based on user type
    if (user.userType === 'repartidor') {
      router.replace('/driver/dashboard');
      return;
    }
    if (user.userType === 'negocio') {
      router.replace('/business/dashboard');
      return;
    }

    const checkActiveOrder = async () => {'''

content = content.replace(old_useeffect, new_useeffect)

with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "w") as f:
    f.write(content)

print("Redirect logic added correctly")
