import { useState, useCallback, useMemo, useEffect } from 'react';
import { Card, Button, Row, Col, Typography, Spin, Collapse, message } from 'antd';
import { UndoOutlined } from '@ant-design/icons';
import { useAppStore } from '../../stores/appStore';
import { gradingApi } from '../../api';
import { paramsToCssFilter, vignetteGradient } from '../../utils/canvasPreview';
import { useDebouncedCallback } from '../../hooks/useDebouncedCallback';
import ParamSliderGroup from './ParamSliderGroup';
import type { ColorParams } from '../../types';

const { Title, Text } = Typography;

const API_BASE = 'http://localhost:8000';

// Default ColorParams values
function defaultParams(): ColorParams {
  return {
    version: '1.0',
    basic: { exposure: 0, contrast: 0, highlights: 0, shadows: 0, whites: 0, blacks: 0 },
    color: { temperature: 6500, tint: 0, vibrance: 0, saturation: 0 },
    tone_curve: {
      points: [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]],
      red: null, green: null, blue: null,
    },
    hsl: {
      red: { hue: 0, saturation: 0, luminance: 0 },
      orange: { hue: 0, saturation: 0, luminance: 0 },
      yellow: { hue: 0, saturation: 0, luminance: 0 },
      green: { hue: 0, saturation: 0, luminance: 0 },
      aqua: { hue: 0, saturation: 0, luminance: 0 },
      blue: { hue: 0, saturation: 0, luminance: 0 },
      purple: { hue: 0, saturation: 0, luminance: 0 },
      magenta: { hue: 0, saturation: 0, luminance: 0 },
    },
    split_toning: {
      highlights: { hue: 0, saturation: 0 },
      shadows: { hue: 0, saturation: 0 },
      balance: 0,
    },
    effects: { clarity: 0, dehaze: 0, vignette: 0, grain: 0 },
  };
}

const BASIC_SLIDERS = [
  { key: 'exposure', label: 'Exposure', min: -3, max: 3, step: 0.1, defaultValue: 0 },
  { key: 'contrast', label: 'Contrast', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'highlights', label: 'Highlights', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'shadows', label: 'Shadows', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'whites', label: 'Whites', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'blacks', label: 'Blacks', min: -100, max: 100, step: 1, defaultValue: 0 },
];

const COLOR_SLIDERS = [
  { key: 'temperature', label: 'Temperature', min: 2000, max: 12000, step: 100, defaultValue: 6500 },
  { key: 'tint', label: 'Tint', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'vibrance', label: 'Vibrance', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, defaultValue: 0 },
];

const EFFECTS_SLIDERS = [
  { key: 'clarity', label: 'Clarity', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'dehaze', label: 'Dehaze', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'vignette', label: 'Vignette', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'grain', label: 'Grain', min: 0, max: 100, step: 1, defaultValue: 0 },
];

