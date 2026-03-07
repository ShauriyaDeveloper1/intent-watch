import { useEffect, useMemo, useState } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

type CameraSource = 'webcam' | 'video_file' | 'rtsp';
type Resolution = '640x480' | '1280x720' | '1920x1080';
type ThemeColor = 'purple' | 'blue' | 'green' | 'red' | 'orange' | 'vibrant';
type UiMode = 'default' | 'dark' | 'light' | 'colorful' | 'vibrant';

type SettingsState = {
  // Camera Settings
  cameraSource: CameraSource;
  resolution: Resolution;
  fps: number;
  rtspUrl: string;

  // Detection Settings
  confidence: number;
  loiteringThreshold: number;
  bagThreshold: number;
  detectPeople: boolean;
  detectLoitering: boolean;
  detectRunning: boolean;
  detectUnattendedBag: boolean;

  // Alert Settings
  sound: boolean;
  alertLogging: boolean;
  email: boolean;

  // System Settings
  uiMode: UiMode;
  theme: boolean;
  themeColor: ThemeColor;
  autoStart: boolean;
};

export function Settings() {
  const SETTINGS_STORAGE_KEY = 'intentwatch.settings.v1';

  const defaultSettings = useMemo<SettingsState>(
    () => ({
      cameraSource: 'webcam',
      resolution: '1280x720',
      fps: 30,
      rtspUrl: '',

      confidence: 50,
      loiteringThreshold: 10,
      bagThreshold: 15,
      detectPeople: true,
      detectLoitering: true,
      detectRunning: true,
      detectUnattendedBag: true,

      sound: true,
      alertLogging: true,
      email: false,

      uiMode: 'default',
      theme: true,
      themeColor: 'purple',
      autoStart: false,
    }),
    [],
  );

  const [settings, setSettings] = useState<SettingsState>(defaultSettings);

  const loadPersistedSettings = () => {
    try {
      const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<SettingsState> | null;
      if (!parsed || typeof parsed !== 'object') return;

      setSettings((prev) => {
        const next: SettingsState = { ...prev };

        const cameraSource = parsed.cameraSource;
        if (cameraSource === 'webcam' || cameraSource === 'video_file' || cameraSource === 'rtsp') next.cameraSource = cameraSource;

        const resolution = parsed.resolution;
        if (resolution === '640x480' || resolution === '1280x720' || resolution === '1920x1080') next.resolution = resolution;

        if (typeof parsed.fps === 'number' && Number.isFinite(parsed.fps)) next.fps = parsed.fps;
        if (typeof parsed.rtspUrl === 'string') next.rtspUrl = parsed.rtspUrl;

        if (typeof parsed.confidence === 'number' && Number.isFinite(parsed.confidence)) next.confidence = parsed.confidence;
        if (typeof parsed.loiteringThreshold === 'number' && Number.isFinite(parsed.loiteringThreshold)) next.loiteringThreshold = parsed.loiteringThreshold;
        if (typeof parsed.bagThreshold === 'number' && Number.isFinite(parsed.bagThreshold)) next.bagThreshold = parsed.bagThreshold;

        if (typeof parsed.detectPeople === 'boolean') next.detectPeople = parsed.detectPeople;
        if (typeof parsed.detectLoitering === 'boolean') next.detectLoitering = parsed.detectLoitering;
        if (typeof parsed.detectRunning === 'boolean') next.detectRunning = parsed.detectRunning;
        if (typeof parsed.detectUnattendedBag === 'boolean') next.detectUnattendedBag = parsed.detectUnattendedBag;

        if (typeof parsed.sound === 'boolean') next.sound = parsed.sound;
        if (typeof parsed.alertLogging === 'boolean') next.alertLogging = parsed.alertLogging;
        if (typeof parsed.email === 'boolean') next.email = parsed.email;

        const uiMode = parsed.uiMode;
        if (uiMode === 'default' || uiMode === 'dark' || uiMode === 'light' || uiMode === 'colorful' || uiMode === 'vibrant') next.uiMode = uiMode;

        if (typeof parsed.theme === 'boolean') next.theme = parsed.theme;

        const themeColor = parsed.themeColor;
        if (
          themeColor === 'purple' ||
          themeColor === 'blue' ||
          themeColor === 'green' ||
          themeColor === 'red' ||
          themeColor === 'orange' ||
          themeColor === 'vibrant'
        ) {
          next.themeColor = themeColor;
        }

        if (typeof parsed.autoStart === 'boolean') next.autoStart = parsed.autoStart;

        return next;
      });
    } catch {
      // ignore
    }
  };

  // Hydrate persisted UI preferences on first load (optional)
  useEffect(() => {
    loadPersistedSettings();
    try {
      const storedUi = window.localStorage.getItem('intentwatch.uiMode');
      if (storedUi === 'default' || storedUi === 'dark' || storedUi === 'light' || storedUi === 'colorful' || storedUi === 'vibrant') {
        setSettings((prev) => ({ ...prev, uiMode: storedUi }));
      }

      const stored = window.localStorage.getItem('intentwatch.themeColor');
      if (stored === 'purple' || stored === 'blue' || stored === 'green' || stored === 'red' || stored === 'orange' || stored === 'vibrant') {
        setSettings((prev) => ({ ...prev, themeColor: stored }));
      }
    } catch {
      // ignore
    }
  }, []);

  const update = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));

    if (key === 'uiMode') {
      try {
        window.localStorage.setItem('intentwatch.uiMode', String(value));
      } catch {
        // ignore
      }
      window.dispatchEvent(new Event('intentwatch:ui'));
    }

    if (key === 'themeColor') {
      try {
        window.localStorage.setItem('intentwatch.themeColor', String(value));
      } catch {
        // ignore
      }
      window.dispatchEvent(new Event('intentwatch:theme'));
    }
  };

  const reset = () => {
    setSettings(defaultSettings);
    try {
      window.localStorage.removeItem(SETTINGS_STORAGE_KEY);
      window.localStorage.setItem('intentwatch.uiMode', defaultSettings.uiMode);
      window.localStorage.setItem('intentwatch.themeColor', defaultSettings.themeColor);
    } catch {
      // ignore
    }
    window.dispatchEvent(new Event('intentwatch:ui'));
    window.dispatchEvent(new Event('intentwatch:theme'));
  };

  const save = () => {
    try {
      window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
      window.localStorage.setItem('intentwatch.uiMode', settings.uiMode);
      window.localStorage.setItem('intentwatch.themeColor', settings.themeColor);
    } catch {
      // ignore
    }
    window.dispatchEvent(new Event('intentwatch:ui'));
    window.dispatchEvent(new Event('intentwatch:theme'));
  };

  const saveButtonTheme = useMemo(() => {
    const map: Record<ThemeColor, { bg: string; hoverBg: string }> = {
      purple: { bg: 'bg-purple-600', hoverBg: 'hover:bg-purple-700' },
      blue: { bg: 'bg-blue-600', hoverBg: 'hover:bg-blue-700' },
      green: { bg: 'bg-green-600', hoverBg: 'hover:bg-green-700' },
      red: { bg: 'bg-red-600', hoverBg: 'hover:bg-red-700' },
      orange: { bg: 'bg-orange-600', hoverBg: 'hover:bg-orange-700' },
      vibrant: { bg: 'bg-gradient-to-r from-purple-600 via-red-600 to-orange-600', hoverBg: 'hover:opacity-90' },
    };
    return map[settings.themeColor];
  }, [settings.themeColor]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Configure camera, detection, alerts, and system behavior</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Camera Settings */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground">Camera Settings</h2>
          <div className="mt-4 space-y-4">
            <div>
              <Label className="text-muted-foreground">Camera Source</Label>
              <Select value={settings.cameraSource} onValueChange={(v) => update('cameraSource', v as CameraSource)}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="webcam">Webcam</SelectItem>
                  <SelectItem value="video_file">Video File</SelectItem>
                  <SelectItem value="rtsp">RTSP</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-muted-foreground">Resolution</Label>
              <Select value={settings.resolution} onValueChange={(v) => update('resolution', v as Resolution)}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select resolution" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="640x480">640x480</SelectItem>
                  <SelectItem value="1280x720">1280x720</SelectItem>
                  <SelectItem value="1920x1080">1920x1080</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-muted-foreground">FPS</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={Number.isFinite(settings.fps) ? settings.fps : ''}
                onChange={(e) => update('fps', Number(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <Label className="text-muted-foreground">RTSP URL</Label>
              <Input
                value={settings.rtspUrl}
                onChange={(e) => update('rtspUrl', e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
        </Card>

        {/* Detection Settings */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground">Detection Settings</h2>
          <div className="mt-4 space-y-6">
            <div>
              <Label className="text-muted-foreground">Confidence</Label>
              <div className="mt-2">
                <Slider
                  value={[settings.confidence]}
                  min={0}
                  max={100}
                  step={1}
                  onValueChange={(v) => update('confidence', v[0] ?? 0)}
                />
              </div>
            </div>

            <div>
              <Label className="text-muted-foreground">Loitering threshold</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={Number.isFinite(settings.loiteringThreshold) ? settings.loiteringThreshold : ''}
                onChange={(e) => update('loiteringThreshold', Number(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <Label className="text-muted-foreground">Bag threshold</Label>
              <Input
                type="number"
                inputMode="numeric"
                value={Number.isFinite(settings.bagThreshold) ? settings.bagThreshold : ''}
                onChange={(e) => update('bagThreshold', Number(e.target.value))}
                className="mt-1"
              />
            </div>

            <div>
              <Label className="text-muted-foreground">Detection toggles</Label>
              <div className="mt-2 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">People</span>
                  <Switch checked={settings.detectPeople} onCheckedChange={(v) => update('detectPeople', Boolean(v))} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Loitering</span>
                  <Switch checked={settings.detectLoitering} onCheckedChange={(v) => update('detectLoitering', Boolean(v))} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Running</span>
                  <Switch checked={settings.detectRunning} onCheckedChange={(v) => update('detectRunning', Boolean(v))} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-foreground">Unattended Bag</span>
                  <Switch
                    checked={settings.detectUnattendedBag}
                    onCheckedChange={(v) => update('detectUnattendedBag', Boolean(v))}
                  />
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Alert Settings */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground">Alert Settings</h2>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Sound toggle</span>
              <Switch checked={settings.sound} onCheckedChange={(v) => update('sound', Boolean(v))} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Alert logging toggle</span>
              <Switch checked={settings.alertLogging} onCheckedChange={(v) => update('alertLogging', Boolean(v))} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Email toggle</span>
              <Switch checked={settings.email} onCheckedChange={(v) => update('email', Boolean(v))} />
            </div>
          </div>
        </Card>

        {/* System Settings */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-foreground">System Settings</h2>
          <div className="mt-4 space-y-4">
            <div>
              <Label className="text-muted-foreground">UI color</Label>
              <Select value={settings.uiMode} onValueChange={(v) => update('uiMode', v as UiMode)}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select UI mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="colorful">Colorful</SelectItem>
                  <SelectItem value="vibrant">Vibrant</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Theme toggle</span>
              <Switch checked={settings.theme} onCheckedChange={(v) => update('theme', Boolean(v))} />
            </div>

            <div>
              <Label className="text-muted-foreground">Theme color</Label>
              <Select value={settings.themeColor} onValueChange={(v) => update('themeColor', v as ThemeColor)}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select color" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="purple">Purple</SelectItem>
                  <SelectItem value="blue">Blue</SelectItem>
                  <SelectItem value="green">Green</SelectItem>
                  <SelectItem value="red">Red</SelectItem>
                  <SelectItem value="orange">Orange</SelectItem>
                  <SelectItem value="vibrant">Vibrant</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Auto start toggle</span>
              <Switch checked={settings.autoStart} onCheckedChange={(v) => update('autoStart', Boolean(v))} />
            </div>
            <div>
              <Button onClick={reset} variant="destructive" className="bg-red-600 hover:bg-red-700">
                Reset
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button onClick={save} className={`${saveButtonTheme.bg} ${saveButtonTheme.hoverBg} text-white`}>
          Save
        </Button>
      </div>
    </div>
  );
}
