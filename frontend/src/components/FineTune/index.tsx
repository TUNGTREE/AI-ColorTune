import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Card, Button, Row, Col, Typography, Spin, Collapse, message, Slider, Segmented, Tooltip } from 'antd';
import {
  UndoOutlined,
  BorderOutlined,
  RadiusSettingOutlined,
  DeleteOutlined,
  SelectOutlined,
} from '@ant-design/icons';
import { useAppStore } from '../../stores/appStore';
import { gradingApi } from '../../api';
import { paramsToCssFilter, vignetteGradient } from '../../utils/canvasPreview';
import { useDebouncedCallback } from '../../hooks/useDebouncedCallback';
import ParamSliderGroup from './ParamSliderGroup';
import SelectionOverlay from './SelectionOverlay';
import type { ColorParams, SelectionRegion, LocalAdjustment } from '../../types';

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
      midtones: { hue: 0, saturation: 0 },
      shadows: { hue: 0, saturation: 0 },
      balance: 0,
    },
    effects: { clarity: 0, dehaze: 0, vignette: 0, grain: 0, texture: 0, fade: 0, sharpening: 0, sharpen_radius: 1.0 },
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
  { key: 'texture', label: 'Texture', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'dehaze', label: 'Dehaze', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'fade', label: 'Fade', min: 0, max: 100, step: 1, defaultValue: 0 },
  { key: 'sharpening', label: 'Sharpening', min: 0, max: 100, step: 1, defaultValue: 0 },
  { key: 'sharpen_radius', label: 'Sharp Radius', min: 0.5, max: 5, step: 0.1, defaultValue: 1.0 },
  { key: 'vignette', label: 'Vignette', min: -100, max: 100, step: 1, defaultValue: 0 },
  { key: 'grain', label: 'Grain', min: 0, max: 100, step: 1, defaultValue: 0 },
];

const HSL_COLORS = ['red', 'orange', 'yellow', 'green', 'aqua', 'blue', 'purple', 'magenta'] as const;

const HSL_COLOR_LABELS: Record<string, string> = {
  red: 'Red', orange: 'Orange', yellow: 'Yellow', green: 'Green',
  aqua: 'Aqua', blue: 'Blue', purple: 'Purple', magenta: 'Magenta',
};

const HSL_DOT_COLORS: Record<string, string> = {
  red: '#e74c3c', orange: '#e67e22', yellow: '#f1c40f', green: '#2ecc71',
  aqua: '#1abc9c', blue: '#3498db', purple: '#9b59b6', magenta: '#e84393',
};

