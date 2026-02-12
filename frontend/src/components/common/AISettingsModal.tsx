import { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Typography,
  message,
  Space,
  Divider,
  Tag,
  Popconfirm,
} from 'antd';
import {
  CheckCircleFilled,
  SaveOutlined,
  DeleteOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { aiApi } from '../../api';

const { Text } = Typography;

const PRESETS_STORAGE_KEY = 'colortune_ai_presets';

interface AIPreset {
  name: string;
  provider: string;
  api_key: string;
  model: string;
  base_url: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

function loadPresets(): AIPreset[] {
  try {
    const raw = localStorage.getItem(PRESETS_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return [];
}

function savePresets(presets: AIPreset[]) {
  localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(presets));
}

export default function AISettingsModal({ open, onClose }: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [providerLabels, setProviderLabels] = useState<Record<string, string>>({});
  const [defaultModels, setDefaultModels] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [apiKeyMasked, setApiKeyMasked] = useState('');
  const [apiKeySet, setApiKeySet] = useState(false);
  const [presets, setPresets] = useState<AIPreset[]>(loadPresets);
  const [presetName, setPresetName] = useState('');

  // Fetch current provider info on open
  useEffect(() => {
    if (open) {
      aiApi
        .getProviders()
        .then((data) => {
          setProviders(data.providers);
          setProviderLabels(data.provider_labels || {});
          setDefaultModels(data.default_models || {});
          setApiKeyMasked(data.api_key_masked);
          setApiKeySet(data.api_key_set);
          form.setFieldsValue({
            provider: data.current,
            model: data.model || undefined,
            base_url: data.base_url || undefined,
            api_key: undefined, // Don't fill in the actual key
          });
        })
        .catch(() => {
          // ignore
        });
      setSaved(false);
    }
  }, [open, form]);

  const selectedProvider = Form.useWatch('provider', form);

  // Whether the selected provider uses base_url
  const showBaseUrl = selectedProvider && selectedProvider !== 'claude';

  const handleSave = useCallback(async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const config: Record<string, string> = { provider: values.provider };
      if (values.api_key) config.api_key = values.api_key;
      if (values.model) config.model = values.model;
      if (values.base_url !== undefined) config.base_url = values.base_url || '';
      await aiApi.setProvider(config);
      setSaved(true);
      // Refresh masked key
      const data = await aiApi.getProviders();
      setApiKeyMasked(data.api_key_masked);
      setApiKeySet(data.api_key_set);
      form.setFieldsValue({ api_key: undefined });
      message.success('AI provider configured successfully');
    } catch {
      message.error('Failed to save AI settings');
    } finally {
      setLoading(false);
    }
  }, [form]);

  // --- Preset management ---
  const handleSavePreset = useCallback(() => {
    const name = presetName.trim();
    if (!name) {
      message.warning('Please enter a preset name');
      return;
    }
    const values = form.getFieldsValue();
    const preset: AIPreset = {
      name,
      provider: values.provider || '',
      api_key: values.api_key || '',
      model: values.model || '',
      base_url: values.base_url || '',
    };
    const updated = presets.filter((p) => p.name !== name);
    updated.push(preset);
    setPresets(updated);
    savePresets(updated);
    setPresetName('');
    message.success(`Preset "${name}" saved`);
  }, [form, presetName, presets]);

  const handleLoadPreset = useCallback(
    async (preset: AIPreset) => {
      form.setFieldsValue({
        provider: preset.provider,
        api_key: preset.api_key || undefined,
        model: preset.model || undefined,
        base_url: preset.base_url || undefined,
      });
      // Auto-apply the preset to backend
      setLoading(true);
      try {
        const config: Record<string, string> = { provider: preset.provider };
        if (preset.api_key) config.api_key = preset.api_key;
        if (preset.model) config.model = preset.model;
        if (preset.base_url !== undefined) config.base_url = preset.base_url || '';
        await aiApi.setProvider(config);
        setSaved(true);
        const data = await aiApi.getProviders();
        setApiKeyMasked(data.api_key_masked);
        setApiKeySet(data.api_key_set);
        form.setFieldsValue({ api_key: undefined });
        message.success(`Switched to "${preset.name}"`);
      } catch {
        message.error('Failed to apply preset');
      } finally {
        setLoading(false);
      }
    },
    [form],
  );

  const handleDeletePreset = useCallback(
    (name: string) => {
      const updated = presets.filter((p) => p.name !== name);
      setPresets(updated);
      savePresets(updated);
      message.success(`Preset "${name}" deleted`);
    },
    [presets],
  );

  // Get placeholder for model field based on selected provider
  const modelPlaceholder = selectedProvider
    ? defaultModels[selectedProvider] || 'model name'
    : 'model name';

  // Get placeholder for API key based on provider
  const apiKeyPlaceholder = apiKeySet
    ? 'Leave empty to keep current key'
    : selectedProvider === 'claude'
      ? 'sk-ant-...'
      : selectedProvider === 'deepseek'
        ? 'sk-...'
        : selectedProvider === 'glm'
          ? 'your-zhipuai-key'
          : 'sk-...';

  return (
    <Modal
      title="AI Provider Settings"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" onClick={handleSave} loading={loading}>
            Apply
          </Button>
        </Space>
      }
      width={520}
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

      {/* Quick presets */}
      {presets.length > 0 && (
        <>
          <Text
            style={{
              color: 'rgba(255,255,255,0.45)',
              fontSize: 12,
              display: 'block',
              marginBottom: 8,
            }}
          >
            Quick Switch Presets
          </Text>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              marginBottom: 16,
            }}
          >
            {presets.map((p) => (
              <Tag
                key={p.name}
                style={{
                  cursor: 'pointer',
                  background: '#2a2a2a',
                  border: '1px solid #3a3a3a',
                  borderRadius: 8,
                  padding: '4px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
                onClick={() => handleLoadPreset(p)}
              >
                <SwapOutlined style={{ fontSize: 11 }} />
                <span>{p.name}</span>
                <Text
                  style={{
                    color: 'rgba(255,255,255,0.3)',
                    fontSize: 11,
                    marginLeft: 2,
                  }}
                >
                  ({providerLabels[p.provider] || p.provider}
                  {p.model ? ` / ${p.model}` : ''})
                </Text>
                <Popconfirm
                  title={`Delete preset "${p.name}"?`}
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    handleDeletePreset(p.name);
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                  okText="Yes"
                  cancelText="No"
                >
                  <DeleteOutlined
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      fontSize: 11,
                      color: 'rgba(255,255,255,0.25)',
                      marginLeft: 4,
                    }}
                  />
                </Popconfirm>
              </Tag>
            ))}
          </div>
          <Divider style={{ margin: '0 0 16px' }} />
        </>
      )}

      <Form form={form} layout="vertical" autoComplete="off">
        <Form.Item name="provider" label="Provider" rules={[{ required: true }]}>
          <Select
            options={providers.map((p) => ({
              value: p,
              label: providerLabels[p] || p,
            }))}
          />
        </Form.Item>

        <Form.Item
          name="api_key"
          label={
            <span>
              API Key{' '}
              {apiKeySet && (
                <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                  (current: {apiKeyMasked})
                </Text>
              )}
            </span>
          }
          rules={[
            {
              validator: (_, value) => {
                if (!value && !apiKeySet) {
                  return Promise.reject('API key is required');
                }
                return Promise.resolve();
              },
            },
          ]}
        >
          <Input.Password placeholder={apiKeyPlaceholder} />
        </Form.Item>

        {showBaseUrl && (
          <Form.Item name="base_url" label="Base URL (optional)">
            <Input
              placeholder={
                selectedProvider === 'deepseek'
                  ? 'https://api.deepseek.com (default)'
                  : selectedProvider === 'glm'
                    ? 'https://open.bigmodel.cn/api/paas/v4 (default)'
                    : 'https://api.openai.com/v1 (leave empty for default)'
              }
            />
          </Form.Item>
        )}

        <Form.Item name="model" label="Model (optional)">
          <Input placeholder={modelPlaceholder} />
        </Form.Item>
      </Form>

      {/* Save as preset */}
      <Divider style={{ margin: '8px 0 16px' }} />
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Input
          size="small"
          placeholder="Preset name (e.g. DeepSeek-V3)"
          value={presetName}
          onChange={(e) => setPresetName(e.target.value)}
          onPressEnter={handleSavePreset}
          style={{ flex: 1 }}
        />
        <Button
          size="small"
          icon={<SaveOutlined />}
          onClick={handleSavePreset}
          disabled={!presetName.trim()}
        >
          Save Preset
        </Button>
      </div>

      <Text
        style={{
          color: 'rgba(255,255,255,0.3)',
          fontSize: 11,
          display: 'block',
          marginTop: 12,
        }}
      >
        Presets are stored in your browser. API keys in presets are stored locally
        and sent to the server when applied.
      </Text>
    </Modal>
  );
}
