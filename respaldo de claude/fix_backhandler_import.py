with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "r") as f:
    content = f.read()

# Fix: Merge BackHandler import with other react-native imports
old_imports = '''import { useState, useEffect, useCallback, useRef } from "react";
import { BackHandler } from "react-native";
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Alert, Modal, Vibration } from "react-native";'''

new_imports = '''import { useState, useEffect, useCallback, useRef } from "react";
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Alert, Modal, Vibration, BackHandler } from "react-native";'''

content = content.replace(old_imports, new_imports)

with open("/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx", "w") as f:
    f.write(content)

print("BackHandler import fixed!")
