import type { Alert } from './api';

const seenAlertKeys = new Set<string>();

let _audioCtx: AudioContext | null = null;

function _isSoundEnabled(): boolean {
  try {
    const raw = window.localStorage.getItem('intentwatch.settings.v1');
    if (!raw) return true;
    const parsed = JSON.parse(raw) as any;
    if (parsed && typeof parsed.sound === 'boolean') return parsed.sound;
    return true;
  } catch {
    return true;
  }
}

function _beepBestEffort(): void {
  try {
    if (typeof window === 'undefined') return;
    if (!_isSoundEnabled()) return;

    const AnyWindow = window as any;
    const Ctx = AnyWindow.AudioContext || AnyWindow.webkitAudioContext;
    if (!Ctx) return;

    if (_audioCtx == null) {
      _audioCtx = new Ctx();
    }

    // Some browsers start audio contexts suspended until user interaction.
    if (_audioCtx.state === 'suspended') {
      void _audioCtx.resume().catch(() => undefined);
    }

    const ctx = _audioCtx;
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.value = 880;

    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.15, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.2);
  } catch {
    // ignore
  }
}

export function ensureNotificationPermissionNonBlocking(): void {
  try {
    if (typeof window === 'undefined') return;
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') return;
    if (Notification.permission === 'denied') return;
    // Do not await; never block UI on permission prompt.
    void Notification.requestPermission();
  } catch {
    // ignore
  }
}

function getAlertKey(a: Alert): string {
  return String(a.id ?? a.timestamp ?? `${a.type}-${a.time}-${a.message}`);
}

export function shouldNotifyAlert(a: Alert): boolean {
  const t = (a.type || '').toLowerCase();
  // Only these types should trigger OS/device notifications.
  // - Weapon + unattended bag (default)
  // - Restricted-zone entry (explicit user requirement)
  if (t.includes('weapon') || t.includes('bag')) return true;

  if (t.includes('zone')) {
    const msg = String(a.message || '').toLowerCase();
    return msg.includes('restricted zone entry');
  }

  return false;
}

export function notifyAlert(a: Alert): void {
  try {
    if (typeof window === 'undefined') return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    if (!shouldNotifyAlert(a)) return;

    const key = getAlertKey(a);
    if (seenAlertKeys.has(key)) return;
    seenAlertKeys.add(key);

    new Notification(a.type, {
      body: a.message,
      tag: key,
    });

    // Best-effort audible cue (only when the web app is open).
    _beepBestEffort();
  } catch {
    // ignore
  }
}
