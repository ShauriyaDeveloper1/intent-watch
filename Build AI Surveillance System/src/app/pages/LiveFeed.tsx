import { useState, useEffect, useRef } from 'react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
  Play, 
  Pause, 
  Upload, 
  Video, 
  Users, 
  AlertTriangle,
  Activity,
  Camera,
  Maximize
} from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { videoAPI, alertsAPI, Alert } from '../../services/api';

export function LiveFeed() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [videoSource, setVideoSource] = useState<string>('webcam');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamNonce, setStreamNonce] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamUrl = `${videoAPI.getStreamUrl()}?t=${streamNonce}`;

  // Fetch alerts periodically
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await alertsAPI.getLiveAlerts();
        setAlerts(Array.isArray(data) ? data.slice(-5) : []); // Get last 5 alerts
      } catch (error) {
        console.error('Error fetching alerts:', error);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, []);

  const handleStartStop = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (isStreaming) {
        await videoAPI.stopVideo();
        setIsStreaming(false);
      } else {
        if (videoSource === 'webcam') {
          const response = await videoAPI.startWebcam(0);
          console.log('Webcam started:', response);
        } else if (videoSource === 'file') {
          // Handled by file upload
          setIsLoading(false);
          return;
        }
        // Force browser to reconnect to the MJPEG stream
        setStreamNonce((n) => n + 1);
        setIsStreaming(true);
      }
    } catch (error: any) {
      console.error('Error toggling stream:', error);
      setError(error.message || 'Failed to start/stop stream');
      alert('Failed to start/stop stream. Make sure the backend is running on http://localhost:8000');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await videoAPI.uploadVideo(file);
      console.log('Video uploaded:', response);
      // The backend automatically sets this as the video source
      // Just start streaming
      setStreamNonce((n) => n + 1);
      setIsStreaming(true);
      setVideoSource('file');
    } catch (error) {
      console.error('Error uploading video:', error);
      alert('Failed to upload video. Make sure the backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityColor = (type: string) => {
    if (type.includes('Loiter') || type.includes('Bag')) return 'text-red-400';
    if (type.includes('Running')) return 'text-orange-400';
    return 'text-blue-400';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Live Feed</h1>
        <p className="text-muted-foreground mt-1">Real-time video surveillance with AI detection</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Feed */}
        <Card className="p-6 lg:col-span-2">
          <div className="space-y-4">
            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Select value={videoSource} onValueChange={setVideoSource}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="webcam">Webcam</SelectItem>
                    <SelectItem value="file">Upload Video File</SelectItem>
                  </SelectContent>
                </Select>
                
                <Button
                  onClick={handleStartStop}
                  disabled={isLoading}
                  className={isStreaming ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
                >
                  {isLoading ? (
                    <>Loading...</>
                  ) : isStreaming ? (
                    <>
                      <Pause className="w-4 h-4 mr-2" />
                      Stop
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Start
                    </>
                  )}
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload
                </Button>
              </div>
            </div>

            {/* Video Display */}
            <div className="relative aspect-video bg-slate-950 rounded-lg overflow-hidden border border-slate-700">
              {isStreaming ? (
                <>
                  <img
                    src={streamUrl}
                    alt="Live video stream"
                    className="w-full h-full object-contain"
                    onError={() => {
                      // Sometimes the backend resets the connection while it (re)opens the capture.
                      // Bump the querystring to force a clean reconnect.
                      setError('Stream connection lost. Reconnecting...');
                      window.setTimeout(() => setStreamNonce((n) => n + 1), 500);
                    }}
                  />
                  
                  {/* Status overlay */}
                  <div className="absolute top-4 left-4 space-y-2">
                    <Badge className="bg-red-600 text-white flex items-center gap-2">
                      <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                      LIVE
                    </Badge>
                    <div className="text-white text-sm bg-black/50 px-2 py-1 rounded backdrop-blur-sm">
                      {new Date().toLocaleTimeString()}
                    </div>
                  </div>

                  {/* Stats overlay */}
                  <div className="absolute bottom-4 left-4 flex gap-4">
                    <div className="bg-black/50 text-white text-sm px-3 py-2 rounded backdrop-blur-sm">
                      <Activity className="w-4 h-4 inline mr-2" />
                      AI Detection Active
                    </div>
                    <div className="bg-black/50 text-white text-sm px-3 py-2 rounded backdrop-blur-sm">
                      <Camera className="w-4 h-4 inline mr-2" />
                      {videoSource === 'webcam' ? 'Webcam' : 'Video File'}
                    </div>
                  </div>
                </>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
                  <div className="text-center">
                    <Video className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400 mb-2">Stream stopped</p>
                    <p className="text-slate-500 text-sm">Click Start to begin detection</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* System Status */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">System Status</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Backend</span>
                <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                  Connected
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">AI Model</span>
                <Badge className="bg-green-500/10 text-green-400 border-green-500/20">
                  YOLOv8
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Stream Status</span>
                <Badge className={isStreaming ? "bg-green-500/10 text-green-400 border-green-500/20" : "bg-slate-500/10 text-slate-400 border-slate-500/20"}>
                  {isStreaming ? 'Active' : 'Inactive'}
                </Badge>
              </div>
            </div>
          </Card>

          {/* Live Alerts */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">Live Alerts</h3>
              <Badge className="bg-red-500/10 text-red-400 border-red-500/20">
                {alerts.length}
              </Badge>
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="text-center py-8">
                  <AlertTriangle className="w-12 h-12 text-slate-600 mx-auto mb-2" />
                  <p className="text-slate-400 text-sm">No alerts yet</p>
                  <p className="text-slate-500 text-xs mt-1">Start the stream to detect events</p>
                </div>
              ) : (
                alerts.map((alert, index) => (
                  <div
                    key={index}
                    className="p-3 bg-muted/50 rounded-lg border border-border"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={`w-4 h-4 mt-0.5 ${getSeverityColor(alert.type)}`} />
                        <div>
                          <p className="text-foreground text-sm font-medium">{alert.type}</p>
                          <p className="text-muted-foreground text-xs mt-1">{alert.message}</p>
                          <p className="text-muted-foreground text-xs mt-1">{alert.time}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
