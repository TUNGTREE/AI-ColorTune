import { useState, useEffect, useCallback } from 'react';
import { Button, Input, Typography, Tooltip } from 'antd';
import { EditOutlined, UndoOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { TextArea } = Input;

interface PromptEditorProps {
  /** Label shown in the toggle button */
  label: string;
  /** Function to load the default prompt template */
  loadTemplate: () => Promise<{ template: string; variables: string[]; schema_value: string }>;
  /** Callback when user changes the prompt; null means use default */
  onChange: (customPrompt: string | null) => void;
}

export default function PromptEditor({ label, loadTemplate, onChange }: PromptEditorProps) {
  const [expanded, setExpanded] = useState(false);
  const [defaultTemplate, setDefaultTemplate] = useState<string>('');
  const [editedPrompt, setEditedPrompt] = useState<string>('');
  const [isModified, setIsModified] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    try {
      const data = await loadTemplate();
      setDefaultTemplate(data.template);
      if (!isModified) {
        setEditedPrompt(data.template);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [loadTemplate, isModified]);

  useEffect(() => {
    if (expanded && !defaultTemplate) {
      fetchTemplate();
    }
  }, [expanded, defaultTemplate, fetchTemplate]);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const handleChange = (value: string) => {
    setEditedPrompt(value);
    const modified = value !== defaultTemplate;
    setIsModified(modified);
    onChange(modified ? value : null);
  };

  const handleReset = () => {
    setEditedPrompt(defaultTemplate);
    setIsModified(false);
    onChange(null);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button
          type="text"
          size="small"
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
          onClick={handleToggle}
          style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12, padding: '2px 8px' }}
        >
          <EditOutlined style={{ marginRight: 4 }} />
          {label}
          {isModified && (
            <span style={{ color: '#faad14', marginLeft: 6 }}>(modified)</span>
          )}
        </Button>
        {expanded && isModified && (
          <Tooltip title="Reset to default prompt">
            <Button
              type="text"
              size="small"
              icon={<UndoOutlined />}
              onClick={handleReset}
              style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}
            >
              Reset
            </Button>
          </Tooltip>
        )}
      </div>

      {expanded && (
        <div style={{ marginTop: 8 }}>
          <Text
            style={{
              color: 'rgba(255,255,255,0.35)',
              fontSize: 11,
              display: 'block',
              marginBottom: 6,
            }}
          >
            Edit the prompt sent to AI. Variables like {'{num_styles}'}, {'{scene_info}'}, {'{schema}'} will be filled automatically.
          </Text>
          <TextArea
            value={editedPrompt}
            onChange={(e) => handleChange(e.target.value)}
            loading={loading}
            autoSize={{ minRows: 6, maxRows: 20 }}
            style={{
              background: '#141414',
              border: '1px solid #2a2a2a',
              color: 'rgba(255,255,255,0.85)',
              fontFamily: 'monospace',
              fontSize: 12,
            }}
          />
        </div>
      )}
    </div>
  );
}
