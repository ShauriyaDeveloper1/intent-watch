import { Link, useLocation } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { 
  LayoutDashboard, 
  Video, 
  BarChart3, 
  Bell, 
  MapPin,
  Settings as SettingsIcon,
  Activity,
  Shield
} from 'lucide-react';

type ThemeColor = 'purple' | 'blue' | 'green' | 'red' | 'orange' | 'vibrant';
type UiMode = 'default' | 'dark' | 'light' | 'colorful' | 'vibrant';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/feed', icon: Video, label: 'Live Feed' },
  { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  { path: '/alerts', icon: Bell, label: 'Alerts Log' },
  { path: '/zones', icon: MapPin, label: 'Zone Config' },
  { path: '/settings', icon: SettingsIcon, label: 'Settings' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [themeColor, setThemeColor] = useState<ThemeColor>('purple');
  const [uiMode, setUiMode] = useState<UiMode>('default');

  useEffect(() => {
    const readSettings = () => {
      try {
        const raw = window.localStorage.getItem('intentwatch.themeColor');
        if (raw === 'purple' || raw === 'blue' || raw === 'green' || raw === 'red' || raw === 'orange' || raw === 'vibrant') {
          setThemeColor(raw);
        }

        const rawUi = window.localStorage.getItem('intentwatch.uiMode');
        if (rawUi === 'default' || rawUi === 'dark' || rawUi === 'light' || rawUi === 'colorful' || rawUi === 'vibrant') {
          setUiMode(rawUi);
        }
      } catch {
        // ignore
      }
    };

    readSettings();
    window.addEventListener('intentwatch:theme', readSettings as EventListener);
    window.addEventListener('intentwatch:ui', readSettings as EventListener);
    return () => {
      window.removeEventListener('intentwatch:theme', readSettings as EventListener);
      window.removeEventListener('intentwatch:ui', readSettings as EventListener);
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    const mql = window.matchMedia?.('(prefers-color-scheme: dark)');

    const apply = (forceDark: boolean) => {
      if (forceDark) root.classList.add('dark');
      else root.classList.remove('dark');
    };

    const applyFromMode = () => {
      if (uiMode === 'dark') return apply(true);
      if (uiMode === 'light') return apply(false);
      apply(Boolean(mql?.matches));
    };

    applyFromMode();

    if ((uiMode !== 'default' && uiMode !== 'colorful' && uiMode !== 'vibrant') || !mql) return;
    const onChange = () => applyFromMode();
    try {
      mql.addEventListener('change', onChange);
      return () => mql.removeEventListener('change', onChange);
    } catch {
      // Safari/older fallback
      // @ts-expect-error legacy
      mql.addListener?.(onChange);
      return () => {
        // @ts-expect-error legacy
        mql.removeListener?.(onChange);
      };
    }
  }, [uiMode]);

  const effectiveThemeColor: ThemeColor = uiMode === 'vibrant' ? 'vibrant' : themeColor;

  const brand = useMemo(() => {
    const map: Record<ThemeColor, { bg: string; hoverBg: string; softFrom: string }> = {
      purple: { bg: 'bg-purple-600', hoverBg: 'hover:bg-purple-700', softFrom: 'from-purple-500/10' },
      blue: { bg: 'bg-blue-600', hoverBg: 'hover:bg-blue-700', softFrom: 'from-blue-500/10' },
      green: { bg: 'bg-green-600', hoverBg: 'hover:bg-green-700', softFrom: 'from-green-500/10' },
      red: { bg: 'bg-red-600', hoverBg: 'hover:bg-red-700', softFrom: 'from-red-500/10' },
      orange: { bg: 'bg-orange-600', hoverBg: 'hover:bg-orange-700', softFrom: 'from-orange-500/10' },
      vibrant: {
        bg: 'bg-gradient-to-r from-purple-600 via-red-600 to-orange-600',
        hoverBg: 'hover:opacity-90',
        softFrom: 'from-purple-500/15',
      },
    };
    return map[effectiveThemeColor];
  }, [effectiveThemeColor]);

  const shellBg = uiMode === 'colorful'
    ? effectiveThemeColor === 'vibrant'
      ? 'bg-gradient-to-br from-purple-500/20 via-orange-500/10 to-background'
      : `bg-gradient-to-br ${brand.softFrom} via-background to-background`
    : uiMode === 'vibrant'
      ? 'bg-gradient-to-br from-purple-500/20 via-red-500/10 to-background'
      : 'bg-background';

  return (
    <div className={`min-h-screen ${shellBg} text-foreground`}>
      {/* Header */}
      <header className="bg-sidebar text-sidebar-foreground border-b border-border">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`${brand.bg} p-2 rounded-lg`}>
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold">IntentWatch</h1>
                <p className="text-xs text-muted-foreground">v2.0 - AI Surveillance System</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-400 animate-pulse" />
              <span className="text-sm text-green-400">System Active</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-73px)]">
        {/* Sidebar */}
        <aside className="w-64 bg-sidebar text-sidebar-foreground border-r border-border">
          <nav className="p-4 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? `${brand.bg} text-white`
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
