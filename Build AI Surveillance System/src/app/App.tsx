import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { LiveFeed } from './pages/LiveFeed';
import { Analytics } from './pages/Analytics';
import { AlertsLog } from './pages/AlertsLog';
import { ZoneConfig } from './pages/ZoneConfig';
import { Settings } from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/feed" element={<LiveFeed />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/alerts" element={<AlertsLog />} />
          <Route path="/zones" element={<ZoneConfig />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
