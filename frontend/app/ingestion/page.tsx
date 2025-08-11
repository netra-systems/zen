'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Upload, Database, FileJson, Cloud, Server, Webhook, 
  FileText, Code, Image as ImageIcon, Video, Music, Archive,
  CheckCircle, XCircle, Clock, AlertCircle, Play, Pause, RefreshCw
} from 'lucide-react';

const IngestionPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [ingestionConfig, setIngestionConfig] = useState({
    dataSource: 'file',
    format: 'json',
    chunkSize: '1024',
    enableValidation: true,
    enableDeduplication: true,
    enableCompression: false,
    processingMode: 'batch',
  });

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  const dataSources = [
    { id: 'file', label: 'File Upload', icon: <Upload className="h-4 w-4" /> },
    { id: 'database', label: 'Database', icon: <Database className="h-4 w-4" /> },
    { id: 'api', label: 'API Endpoint', icon: <Webhook className="h-4 w-4" /> },
    { id: 'cloud', label: 'Cloud Storage', icon: <Cloud className="h-4 w-4" /> },
    { id: 'streaming', label: 'Real-time Stream', icon: <Server className="h-4 w-4" /> },
  ];

  const recentIngestions = [
    {
      id: '1',
      name: 'Training Dataset v2.3',
      source: 'S3 Bucket',
      status: 'completed',
      records: '1.2M',
      size: '4.8 GB',
      timestamp: '2 hours ago',
    },
    {
      id: '2',
      name: 'Customer Feedback Logs',
      source: 'PostgreSQL',
      status: 'processing',
      records: '450K',
      size: '892 MB',
      timestamp: '4 hours ago',
      progress: 67,
    },
    {
      id: '3',
      name: 'API Response Cache',
      source: 'Redis Stream',
      status: 'failed',
      records: '89K',
      size: '156 MB',
      timestamp: '6 hours ago',
      error: 'Schema validation failed',
    },
    {
      id: '4',
      name: 'Product Catalog Update',
      source: 'REST API',
      status: 'queued',
      records: '12K',
      size: '45 MB',
      timestamp: '8 hours ago',
    },
  ];

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setSelectedFiles(files);
  };

  const startIngestion = () => {
    setIsProcessing(true);
    setUploadProgress(0);
    
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsProcessing(false);
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'queued':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
      case 'xml':
        return <FileJson className="h-4 w-4" />;
      case 'txt':
      case 'csv':
        return <FileText className="h-4 w-4" />;
      case 'py':
      case 'js':
      case 'ts':
        return <Code className="h-4 w-4" />;
      case 'jpg':
      case 'png':
      case 'gif':
        return <ImageIcon className="h-4 w-4" />;
      case 'mp4':
      case 'avi':
        return <Video className="h-4 w-4" />;
      case 'mp3':
      case 'wav':
        return <Music className="h-4 w-4" />;
      case 'zip':
      case 'tar':
      case 'gz':
        return <Archive className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Data Ingestion</h1>
          <p className="text-muted-foreground">Import and process data from multiple sources</p>
        </div>
        <Button onClick={() => router.push('/corpus')}>
          View Corpus
          <Database className="ml-2 h-4 w-4" />
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload">New Ingestion</TabsTrigger>
          <TabsTrigger value="active">Active Jobs</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Configure Data Source</CardTitle>
              <CardDescription>Select how you want to ingest data into the system</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-5 gap-4">
                {dataSources.map((source) => (
                  <Button
                    key={source.id}
                    variant={ingestionConfig.dataSource === source.id ? 'default' : 'outline'}
                    className="h-24 flex-col gap-2"
                    onClick={() => setIngestionConfig({ ...ingestionConfig, dataSource: source.id })}
                  >
                    {source.icon}
                    <span className="text-xs">{source.label}</span>
                  </Button>
                ))}
              </div>

              {ingestionConfig.dataSource === 'file' && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="file-upload">Select Files</Label>
                    <Input
                      id="file-upload"
                      type="file"
                      multiple
                      onChange={handleFileUpload}
                      className="mt-2"
                    />
                  </div>
                  {selectedFiles.length > 0 && (
                    <div className="border rounded-lg p-4 space-y-2">
                      <p className="text-sm font-medium">Selected Files:</p>
                      {selectedFiles.map((file, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          {getFileIcon(file.name)}
                          <span>{file.name}</span>
                          <Badge variant="secondary">{(file.size / 1024 / 1024).toFixed(2)} MB</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {ingestionConfig.dataSource === 'database' && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="db-type">Database Type</Label>
                    <Select defaultValue="postgresql">
                      <SelectTrigger id="db-type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="postgresql">PostgreSQL</SelectItem>
                        <SelectItem value="mysql">MySQL</SelectItem>
                        <SelectItem value="mongodb">MongoDB</SelectItem>
                        <SelectItem value="clickhouse">ClickHouse</SelectItem>
                        <SelectItem value="redis">Redis</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="connection-string">Connection String</Label>
                    <Input
                      id="connection-string"
                      type="password"
                      placeholder="postgresql://user:password@host:port/database"
                    />
                  </div>
                  <div>
                    <Label htmlFor="query">Query / Collection</Label>
                    <Textarea
                      id="query"
                      placeholder="SELECT * FROM table_name"
                      rows={3}
                    />
                  </div>
                </div>
              )}

              {ingestionConfig.dataSource === 'api' && (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="api-url">API Endpoint</Label>
                    <Input
                      id="api-url"
                      type="url"
                      placeholder="https://api.example.com/data"
                    />
                  </div>
                  <div>
                    <Label htmlFor="auth-type">Authentication</Label>
                    <Select defaultValue="bearer">
                      <SelectTrigger id="auth-type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="bearer">Bearer Token</SelectItem>
                        <SelectItem value="apikey">API Key</SelectItem>
                        <SelectItem value="oauth2">OAuth 2.0</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="headers">Custom Headers (JSON)</Label>
                    <Textarea
                      id="headers"
                      placeholder='{"X-Custom-Header": "value"}'
                      rows={2}
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="format">Data Format</Label>
                  <Select value={ingestionConfig.format} onValueChange={(value) => setIngestionConfig({ ...ingestionConfig, format: value })}>
                    <SelectTrigger id="format">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="json">JSON</SelectItem>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="parquet">Parquet</SelectItem>
                      <SelectItem value="avro">Avro</SelectItem>
                      <SelectItem value="xml">XML</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="chunk-size">Chunk Size (KB)</Label>
                  <Input
                    id="chunk-size"
                    type="number"
                    value={ingestionConfig.chunkSize}
                    onChange={(e) => setIngestionConfig({ ...ingestionConfig, chunkSize: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="validation">Enable Schema Validation</Label>
                  <Switch
                    id="validation"
                    checked={ingestionConfig.enableValidation}
                    onCheckedChange={(checked) => setIngestionConfig({ ...ingestionConfig, enableValidation: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="deduplication">Enable Deduplication</Label>
                  <Switch
                    id="deduplication"
                    checked={ingestionConfig.enableDeduplication}
                    onCheckedChange={(checked) => setIngestionConfig({ ...ingestionConfig, enableDeduplication: checked })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="compression">Enable Compression</Label>
                  <Switch
                    id="compression"
                    checked={ingestionConfig.enableCompression}
                    onCheckedChange={(checked) => setIngestionConfig({ ...ingestionConfig, enableCompression: checked })}
                  />
                </div>
              </div>

              {isProcessing && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Processing...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}

              <div className="flex gap-4">
                <Button onClick={startIngestion} disabled={isProcessing}>
                  {isProcessing ? (
                    <>
                      <Clock className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Start Ingestion
                    </>
                  )}
                </Button>
                <Button variant="outline" disabled={isProcessing}>
                  <Pause className="mr-2 h-4 w-4" />
                  Schedule
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="active" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Active Ingestion Jobs</CardTitle>
              <CardDescription>Monitor ongoing data ingestion processes</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentIngestions
                  .filter((ing) => ing.status === 'processing')
                  .map((ingestion) => (
                    <div key={ingestion.id} className="border rounded-lg p-4 space-y-3">
                      <div className="flex justify-between items-start">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(ingestion.status)}
                            <p className="font-medium">{ingestion.name}</p>
                            <Badge variant="secondary">{ingestion.source}</Badge>
                          </div>
                          <div className="flex gap-4 text-sm text-muted-foreground">
                            <span>{ingestion.records} records</span>
                            <span>{ingestion.size}</span>
                            <span>{ingestion.timestamp}</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            <Pause className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline">
                            <XCircle className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      {ingestion.progress && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>Progress</span>
                            <span>{ingestion.progress}%</span>
                          </div>
                          <Progress value={ingestion.progress} className="h-2" />
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ingestion History</CardTitle>
              <CardDescription>View past ingestion jobs and their results</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentIngestions.map((ingestion) => (
                  <div key={ingestion.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(ingestion.status)}
                          <p className="font-medium">{ingestion.name}</p>
                          <Badge variant="secondary">{ingestion.source}</Badge>
                        </div>
                        <div className="flex gap-4 text-sm text-muted-foreground">
                          <span>{ingestion.records} records</span>
                          <span>{ingestion.size}</span>
                          <span>{ingestion.timestamp}</span>
                        </div>
                        {ingestion.error && (
                          <Alert className="mt-2">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{ingestion.error}</AlertDescription>
                          </Alert>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          View Details
                        </Button>
                        {ingestion.status === 'failed' && (
                          <Button size="sm" variant="outline">
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Retry
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ingestion Settings</CardTitle>
              <CardDescription>Configure default settings for data ingestion</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Default Processing Mode</Label>
                  <Select defaultValue="batch">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="batch">Batch Processing</SelectItem>
                      <SelectItem value="stream">Stream Processing</SelectItem>
                      <SelectItem value="micro-batch">Micro-batch</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Error Handling</Label>
                  <Select defaultValue="skip">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="skip">Skip Errors</SelectItem>
                      <SelectItem value="fail">Fail on Error</SelectItem>
                      <SelectItem value="quarantine">Quarantine Failed Records</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Max Parallel Jobs</Label>
                  <Input type="number" defaultValue="5" />
                </div>
                <div className="space-y-2">
                  <Label>Retention Period (days)</Label>
                  <Input type="number" defaultValue="30" />
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Auto-retry Failed Jobs</p>
                    <p className="text-sm text-muted-foreground">Automatically retry failed ingestion jobs</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Send Notifications</p>
                    <p className="text-sm text-muted-foreground">Get notified about ingestion status</p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Enable Monitoring</p>
                    <p className="text-sm text-muted-foreground">Track detailed metrics and performance</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
              <Button>Save Settings</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default IngestionPage;