export default function FineTunePanel() {
  const { gradingTask, selectedSuggestion, setStep, setFinalParams } = useAppStore();
  const [params, setParams] = useState<ColorParams>(() => {
    if (selectedSuggestion?.parameters) {
      return mergeParams(defaultParams(), selectedSuggestion.parameters);
    }
    return defaultParams();
  });
  const [serverPreviewUrl, setServerPreviewUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [hslColor, setHslColor] = useState<string>('red');

  // Local adjustment state
  const [selectionTool, setSelectionTool] = useState<'rect' | 'ellipse' | null>(null);
  const [localAdjustments, setLocalAdjustments] = useState<LocalAdjustment[]>([]);
  const [activeLocalIndex, setActiveLocalIndex] = useState<number | null>(null);
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const [previewSize, setPreviewSize] = useState({ width: 800, height: 600 });

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

  // Request server-side precise preview (debounced - reduced to 150ms for smoother feel)
  const requestServerPreview = useDebouncedCallback(
    async () => {
      if (!gradingTask) return;
      setLoadingPreview(true);
      try {
        const localAdj = localAdjustments.length > 0
          ? localAdjustments.map((a) => ({
              region: a.region as unknown as Record<string, unknown>,
              parameters: a.parameters as unknown as Record<string, unknown>,
            }))
          : undefined;
        const result = await gradingApi.preview(
          gradingTask.id,
          params as unknown as Record<string, unknown>,
          localAdj,
        );
        setServerPreviewUrl(`${API_BASE}${result.preview_url}`);
      } catch {
        // Silent fail for preview
      } finally {
        setLoadingPreview(false);
      }
    },
    150,
  );

  useEffect(() => {
    // Clear server preview so CSS preview takes over instantly on param change
    setServerPreviewUrl(null);
    requestServerPreview();
  }, [params, localAdjustments, requestServerPreview]);

  // Measure preview container for selection overlay sizing
  useEffect(() => {
    const container = previewContainerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setPreviewSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

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

  const updateHsl = useCallback((colorName: string, key: string, value: number) => {
    setParams((prev) => ({
      ...prev,
      hsl: {
        ...prev.hsl,
        [colorName]: { ...prev.hsl[colorName], [key]: value },
      },
    }));
  }, []);

  const updateSplitToning = useCallback((channel: string, key: string, value: number) => {
    setParams((prev) => ({
      ...prev,
      split_toning: {
        ...prev.split_toning,
        [channel]: {
          ...(prev.split_toning as Record<string, unknown>)[channel] as Record<string, number>,
          [key]: value,
        },
      },
    }));
  }, []);

  const updateSplitToningBalance = useCallback((value: number) => {
    setParams((prev) => ({
      ...prev,
      split_toning: { ...prev.split_toning, balance: value },
    }));
  }, []);

  // Local adjustment handlers
  const handleRegionAdd = useCallback((region: SelectionRegion) => {
    const newAdj: LocalAdjustment = {
      id: `local_${Date.now()}`,
      region,
      parameters: {
        basic: { exposure: 0, contrast: 0, highlights: 0, shadows: 0, whites: 0, blacks: 0 },
        color: { temperature: 6500, tint: 0, vibrance: 0, saturation: 0 },
      },
    };
    setLocalAdjustments((prev) => [...prev, newAdj]);
    setActiveLocalIndex(localAdjustments.length);
    setSelectionTool(null); // Deactivate tool after drawing
  }, [localAdjustments.length]);

  const handleRegionUpdate = useCallback((index: number, region: SelectionRegion) => {
    setLocalAdjustments((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], region };
      return next;
    });
  }, []);

  const handleDeleteLocal = useCallback((index: number) => {
    setLocalAdjustments((prev) => prev.filter((_, i) => i !== index));
    setActiveLocalIndex(null);
  }, []);

  const updateLocalParam = useCallback((index: number, group: string, key: string, value: number) => {
    setLocalAdjustments((prev) => {
      const next = [...prev];
      const adj = next[index];
      const groupObj = (adj.parameters as Record<string, Record<string, number>>)[group] || {};
      next[index] = {
        ...adj,
        parameters: {
          ...adj.parameters,
          [group]: { ...groupObj, [key]: value },
        },
      };
      return next;
    });
  }, []);

  const handleReset = useCallback(() => {
    if (selectedSuggestion?.parameters) {
      setParams(mergeParams(defaultParams(), selectedSuggestion.parameters));
    } else {
      setParams(defaultParams());
    }
    setServerPreviewUrl(null);
    setLocalAdjustments([]);
    setActiveLocalIndex(null);
    message.info('Parameters reset');
  }, [selectedSuggestion]);

  const handleProceed = useCallback(() => {
    setFinalParams(params, localAdjustments);
    setStep(3);
  }, [setStep, setFinalParams, params, localAdjustments]);

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

  const activeLocal = activeLocalIndex !== null ? localAdjustments[activeLocalIndex] : null;

  return (
    <div style={{ width: '100%', padding: '16px 0' }}>
      <Row gutter={24}>
        {/* Preview area */}
        <Col xs={24} lg={16}>
          <Card
            title="Preview"
            extra={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Selection tools */}
                <Tooltip title="Rectangle selection">
                  <Button
                    size="small"
                    type={selectionTool === 'rect' ? 'primary' : 'default'}
                    icon={<BorderOutlined />}
                    onClick={() => setSelectionTool(selectionTool === 'rect' ? null : 'rect')}
                  />
                </Tooltip>
                <Tooltip title="Ellipse selection">
                  <Button
                    size="small"
                    type={selectionTool === 'ellipse' ? 'primary' : 'default'}
                    icon={<RadiusSettingOutlined />}
                    onClick={() => setSelectionTool(selectionTool === 'ellipse' ? null : 'ellipse')}
                  />
                </Tooltip>
                {localAdjustments.length > 0 && (
                  <Tooltip title="Deselect region">
                    <Button
                      size="small"
                      icon={<SelectOutlined />}
                      onClick={() => {
                        setActiveLocalIndex(null);
                        setSelectionTool(null);
                      }}
                    />
                  </Tooltip>
                )}
                <div style={{ width: 1, height: 20, background: '#333', margin: '0 4px' }} />
                {loadingPreview && <Spin size="small" />}
                <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
                  {serverPreviewUrl ? 'Server preview' : 'CSS approximate'}
                </Text>
              </div>
            }
          >
            <div
              ref={previewContainerRef}
              style={{ position: 'relative', width: '100%' }}
            >
              {serverPreviewUrl ? (
                <img
                  src={serverPreviewUrl}
                  alt="Server preview"
                  style={{
                    width: '100%',
                    maxHeight: 600,
                    objectFit: 'contain',
                    borderRadius: 8,
                    transition: 'opacity 0.15s ease',
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
                      transition: 'filter 0.1s ease-out',
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
                        transition: 'background-image 0.1s ease-out',
                      }}
                    />
                  )}
                </div>
              ) : (
                <div style={{ height: 400, background: '#1a1a1a', borderRadius: 8 }} />
              )}
              {/* Selection overlay */}
              <SelectionOverlay
                width={previewSize.width}
                height={previewSize.height}
                tool={selectionTool}
                regions={localAdjustments.map((a) => a.region)}
                activeRegionIndex={activeLocalIndex}
                onRegionAdd={handleRegionAdd}
                onRegionUpdate={handleRegionUpdate}
                onRegionSelect={setActiveLocalIndex}
              />
            </div>
          </Card>
        </Col>

        {/* Parameter controls */}
        <Col xs={24} lg={8}>
          <Card
            title={activeLocal ? `Local Adjustment ${activeLocalIndex! + 1}` : 'Parameters'}
            extra={
              <div style={{ display: 'flex', gap: 4 }}>
                {activeLocal && (
                  <Button
                    icon={<DeleteOutlined />}
                    size="small"
                    danger
                    onClick={() => handleDeleteLocal(activeLocalIndex!)}
                  >
                    Delete
                  </Button>
                )}
                <Button icon={<UndoOutlined />} size="small" onClick={handleReset}>
                  Reset
                </Button>
              </div>
            }
            style={{ maxHeight: 'calc(100vh - 140px)', overflow: 'auto' }}
          >
            {activeLocal ? (
              /* Local adjustment parameter panel */
              <LocalParamPanel
                adjustment={activeLocal}
                onUpdate={(group, key, value) => updateLocalParam(activeLocalIndex!, group, key, value)}
              />
            ) : (
              /* Global parameter panel */
              <Collapse
                defaultActiveKey={['basic']}
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
                    key: 'hsl',
                    label: 'HSL',
                    children: (
                      <div>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
                          {HSL_COLORS.map((c) => (
                            <Button
                              key={c}
                              size="small"
                              type={hslColor === c ? 'primary' : 'text'}
                              onClick={() => setHslColor(c)}
                              style={{
                                padding: '0 8px',
                                fontSize: 12,
                                borderColor: hslColor === c ? undefined : '#333',
                              }}
                            >
                              <span
                                style={{
                                  display: 'inline-block',
                                  width: 8,
                                  height: 8,
                                  borderRadius: '50%',
                                  background: HSL_DOT_COLORS[c],
                                  marginRight: 4,
                                }}
                              />
                              {HSL_COLOR_LABELS[c]}
                            </Button>
                          ))}
                        </div>
                        <ParamSliderGroup
                          title=""
                          sliders={[
                            { key: 'hue', label: 'Hue', min: -180, max: 180, step: 1, defaultValue: 0 },
                            { key: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, defaultValue: 0 },
                            { key: 'luminance', label: 'Luminance', min: -100, max: 100, step: 1, defaultValue: 0 },
                          ]}
                          values={params.hsl[hslColor] as unknown as Record<string, number>}
                          onChange={(key, value) => updateHsl(hslColor, key, value)}
                        />
                      </div>
                    ),
                  },
                  {
                    key: 'split_toning',
                    label: 'Color Grading',
                    children: (
                      <div>
                        <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', display: 'block', marginBottom: 8 }}>
                          Highlights
                        </Text>
                        <ParamSliderGroup
                          title=""
                          sliders={[
                            { key: 'hue', label: 'Hue', min: 0, max: 360, step: 1, defaultValue: 0 },
                            { key: 'saturation', label: 'Saturation', min: 0, max: 100, step: 1, defaultValue: 0 },
                          ]}
                          values={params.split_toning.highlights as unknown as Record<string, number>}
                          onChange={(key, value) => updateSplitToning('highlights', key, value)}
                        />
                        <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', display: 'block', marginBottom: 8, marginTop: 8 }}>
                          Midtones
                        </Text>
                        <ParamSliderGroup
                          title=""
                          sliders={[
                            { key: 'hue', label: 'Hue', min: 0, max: 360, step: 1, defaultValue: 0 },
                            { key: 'saturation', label: 'Saturation', min: 0, max: 100, step: 1, defaultValue: 0 },
                          ]}
                          values={params.split_toning.midtones as unknown as Record<string, number>}
                          onChange={(key, value) => updateSplitToning('midtones', key, value)}
                        />
                        <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', display: 'block', marginBottom: 8, marginTop: 8 }}>
                          Shadows
                        </Text>
                        <ParamSliderGroup
                          title=""
                          sliders={[
                            { key: 'hue', label: 'Hue', min: 0, max: 360, step: 1, defaultValue: 0 },
                            { key: 'saturation', label: 'Saturation', min: 0, max: 100, step: 1, defaultValue: 0 },
                          ]}
                          values={params.split_toning.shadows as unknown as Record<string, number>}
                          onChange={(key, value) => updateSplitToning('shadows', key, value)}
                        />
                        <div style={{ marginTop: 12 }}>
                          <Row align="middle" gutter={8}>
                            <Col span={5}>
                              <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>Balance</Text>
                            </Col>
                            <Col span={15}>
                              <Slider
                                min={-100}
                                max={100}
                                step={1}
                                value={params.split_toning.balance}
                                onChange={updateSplitToningBalance}
                              />
                            </Col>
                            <Col span={4}>
                              <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)' }}>
                                {params.split_toning.balance}
                              </Text>
                            </Col>
                          </Row>
                        </div>
                      </div>
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
            )}

            {/* Local adjustment list */}
            {localAdjustments.length > 0 && !activeLocal && (
              <div style={{ marginTop: 16, borderTop: '1px solid #2a2a2a', paddingTop: 12 }}>
                <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', display: 'block', marginBottom: 8 }}>
                  Local Adjustments ({localAdjustments.length})
                </Text>
                {localAdjustments.map((adj, i) => (
                  <div
                    key={adj.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 8px',
                      borderRadius: 6,
                      background: '#1a1a1a',
                      marginBottom: 4,
                      cursor: 'pointer',
                    }}
                    onClick={() => setActiveLocalIndex(i)}
                  >
                    <Text style={{ fontSize: 12 }}>
                      {adj.region.type === 'rect' ? 'Rectangle' : 'Ellipse'} #{i + 1}
                    </Text>
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteLocal(i);
                      }}
                    />
                  </div>
                ))}
              </div>
            )}

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

