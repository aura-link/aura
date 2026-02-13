with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "r") as f:
    content = f.read()

# Fix: Move the conditional return AFTER all hooks
old_code = '''export default function HomeScreen() {
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
  }
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [showReorderSection, setShowReorderSection] = useState(true);
  const logoScale = useRef(new Animated.Value(0)).current;
  const logoOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {'''

new_code = '''export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [showReorderSection, setShowReorderSection] = useState(true);
  const logoScale = useRef(new Animated.Value(0)).current;
  const logoOpacity = useRef(new Animated.Value(0)).current;

  // Redirect drivers to their dashboard
  useEffect(() => {
    if (user && user.userType === 'repartidor') {
      router.replace('/driver/dashboard');
    }
  }, [user]);

  // If driver, don't render the client home screen
  if (user?.userType === 'repartidor') {
    return null;
  }

  useEffect(() => {'''

content = content.replace(old_code, new_code)

with open("/home/yesswera/yesswera-app-mobile/app/index.tsx", "w") as f:
    f.write(content)

print("Hooks order fixed!")
