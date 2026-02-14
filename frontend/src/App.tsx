import { useEffect, useState } from 'react';
import { Layout, Typography, Steps, Button, Space, Popconfirm, theme } from 'antd';
import { SettingOutlined, ArrowLeftOutlined, HomeOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';
import StyleDiscovery from './components/StyleDiscovery';
import GradingSuggestionPanel from './components/GradingSuggestion';
import FineTunePanel from './components/FineTune';
import ExportPanel from './components/Export';
import AISettingsModal from './components/common/AISettingsModal';
import ProfileManager from './components/common/ProfileManager';
import { useAppStore } from './stores/appStore';
import './App.css';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;

const API_BASE = 'http://localhost:8000';

const STEP_ITEMS = [
  { title: 'Style Discovery' },
  { title: 'Grading Suggestions' },
  { title: 'Fine-tune' },
  { title: 'Export' },
];

function App() {
  const [backendStatus, setBackendStatus] = useState<string>('checking...');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profilesOpen, setProfilesOpen] = useState(false);
  const { currentStep, goBack, reset } = useAppStore();
  const { token } = theme.useToken();

  useEffect(() => {
    axios
      .get(`${API_BASE}/health`)
      .then((res) => setBackendStatus(res.data.status))
      .catch(() => setBackendStatus('offline'));
  }, []);

  return (
    <Layout style={{ minHeight: '100vh', background: '#0d0d0d' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#111111',
          borderBottom: '1px solid #1f1f1f',
          padding: '0 24px',
          height: 56,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 160 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background: `linear-gradient(135deg, ${token.colorPrimary}, #8b5cf6)`,
              cursor: 'pointer',
            }}
            onClick={reset}
            title="Back to home"
          />
          <Title level={4} style={{ color: '#fff', margin: 0, fontWeight: 600 }}>
            ColorTune
          </Title>
        </div>

        <Steps
          current={currentStep}
          items={STEP_ITEMS}
          size="small"
          style={{ maxWidth: 500 }}
        />

        <Space size={4} style={{ minWidth: 280, justifyContent: 'flex-end' }}>
          {currentStep > 0 && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={goBack}
              style={{ color: 'rgba(255,255,255,0.65)' }}
            >
              Back
            </Button>
          )}
          <Popconfirm
            title="Start over?"
            description="This will reset all progress."
            onConfirm={reset}
            okText="Yes"
            cancelText="No"
          >
            <Button
              type="text"
              icon={<HomeOutlined />}
              style={{ color: 'rgba(255,255,255,0.65)' }}
            >
              Home
            </Button>
          </Popconfirm>
          <Button
            type="text"
            icon={<UserOutlined />}
            onClick={() => setProfilesOpen(true)}
            style={{ color: 'rgba(255,255,255,0.65)' }}
          >
            Profiles
          </Button>
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => setSettingsOpen(true)}
            style={{ color: 'rgba(255,255,255,0.65)' }}
          >
            AI
          </Button>
        </Space>
      </Header>

      <Content style={{ padding: '16px 24px', minHeight: 'calc(100vh - 56px - 40px)' }}>
        {currentStep === 0 && <StyleDiscovery />}
        {currentStep === 1 && <GradingSuggestionPanel />}
        {currentStep === 2 && <FineTunePanel />}
        {currentStep === 3 && <ExportPanel />}
      </Content>

      <Footer
        style={{
          textAlign: 'center',
          background: '#0d0d0d',
          borderTop: '1px solid #1f1f1f',
          padding: '10px 24px',
        }}
      >
        <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
          ColorTune &middot; Backend: {backendStatus === 'ok' ? 'Connected' : backendStatus}
        </Text>
      </Footer>

      <AISettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ProfileManager open={profilesOpen} onClose={() => setProfilesOpen(false)} />
    </Layout>
  );
}

export default App;