/** Local adjustment parameter panel - simplified subset of controls */
function LocalParamPanel({
  adjustment,
  onUpdate,
}: {
  adjustment: LocalAdjustment;
  onUpdate: (group: string, key: string, value: number) => void;
}) {
  const basic = (adjustment.parameters.basic || {
    exposure: 0, contrast: 0, highlights: 0, shadows: 0, whites: 0, blacks: 0,
  }) as Record<string, number>;
  const color = (adjustment.parameters.color || {
    temperature: 6500, tint: 0, vibrance: 0, saturation: 0,
  }) as Record<string, number>;

  return (
    <div>
      <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', display: 'block', marginBottom: 8 }}>
        {adjustment.region.type === 'rect' ? 'Rectangle' : 'Ellipse'} region — Feather: {adjustment.region.feather}
      </Text>
      <Collapse
        defaultActiveKey={['basic', 'color']}
        ghost
        items={[
          {
            key: 'basic',
            label: 'Basic',
            children: (
              <ParamSliderGroup
                title=""
                sliders={[
                  { key: 'exposure', label: 'Exposure', min: -3, max: 3, step: 0.1, defaultValue: 0 },
                  { key: 'contrast', label: 'Contrast', min: -100, max: 100, step: 1, defaultValue: 0 },
                  { key: 'highlights', label: 'Highlights', min: -100, max: 100, step: 1, defaultValue: 0 },
                  { key: 'shadows', label: 'Shadows', min: -100, max: 100, step: 1, defaultValue: 0 },
                ]}
                values={basic}
                onChange={(key, value) => onUpdate('basic', key, value)}
              />
            ),
          },
          {
            key: 'color',
            label: 'Color',
            children: (
              <ParamSliderGroup
                title=""
                sliders={[
                  { key: 'temperature', label: 'Temperature', min: 2000, max: 12000, step: 100, defaultValue: 6500 },
                  { key: 'tint', label: 'Tint', min: -100, max: 100, step: 1, defaultValue: 0 },
                  { key: 'saturation', label: 'Saturation', min: -100, max: 100, step: 1, defaultValue: 0 },
                ]}
                values={color}
                onChange={(key, value) => onUpdate('color', key, value)}
              />
            ),
          },
        ]}
      />
    </div>
  );
}

/** Merge partial params from suggestion into full defaults */
function mergeParams(base: ColorParams, partial: Partial<ColorParams>): ColorParams {
  return {
    ...base,
    ...partial,
    basic: { ...base.basic, ...(partial.basic || {}) },
    color: { ...base.color, ...(partial.color || {}) },
    tone_curve: { ...base.tone_curve, ...(partial.tone_curve || {}) },
    hsl: { ...base.hsl, ...(partial.hsl || {}) },
    split_toning: {
      ...base.split_toning,
      ...(partial.split_toning || {}),
      highlights: { ...base.split_toning.highlights, ...((partial.split_toning || {}).highlights || {}) },
      midtones: { ...base.split_toning.midtones, ...((partial.split_toning || {}).midtones || {}) },
      shadows: { ...base.split_toning.shadows, ...((partial.split_toning || {}).shadows || {}) },
    },
    effects: { ...base.effects, ...(partial.effects || {}) },
  };
}