export default function FineTunePanel() {
  const { gradingTask, selectedSuggestion, setStep, setFinalParams } = useAppStore();
  const [params, setParams] = useState<ColorParams>(() => {
    if (selectedSuggestion?.parameters) {
      return { ...defaultParams(), ...selectedSuggestion.parameters } as ColorParams;
    }
    return defaultParams();
  });
  const [serverPreviewUrl, setServerPreviewUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const originalUrl = gradingTask?.original_image_url
    ? `${API_BASE}${gradingTask.original_image_url}`
    : null;

  // Client-side CSS filter for instant feedback
  const cssFilter = useMemo(
    () => paramsToCssFilter({ basic: params.basic, color: params.color, effects: params.effects }),
    [params.basic, params.color, params.effects],
  );

  const vignetteOverlay = useMemo(
    () => vignetteGradient(params.effects.vignette),
    [params.effects.vignette],
  );

  // Request server-side precise preview (debounced)
  const requestServerPreview = useDebouncedCallback(
    async () => {
      if (!gradingTask) return;
      setLoadingPreview(true);
      try {
        const result = await gradingApi.preview(gradingTask.id, params as unknown as Record<string, unknown>);
        setServerPreviewUrl(`${API_BASE}${result.preview_url}`);
      } catch {
        // Silent fail for preview
      } finally {
        setLoadingPreview(false);
      }
    },
    500,
  );

  useEffect(() => {
    requestServerPreview();
  }, [params, requestServerPreview]);

  const updateBasic = useCallback((key: string, value: number) => {
    setParams((prev) => ({
      ...prev,
      basic: { ...prev.basic, [key]: value },
    }));
  }, []);

  const updateColor = useCallback((key: string, value: number) => {
    setParams((prev) => ({
      ...prev,
      color: { ...prev.color, [key]: value },
    }));
  }, []);

  const updateEffects = useCallback((key: string, value: number) => {
    setParams((prev) => ({
      ...prev,
      effects: { ...prev.effects, [key]: value },
    }));
  }, []);

  const handleReset = useCallback(() => {
    if (selectedSuggestion?.parameters) {
      setParams({ ...defaultParams(), ...selectedSuggestion.parameters } as ColorParams);
    } else {
      setParams(defaultParams());
    }
    setServerPreviewUrl(null);
    message.info('Parameters reset');
  }, [selectedSuggestion]);

  const handleProceed = useCallback(() => {
    setFinalParams(params);
    setStep(3);
  }, [setStep, setFinalParams, params]);

  if (!gradingTask) {
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
        <Title level={4}>No grading task found</Title>
        <Text style={{ color: 'rgba(255,255,255,0.45)' }}>
          Please go back and create a grading task first.
        </Text>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', padding: '16px 0' }}>
      <Row gutter={24}>
        {/* Preview area */}
        <Col xs={24} lg={16}>
          <Card
            title="Preview"
            extra={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {loadingPreview && <Spin size="small" />}
                <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
                  {serverPreviewUrl ? 'Server preview' : 'CSS approximate'}
                </Text>
              </div>
            }
          >
            <div style={{ position: 'relative', width: '100%' }}>
              {serverPreviewUrl ? (
                <img
                  src={serverPreviewUrl}
                  alt="Server preview"
                  style={{
                    width: '100%',
                    maxHeight: 600,
                    objectFit: 'contain',
                    borderRadius: 8,
                  }}
                />
              ) : originalUrl ? (
                <div style={{ position: 'relative' }}>
                  <img
                    src={originalUrl}
                    alt="CSS preview"
                    style={{
                      width: '100%',
                      maxHeight: 600,
                      objectFit: 'contain',
                      borderRadius: 8,
                      filter: cssFilter,
                    }}
                  />
                  {vignetteOverlay !== 'none' && (
                    <div
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundImage: vignetteOverlay,
                        pointerEvents: 'none',
                        borderRadius: 8,
                      }}
                    />
                  )}
                </div>
              ) : (
                <div style={{ height: 400, background: '#1a1a1a', borderRadius: 8 }} />
              )}
            </div>
          </Card>
        </Col>

        {/* Parameter controls */}
        <Col xs={24} lg={8}>
          <Card
            title="Parameters"
            extra={
              <Button icon={<UndoOutlined />} size="small" onClick={handleReset}>
                Reset
              </Button>
            }
          >
            <Collapse
              defaultActiveKey={['basic', 'color', 'effects']}
              ghost
              items={[
                {
                  key: 'basic',
                  label: 'Basic',
                  children: (
                    <ParamSliderGroup
                      title=""
                      sliders={BASIC_SLIDERS}
                      values={params.basic as unknown as Record<string, number>}
                      onChange={updateBasic}
                    />
                  ),
                },
                {
                  key: 'color',
                  label: 'Color',
                  children: (
                    <ParamSliderGroup
                      title=""
                      sliders={COLOR_SLIDERS}
                      values={params.color as unknown as Record<string, number>}
                      onChange={updateColor}
                    />
                  ),
                },
                {
                  key: 'effects',
                  label: 'Effects',
                  children: (
                    <ParamSliderGroup
                      title=""
                      sliders={EFFECTS_SLIDERS}
                      values={params.effects as unknown as Record<string, number>}
                      onChange={updateEffects}
                    />
                  ),
                },
              ]}
            />

            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Button
                type="primary"
                size="large"
                onClick={handleProceed}
                block
                style={{ height: 44, borderRadius: 10, fontWeight: 600 }}
              >
                Proceed to Export
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
