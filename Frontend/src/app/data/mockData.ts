// Mock data for the surveillance system

export interface Alert {
  id: string;
  timestamp: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  location: string;
  camera: string;
}

export interface Stats {
  peopleDetected: number;
  activeAlerts: number;
  camerasOnline: number;
  threatLevel: string;
  uptime: string;
}

export const generateMockAlerts = (count: number = 50): Alert[] => {
  const types = [
    'Weapon Detected',
    'Unauthorized Access',
    'Loitering',
    'Crowd Detected',
    'Running Detected',
    'Zone Breach',
    'Suspicious Activity',
    'Face Recognized'
  ];
  
  const severities: Array<'critical' | 'high' | 'medium' | 'low'> = ['critical', 'high', 'medium', 'low'];
  const locations = ['Main Entrance', 'Parking Lot', 'Loading Dock', 'Server Room', 'Lobby', 'Corridor A'];
  const cameras = ['Camera 01', 'Camera 02', 'Camera 03', 'Camera 04', 'Camera 05'];

  const alerts: Alert[] = [];
  const now = new Date();

  for (let i = 0; i < count; i++) {
    const timestamp = new Date(now.getTime() - Math.random() * 7 * 24 * 60 * 60 * 1000);
    alerts.push({
      id: `alert-${i + 1}`,
      timestamp: timestamp.toISOString(),
      type: types[Math.floor(Math.random() * types.length)],
      severity: severities[Math.floor(Math.random() * severities.length)],
      description: `Alert ${i + 1} - ${types[Math.floor(Math.random() * types.length)]}`,
      location: locations[Math.floor(Math.random() * locations.length)],
      camera: cameras[Math.floor(Math.random() * cameras.length)]
    });
  }

  return alerts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
};

export const mockStats: Stats = {
  peopleDetected: 12,
  activeAlerts: 3,
  camerasOnline: 5,
  threatLevel: 'Medium',
  uptime: '99.8%'
};

export const generateActivityData = () => {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  return hours.map(hour => ({
    hour: `${hour.toString().padStart(2, '0')}:00`,
    people: Math.floor(Math.random() * 30) + 5,
    alerts: Math.floor(Math.random() * 10)
  }));
};

export const generateWeeklyData = () => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return days.map(day => ({
    day,
    people: Math.floor(Math.random() * 200) + 50,
    alerts: Math.floor(Math.random() * 30) + 5,
    threats: Math.floor(Math.random() * 5)
  }));
};

export const generateAlertDistribution = () => {
  return [
    { name: 'Critical', value: 5, color: '#ef4444' },
    { name: 'High', value: 12, color: '#f97316' },
    { name: 'Medium', value: 23, color: '#eab308' },
    { name: 'Low', value: 45, color: '#3b82f6' }
  ];
};

export const generateHeatmapData = () => {
  const data = [];
  for (let y = 0; y < 10; y++) {
    for (let x = 0; x < 10; x++) {
      data.push({
        x,
        y,
        value: Math.random()
      });
    }
  }
  return data;
};

export const mockZones = [
  {
    id: 'zone-1',
    name: 'Restricted Area',
    severity: 'critical',
    coordinates: { x1: 100, y1: 100, x2: 300, y2: 200 },
    color: '#ef4444'
  },
  {
    id: 'zone-2',
    name: 'High-Risk Zone',
    severity: 'high',
    coordinates: { x1: 350, y1: 150, x2: 500, y2: 300 },
    color: '#f97316'
  }
];
