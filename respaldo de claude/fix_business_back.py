#!/usr/bin/env python3
"""Add BackHandler to business dashboard to prevent going back"""

with open("/home/yesswera/yesswera-app-mobile/app/business/dashboard.tsx", "r") as f:
    content = f.read()

# 1. Add useEffect import and BackHandler import
old_imports = '''import { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Alert, TextInput } from 'react-native';'''

new_imports = '''import { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Alert, TextInput, BackHandler } from 'react-native';'''

content = content.replace(old_imports, new_imports)

# 2. Add useEffect for BackHandler after the useState declarations
old_state = '''const [showAddProduct, setShowAddProduct] = useState(false);

  const stats = {'''

new_state = '''const [showAddProduct, setShowAddProduct] = useState(false);

  // Block hardware back button - only logout allows leaving dashboard
  useEffect(() => {
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      // Return true to prevent default back behavior
      return true;
    });
    return () => backHandler.remove();
  }, []);

  const stats = {'''

content = content.replace(old_state, new_state)

with open("/home/yesswera/yesswera-app-mobile/app/business/dashboard.tsx", "w") as f:
    f.write(content)

print("Business dashboard back button blocked!")
