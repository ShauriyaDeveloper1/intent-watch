import { useEffect, useMemo, useState } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  AreaChart, 
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { TrendingUp, Users, AlertTriangle, Activity } from 'lucide-react';
import { Badge } from '../components/ui/badge';
import { alertsAPI, AnalyticsData } from '../../services/api';

export function Analytics() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resetToZeroAfterClick, setResetToZeroAfterClick] = useState(true);
  const [isResetting, setIsResetting] = useState(false);

  const refresh = async () => {
    try {
      setError(null);
      const data = await alertsAPI.getAnalytics();
      setAnalytics(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch analytics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();

    const interval = window.setInterval(refresh, 5000);
    const onVisibility = () => {
      if (!document.hidden) refresh();
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalAlerts = analytics?.total ?? 0;
  const counts = analytics?.counts ?? {};
  const uniqueTypes = Object.keys(counts).length;

  const topType = useMemo(() => {
    let best: { type: string; count: number } | null = null;
    for (const [type, count] of Object.entries(counts)) {
      if (!best || count > best.count) best = { type, count };
    }
    return best;
  }, [counts]);

  const weeklyData = useMemo(() => {
    const byDay = analytics?.by_day;
    if (!byDay || byDay.length === 0) return [];
    return byDay.map((d) => ({ day: d.day, alerts: d.alerts }));
  }, [analytics?.by_day]);

  const hourlyData = useMemo(() => {
    const byHour = analytics?.by_hour;
    if (!byHour || byHour.length === 0) return [];
    return byHour.map((h) => ({ hour: h.hour, alerts: h.alerts }));
  }, [analytics?.by_hour]);

  const threatTrends = useMemo(() => {
    const tt = analytics?.threat_trends;
    if (!tt || tt.length === 0) return [];
    return tt.map((d) => ({ day: d.day, running: d.Running ?? 0, loitering: d.Loitering ?? 0, bag: (d as any)['Unattended Bag'] ?? 0 }));
  }, [analytics?.threat_trends]);

  const alertDistribution = useMemo(() => {
    const sev = analytics?.severity ?? {};
    return [
      { name: 'Critical', value: sev['Critical'] ?? 0, color: '#ef4444' },
      { name: 'High', value: sev['High'] ?? 0, color: '#f97316' },
      { name: 'Medium', value: sev['Medium'] ?? 0, color: '#eab308' },
      { name: 'Low', value: sev['Low'] ?? 0, color: '#3b82f6' }
    ];
  }, [analytics?.severity]);

  const topTypes = useMemo(() => {
    return Object.entries(counts)
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [counts]);

  const handleResetAnalytics = async () => {
    setIsResetting(true);
    try {
      setError(null);
      await alertsAPI.clearAlerts();

      if (resetToZeroAfterClick) {
        setAnalytics({
          total: 0,
          counts: {},
          severity: { Critical: 0, High: 0, Medium: 0, Low: 0 },
          by_day: [],
          by_hour: [],
          threat_trends: [],
          recent: [],
        });
        setIsLoading(false);
      } else {
        await refresh();
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to reset analytics');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Analytics</h1>
          <p className="text-muted-foreground mt-1">Historical data and trend analysis</p>
          {error && (
            <p className="text-sm text-red-400 mt-2">{error}</p>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Checkbox
              id="reset-to-zero"
              checked={resetToZeroAfterClick}
              onCheckedChange={(v) => setResetToZeroAfterClick(Boolean(v))}
            />
            <label htmlFor="reset-to-zero" className="text-sm text-slate-300 select-none">
              Reset view to zero after click
            </label>
          </div>

          <Button
            onClick={handleResetAnalytics}
            disabled={isResetting}
            variant="destructive"
            className="bg-red-600 hover:bg-red-700"
          >
            {isResetting ? 'Resetting…' : 'Reset Analytics'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Unique Alert Types (7d)</p>
              <p className="text-3xl font-bold text-foreground mt-2">{isLoading ? '—' : uniqueTypes}</p>
              <div className="flex items-center gap-1 mt-2">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400">Live from backend</span>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-purple-600">
              <Users className="w-6 h-6 text-white" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Total Alerts (7d)</p>
              <p className="text-3xl font-bold text-foreground mt-2">{isLoading ? '—' : totalAlerts}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                  {topType ? `${topType.type}: ${topType.count}` : 'No alerts'}
                </Badge>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-red-600">
              <AlertTriangle className="w-6 h-6 text-white" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Threat Alerts (7d)</p>
              <p className="text-3xl font-bold text-foreground mt-2">
                {isLoading
                  ? '—'
                  : (counts['Running'] ?? 0) + (counts['Loitering'] ?? 0) + (counts['Unattended Bag'] ?? 0)}
              </p>
              <div className="flex items-center gap-1 mt-2">
                <TrendingUp className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400">Auto-refresh every 5s</span>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-blue-600">
              <Activity className="w-6 h-6 text-white" />
            </div>
          </div>
        </Card>
      </div>

      {/* Charts Tabs */}
      <Tabs defaultValue="weekly" className="space-y-6">
        <TabsList className="bg-card border border-border">
          <TabsTrigger value="weekly" className="data-[state=active]:bg-purple-600">
            Weekly Overview
          </TabsTrigger>
          <TabsTrigger value="hourly" className="data-[state=active]:bg-purple-600">
            24-Hour Activity
          </TabsTrigger>
          <TabsTrigger value="threats" className="data-[state=active]:bg-purple-600">
            Threat Trends
          </TabsTrigger>
        </TabsList>

        <TabsContent value="weekly" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Weekly Alert Volume</h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--foreground)'
                  }}
                />
                <Legend />
                <Bar dataKey="alerts" fill="#ef4444" name="Alerts" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="hourly" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Last 24 Hours</h3>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="hour" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--foreground)'
                  }}
                />
                <Legend />
                <Area type="monotone" dataKey="alerts" stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} name="Alerts" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="threats" className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Threat Pattern Analysis (7d)</h3>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={threatTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--foreground)'
                  }}
                />
                <Legend />
                <Line type="monotone" dataKey="bag" stroke="#ef4444" strokeWidth={2} name="Unattended Bag" />
                <Line type="monotone" dataKey="running" stroke="#f97316" strokeWidth={2} name="Running" />
                <Line type="monotone" dataKey="loitering" stroke="#eab308" strokeWidth={2} name="Loitering" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Additional Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Location Stats */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Top Alert Types</h3>
          <div className="space-y-3">
            {topTypes.length === 0 ? (
              <div className="text-slate-400 text-sm">No alerts recorded yet.</div>
            ) : topTypes.map((stat, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 bg-muted/50 rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-foreground font-medium">{stat.type}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 text-sm">{stat.count} alerts</span>
                    </div>
                  </div>
                  <div className="bg-muted rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full"
                      style={{ width: `${totalAlerts > 0 ? (stat.count / totalAlerts) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Alert Severity Distribution */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Alert Severity Breakdown</h3>
          <div className="flex items-center justify-center">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={alertDistribution.filter((d) => (d?.value ?? 0) > 0)}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {alertDistribution.filter((d) => (d?.value ?? 0) > 0).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Legend verticalAlign="middle" align="right" layout="vertical" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--popover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--foreground)'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            {alertDistribution.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-slate-400">{item.name}: {item.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
