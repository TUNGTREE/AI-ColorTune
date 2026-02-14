import { useState, useCallback, useRef } from 'react';
import {
  Card,
  Upload,
  Button,
  Row,
  Col,
  Typography,
  Spin,
  message,
  theme,
} from 'antd';
import { UploadOutlined, CheckCircleFilled, ReloadOutlined } from '@ant-design/icons';
import { gradingApi, styleApi } from '../../api';
import { useAppStore } from '../../stores/appStore';
import BeforeAfterSlider from './BeforeAfterSlider';
import PromptEditor from '../common/PromptEditor';
import type { GradingSuggestion } from '../../types';

const { Title, Text, Paragraph } = Typography;

const API_BASE = 'http://localhost:8000';

export default function GradingSuggestionPanel() {
  const { session, profile, setGradingTask, setSelectedSuggestion, setStep } =
    useAppStore();
  const { token } = theme.useToken();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<GradingSuggestion[]>([]);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [compareSuggestion, setCompareSuggestion] =
    useState<GradingSuggestion | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const customPromptRef = useRef<string | null>(null);

  const userId = session?.user_id;

  // Upload image and create grading task
  const handleUpload = useCallback(
    async (file: File) => {
      if (!userId) {
        message.error('No user session found. Please complete style discovery first.');
        return;
      }
      setUploading(true);
      try {
        const task = await gradingApi.createTask(
          userId,
          file,
          profile?.id,
        );
        setTaskId(task.id);
        setOriginalUrl(task.original_image_url);
        setGradingTask(task);
        message.success('Image uploaded! Generating suggestions...');

        // Auto-generate suggestions
        setGenerating(true);
        const sugs = await gradingApi.generateSuggestions(task.id, 3, customPromptRef.current || undefined);
        setSuggestions(sugs);
        message.success(`Generated ${sugs.length} suggestions`);
      } catch {
        message.error('Failed to upload or generate suggestions');
      } finally {
        setUploading(false);
        setGenerating(false);
      }
    },
    [userId, profile, setGradingTask],
  );

  // Select a suggestion and move to fine-tune
  const handleSelect = useCallback(
    async (suggestion: GradingSuggestion) => {
      try {
        const result = await gradingApi.selectSuggestion(suggestion.id);
        setSuggestions((prev) =>
          prev.map((s) => ({
            ...s,
            is_selected: s.id === result.id,
          })),
        );
        setSelectedSuggestion(result);
        message.success(`Selected "${result.suggestion_name}"`);
      } catch {
        message.error('Failed to select suggestion');
      }
    },
    [setSelectedSuggestion],
  );

  const handleProceed = useCallback(() => {
    setStep(2);
  }, [setStep]);

  // Regenerate suggestions
  const handleRegenerate = useCallback(async () => {
    if (!taskId) return;
    setRegenerating(true);
    setCompareSuggestion(null);
    try {
      const sugs = await gradingApi.regenerateSuggestions(taskId, 3, customPromptRef.current || undefined);
      setSuggestions(sugs);
      message.success(`Generated ${sugs.length} new suggestions`);
    } catch {
      message.error('Failed to regenerate suggestions');
    } finally {
      setRegenerating(false);
    }
  }, [taskId]);

  const hasSelection = suggestions.some((s) => s.is_selected);

  // --- No task yet: show upload prompt ---
  if (!taskId) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 400,
          gap: 16,
        }}
      >
        <Title level={3}>Get Grading Suggestions</Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.45)', maxWidth: 500, textAlign: 'center' }}>
          Upload the photo you want to color grade. Based on your style profile,
          we'll generate personalized grading suggestions for you to choose from.
        </Paragraph>
        {profile && (
          <Text style={{ color: token.colorPrimary }}>
            Style profile loaded
          </Text>
        )}
        <PromptEditor
          label="Edit grading prompt"
          loadTemplate={styleApi.getGradingSuggestionsPromptTemplate}
          onChange={(p) => { customPromptRef.current = p; }}
        />
        <Upload
          accept="image/*"
          showUploadList={false}
          beforeUpload={(file) => {
            handleUpload(file as unknown as File);
            return false;
          }}
        >
          <Button
            icon={<UploadOutlined />}
            type="primary"
            size="large"
            loading={uploading}
            style={{ height: 48, paddingInline: 32, borderRadius: 12 }}
          >
            Upload Photo for Grading
          </Button>
        </Upload>
      </div>
    );
  }

  // --- Generating suggestions ---
  if (generating || regenerating) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 400,
          gap: 16,
        }}
      >
        <Spin size="large" />
        <Text style={{ color: 'rgba(255,255,255,0.45)' }}>
          {regenerating
            ? 'Regenerating suggestions with new variations...'
            : 'Analyzing your photo and generating personalized suggestions...'}
        </Text>
      </div>
    );
  }

  // --- Show suggestions ---
  return (
    <div style={{ width: '100%', padding: '16px 0' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 8 }}>
          Choose a Grading Style
        </Title>
        {!hasSelection && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRegenerate}
            type="text"
            style={{ color: 'rgba(255,255,255,0.45)' }}
          >
            Not satisfied? Regenerate suggestions
          </Button>
        )}
      </div>

      {/* Prompt editor for regeneration */}
      {!hasSelection && (
        <PromptEditor
          label="Edit grading prompt"
          loadTemplate={styleApi.getGradingSuggestionsPromptTemplate}
          onChange={(p) => { customPromptRef.current = p; }}
        />
      )}

      {/* Before/After comparison */}
      {compareSuggestion && originalUrl && (
        <Card
          title={`Comparing: ${compareSuggestion.suggestion_name}`}
          extra={
            <Button onClick={() => setCompareSuggestion(null)} size="small">
              Close
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          <BeforeAfterSlider
            beforeSrc={`${API_BASE}${originalUrl}`}
            afterSrc={
              compareSuggestion.preview_url
                ? `${API_BASE}${compareSuggestion.preview_url}`
                : `${API_BASE}${originalUrl}`
            }
            height={500}
          />
        </Card>
      )}

      {/* Suggestion cards */}
      <Row gutter={[16, 16]}>
        {suggestions.map((s) => (
          <Col xs={24} sm={12} md={8} key={s.id}>
            <div
              style={{
                borderRadius: 12,
                overflow: 'hidden',
                background: '#1a1a1a',
                border: s.is_selected
                  ? `3px solid ${token.colorPrimary}`
                  : '3px solid transparent',
                opacity: hasSelection && !s.is_selected ? 0.6 : 1,
                transition: 'all 0.3s ease',
              }}
            >
              {s.preview_url ? (
                <img
                  alt={s.suggestion_name}
                  src={`${API_BASE}${s.preview_url}`}
                  style={{
                    width: '100%',
                    height: 280,
                    objectFit: 'cover',
                    cursor: 'pointer',
                    display: 'block',
                  }}
                  onClick={() => setCompareSuggestion(s)}
                />
              ) : (
                <div style={{ height: 280, background: '#1a1a1a' }} />
              )}
              <div style={{ padding: '12px 16px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 8,
                  }}
                >
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.85)',
                      fontSize: 14,
                      fontWeight: 500,
                    }}
                  >
                    {s.suggestion_name}
                    {s.is_selected && (
                      <CheckCircleFilled
                        style={{ color: token.colorPrimary, marginLeft: 8 }}
                      />
                    )}
                  </Text>
                </div>
                {s.description && (
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.45)',
                      fontSize: 12,
                      display: 'block',
                      marginBottom: 8,
                    }}
                  >
                    {s.description}
                  </Text>
                )}
                <div style={{ display: 'flex', gap: 8 }}>
                  <Button
                    size="small"
                    onClick={() => setCompareSuggestion(s)}
                    style={{ flex: 1 }}
                  >
                    Compare
                  </Button>
                  <Button
                    size="small"
                    type={s.is_selected ? 'primary' : 'default'}
                    onClick={() => handleSelect(s)}
                    disabled={hasSelection && !s.is_selected}
                    style={{ flex: 1 }}
                  >
                    {s.is_selected ? 'Selected' : 'Select'}
                  </Button>
                </div>
              </div>
            </div>
          </Col>
        ))}
      </Row>

      {/* Original image reference */}
      {originalUrl && !compareSuggestion && (
        <Card title="Original Image" style={{ marginTop: 24 }}>
          <img
            src={`${API_BASE}${originalUrl}`}
            alt="Original"
            style={{ maxWidth: '100%', maxHeight: 300, objectFit: 'contain' }}
          />
        </Card>
      )}

      {/* Proceed button */}
      {hasSelection && (
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Button
            type="primary"
            size="large"
            onClick={handleProceed}
            style={{
              height: 48,
              paddingInline: 32,
              borderRadius: 12,
              fontWeight: 600,
            }}
          >
            Proceed to Fine-tune
          </Button>
        </div>
      )}
    </div>
  );
}
