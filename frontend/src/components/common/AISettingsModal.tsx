import { useState, useEffect, useCallback } from 'react';
import { Modal, Form, Input, Select, Button, Typography, message, Space } from 'antd';
import { SettingOutlined, CheckCircleFilled } from '@ant-design/icons';
import { aiApi } from '../../api';

const { Text } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AISettingsModal({ open, onClose }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentProvider, setCurrentProvider] = useState<string>('');
  const [providers, setProviders] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);

  // Fetch current provider info on open
  useEffect(() => {
    if (open) {
      aiApi.getProviders().then((data) => {
        setProviders(data.providers);
        setCurrentProvider(data.current);
        form.setFieldsValue({ provider: data.current });
      }).catch(() => {
        // ignore
      });
      setSaved(false);
    }
  }, [open, form]);

  const selectedProvider = Form.useWatch('provider', form);

  const handleSave = useCallback(async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const config: Record<string, string> = { provider: values.provider };
      if (values.api_key) config.api_key = values.api_key;
      if (values.model) config.model = values.model;
      if (values.base_url) config.base_url = values.base_url;
      await aiApi.setProvider(config);
      setCurrentProvider(values.provider);
      setSaved(true);
      message.success('AI provider configured successfully');
    } catch {
      message.error('Failed to save AI settings');
    } finally {
      setLoading(false);
    }
  }, [form]);

  return (
    <Modal
      title="AI Provider Settings"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" onClick={handleSave} loading={loading}>
            Save
          </Button>
        </Space>
      }
      width={480}
    >
      {saved && (
        <div
          style={{
            padding: '8px 12px',
            marginBottom: 16,
            borderRadius: 8,
            background: 'rgba(82, 196, 26, 0.1)',
            border: '1px solid rgba(82, 196, 26, 0.3)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckCircleFilled style={{ color: '#52c41a' }} />
          <Text style={{ color: '#52c41a', fontSize: 13 }}>
            Settings saved. You can now use AI features.
          </Text>
        </div>
      )}

      <Form form={form} layout="vertical" autoComplete="off">
        <Form.Item
          name="provider"
          label="Provider"
          rules={[{ required: true }]}
        >
          <Select
            options={providers.map((p) => ({
              value: p,
              label: p === 'claude' ? 'Claude (Anthropic)' : p === 'openai' ? 'OpenAI / Compatible' : p,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="api_key"
          label="API Key"
          rules={[{ required: true, message: 'API key is required' }]}
        >
          <Input.Password
            placeholder={
              selectedProvider === 'claude'
                ? 'sk-ant-...'
                : 'sk-...'
            }
          />
        </Form.Item>

        {selectedProvider === 'openai' && (
          <Form.Item name="base_url" label="Base URL (optional)">
            <Input placeholder="https://api.openai.com/v1 (leave empty for default)" />
          </Form.Item>
        )}

        <Form.Item name="model" label="Model (optional)">
          <Input
            placeholder={
              selectedProvider === 'claude'
                ? 'claude-sonnet-4-5-20250929'
                : 'gpt-4o'
            }
          />
        </Form.Item>
      </Form>

      <Text style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>
        API keys are stored server-side only and never sent to the frontend.
        For OpenAI-compatible APIs (DashScope, etc.), set a custom Base URL.
      </Text>
    </Modal>
  );
}
