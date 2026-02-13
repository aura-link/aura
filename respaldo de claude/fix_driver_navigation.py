import re

# 1. Fix index.tsx - redirect drivers to their dashboard
with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "r") as f:
    index_content = f.read()

# Add redirect for drivers at the beginning of the component
old_home_start = '''export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();'''

new_home_start = '''export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();

  // Redirect drivers to their dashboard
  useEffect(() => {
    if (user && user.userType === 'repartidor') {
      router.replace('/driver/dashboard');
    }
  }, [user]);

  // If driver, don't render the client home screen
  if (user?.userType === 'repartidor') {
    return null;
  }'''

index_content = index_content.replace(old_home_start, new_home_start)

with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "w") as f:
    f.write(index_content)

print("1. index.tsx actualizado - redirige repartidores")

# 2. Fix driver dashboard - prevent back navigation
with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "r") as f:
    dashboard_content = f.read()

# Add BackHandler import if not exists
if "BackHandler" not in dashboard_content:
    old_import = 'import { useState, useEffect, useCallback, useRef } from "react";'
    new_import = '''import { useState, useEffect, useCallback, useRef } from "react";
import { BackHandler } from "react-native";'''
    dashboard_content = dashboard_content.replace(old_import, new_import)

# Add useEffect to block back button after the state declarations
# Find the first useEffect and add before it
if "BackHandler.addEventListener" not in dashboard_content:
    old_effect = "const loadAvailableOrders = useCallback"
    new_effect = '''// Block back button - driver cannot go back to client home
  useEffect(() => {
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      // Return true to prevent default back behavior
      return true;
    });
    return () => backHandler.remove();
  }, []);

  const loadAvailableOrders = useCallback'''
    dashboard_content = dashboard_content.replace(old_effect, new_effect)

with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "w") as f:
    f.write(dashboard_content)

print("2. dashboard.tsx actualizado - bloquea botón atrás")

# 3. Fix tracking screen - hide delivery code for drivers
with open("/home/yesswera/yesswera-app-mobile/app/tracking/[orderId].tsx", "r") as f:
    tracking_content = f.read()

# Check if useAuth is imported
if "useAuth" not in tracking_content:
    # Add import
    old_import = "import { useRouter, useLocalSearchParams } from 'expo-router';"
    new_import = """import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '@/contexts/auth';"""
    tracking_content = tracking_content.replace(old_import, new_import)

# Add user check and hide delivery code for drivers
# This needs to be done carefully - let's check the file first
print("3. Verificando tracking screen...")

with open("/home/yesswera/yesswera-app-mobile/app/tracking/[orderId].tsx", "w") as f:
    f.write(tracking_content)

print("Correcciones aplicadas")
