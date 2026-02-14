import { useState, useCallback, useEffect } from 'react';
import { Row, Col, Typography, Spin, Button, message, Progress, theme } from 'antd';
import { CheckCircleFilled, ThunderboltOutlined, ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
import { styleApi } from '../../api';
import { useAppStore } from '../../stores/appStore';
import type { SampleScene, StyleRound, StyleOption } from '../../types';

const { Title, Text } = Typography;

const API_BASE = 'http://localhost:8000';

const MIN_ROUNDS = 3;
const MAX_ROUNDS = 12;

type Phase = 'samples' | 'options' | 'loading';

export default function StyleDiscovery() {
  const { session, setSession, setProfile, setStep } = useAppStore();
  const { token } = theme.useToken();

  const [samples, setSamples] = useState<SampleScene[]>([]);
  const [phase, setPhase] = useState<Phase>('samples');
  const [completedSampleIds, setCompletedSampleIds] = useState<Set<string>>(new Set());
  const [currentRound, setCurrentRound] = useState<StyleRound | null>(null);
  const [currentSampleId, setCurrentSampleId] = useState<string | null>(null);
  const [rounds, setRounds] = useState<StyleRound[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Fetch samples on mount
  useEffect(() => {
    styleApi.getSamples().then(setSamples).catch(() => {
      message.error('Failed to load sample scenes');
    });
  }, []);

  const completedCount = completedSampleIds.size;
  const canAnalyze = completedCount >= MIN_ROUNDS;
  const allDone = completedCount >= MAX_ROUNDS;

  // Handle sample card click
  const handleSampleClick = useCallback(
    async (sample: SampleScene) => {
      if (completedSampleIds.has(sample.id)) return;

      setPhase('loading');
      setCurrentSampleId(sample.id);

      try {
        // Create session if needed
        let sid = session?.id;
        if (!sid) {
          const s = await styleApi.createSession();
          setSession(s);
          sid = s.id;
        }

        // Create round from sample
        const round = await styleApi.createRoundFromSample(sid!, sample.id);
        setCurrentRound(round);

        if (!round.options || round.options.length === 0) {
          message.warning(
            'No style options generated. Check AI settings in the header.',
            5,
          );
          setPhase('samples');
          return;
        }
        setPhase('options');
      } catch (err: unknown) {
        const detail =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;
        message.error(detail || 'Failed to generate style options. Check AI Settings in the header.');
        setPhase('samples');
      }
    },
    [session, setSession, completedSampleIds],
  );

  // Handle style option selection
  const handleSelectOption = useCallback(
    async (roundId: string, optionId: string) => {
      try {
        await styleApi.selectOption(roundId, optionId);

        // Update current round
        if (currentRound) {
          const updated = {
            ...currentRound,
            options: currentRound.options.map((o) => ({
              ...o,
              is_selected: o.id === optionId,
            })),
          };
          setCurrentRound(updated);
          setRounds((prev) => [...prev, updated]);
        }

        // Mark sample as completed
        if (currentSampleId) {
          setCompletedSampleIds((prev) => new Set([...prev, currentSampleId]));
        }

        message.success('Style selected!');

        // Return to samples after a brief delay
        setTimeout(() => {
          setPhase('samples');
          setCurrentRound(null);
          setCurrentSampleId(null);
        }, 600);
      } catch {
        message.error('Failed to select style');
      }
    },
    [currentRound, currentSampleId],
  );

  // Regenerate style options for current round
  const handleRegenerate = useCallback(async () => {
    if (!currentRound) return;
    setRegenerating(true);
    try {
      const newRound = await styleApi.regenerateOptions(currentRound.id);
      setCurrentRound(newRound);
      if (!newRound.options || newRound.options.length === 0) {
        message.warning('No style options generated. Try again or check AI settings.');
      } else {
        message.success('New style options generated!');
      }
    } catch {
      message.error('Failed to regenerate options');
    } finally {
      setRegenerating(false);
    }
  }, [currentRound]);

  // Analyze preferences
  const handleAnalyze = useCallback(async () => {
    if (!session) return;
    setAnalyzing(true);
    try {
      const profile = await styleApi.analyzeSession(session.id);
      setProfile(profile);
      setStep(1);
      message.success('Style profile created!');
    } catch {
      message.error('Failed to analyze preferences');
    } finally {
      setAnalyzing(false);
    }
  }, [session, setProfile, setStep]);

  // --- Loading state ---
  if (phase === 'loading') {
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
        <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14 }}>
          Analyzing scene and generating style options...
        </Text>
      </div>
    );
  }

  // --- Options phase ---
  if (phase === 'options' && currentRound) {
    const hasSelection = currentRound.options.some((o) => o.is_selected);
    return (
      <div style={{ width: '100%', padding: '16px 0' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>
            Choose your preferred style
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.45)' }}>
            {currentRound.scene_type} &middot; {currentRound.time_of_day}
          </Text>
        </div>

        <Row gutter={[16, 16]} justify="center">
          {currentRound.options.map((option: StyleOption) => (
            <Col xs={24} sm={12} md={8} lg={6} key={option.id}>
              <div
                onClick={() =>
                  !hasSelection && handleSelectOption(currentRound.id, option.id)
                }
                style={{
                  position: 'relative',
                  borderRadius: 12,
                  overflow: 'hidden',
                  cursor: hasSelection ? 'default' : 'pointer',
                  border: option.is_selected
                    ? `3px solid ${token.colorPrimary}`
                    : '3px solid transparent',
                  opacity: hasSelection && !option.is_selected ? 0.5 : 1,
                  transition: 'all 0.3s ease',
                  background: '#1a1a1a',
                }}
              >
                {option.preview_url ? (
                  <img
                    alt={option.style_name}
                    src={`${API_BASE}${option.preview_url}`}
                    style={{
                      width: '100%',
                      height: 220,
                      objectFit: 'cover',
                      display: 'block',
                    }}
                  />
                ) : (
                  <div style={{ height: 220, background: '#1a1a1a' }} />
                )}
                <div
                  style={{
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.85)',
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                    ellipsis
                  >
                    {option.style_name}
                  </Text>
                  {option.is_selected && (
                    <CheckCircleFilled
                      style={{ color: token.colorPrimary, fontSize: 18 }}
                    />
                  )}
                </div>
              </div>
            </Col>
          ))}
        </Row>

        <div style={{ textAlign: 'center', marginTop: 24, display: 'flex', justifyContent: 'center', gap: 16 }}>
          <Button
            onClick={() => {
              setPhase('samples');
              setCurrentRound(null);
              setCurrentSampleId(null);
            }}
            icon={<ArrowLeftOutlined />}
            style={{ color: 'rgba(255,255,255,0.45)' }}
            type="text"
          >
            Back to samples
          </Button>
          {!hasSelection && (
            <Button
              onClick={handleRegenerate}
              icon={<ReloadOutlined />}
              loading={regenerating}
              type="text"
              style={{ color: 'rgba(255,255,255,0.45)' }}
            >
              Regenerate options
            </Button>
          )}
        </div>
      </div>
    );
  }

  // --- Sample grid phase ---
  return (
    <div style={{ width: '100%', padding: '16px 0' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: '0 0 8px' }}>
          Discover Your Style
        </Title>
        <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14 }}>
          Select scenes to explore different color grading styles.
          {completedCount < MIN_ROUNDS
            ? ` Complete at least ${MIN_ROUNDS} rounds to build your profile.`
            : completedCount < MAX_ROUNDS
              ? ' You can analyze now or continue for better accuracy.'
              : ' All scenes completed!'}
        </Text>
      </div>

      {/* Progress indicator */}
      <div
        style={{
          maxWidth: 500,
          margin: '0 auto 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <Progress
          percent={(completedCount / MAX_ROUNDS) * 100}
          success={{ percent: (Math.min(completedCount, MIN_ROUNDS) / MAX_ROUNDS) * 100 }}
          showInfo={false}
          strokeColor={token.colorPrimary}
          railColor="#2a2a2a"
          size="small"
        />
        <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12, whiteSpace: 'nowrap' }}>
          {completedCount} / {MAX_ROUNDS}
        </Text>
      </div>

      {/* Analyze button — prominent when available */}
      {canAnalyze && (
        <div
          style={{
            textAlign: 'center',
            marginBottom: 24,
            padding: '16px',
            background: 'rgba(91, 106, 191, 0.08)',
            borderRadius: 12,
            border: '1px solid rgba(91, 106, 191, 0.2)',
          }}
        >
          <div style={{ marginBottom: 8 }}>
            <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13 }}>
              {allDone
                ? 'All scenes completed! Ready to analyze your style.'
                : `${completedCount} rounds completed. You can analyze now or continue for more accurate results (${MAX_ROUNDS - completedCount} scenes remaining).`}
            </Text>
          </div>
          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            loading={analyzing}
            onClick={handleAnalyze}
            style={{
              height: 48,
              paddingInline: 32,
              borderRadius: 12,
              fontWeight: 600,
            }}
          >
            Analyze My Style Preferences ({completedCount} rounds)
          </Button>
        </div>
      )}

      {/* Sample grid */}
      <Row gutter={[16, 16]}>
        {samples.map((sample) => {
          const done = completedSampleIds.has(sample.id);
          return (
            <Col xs={12} sm={8} md={6} lg={4} key={sample.id}>
              <div
                onClick={() => !done && handleSampleClick(sample)}
                style={{
                  position: 'relative',
                  borderRadius: 12,
                  overflow: 'hidden',
                  cursor: done ? 'default' : 'pointer',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                  background: '#1a1a1a',
                }}
                onMouseEnter={(e) => {
                  if (!done) {
                    (e.currentTarget as HTMLDivElement).style.transform = 'scale(1.03)';
                    (e.currentTarget as HTMLDivElement).style.boxShadow =
                      '0 8px 24px rgba(0,0,0,0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLDivElement).style.transform = 'scale(1)';
                  (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
                }}
              >
                <img
                  alt={sample.label_en}
                  src={`${API_BASE}${sample.thumbnail_url}`}
                  style={{
                    width: '100%',
                    height: 160,
                    objectFit: 'cover',
                    display: 'block',
                    opacity: done ? 0.4 : 1,
                  }}
                />

                {/* Completed overlay */}
                {done && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <CheckCircleFilled
                      style={{ fontSize: 32, color: token.colorPrimary, opacity: 0.8 }}
                    />
                  </div>
                )}

                {/* Bottom label */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    padding: '20px 10px 8px',
                    background: 'linear-gradient(transparent, rgba(0,0,0,0.7))',
                  }}
                >
                  <Text
                    style={{
                      color: '#fff',
                      fontSize: 12,
                      fontWeight: 500,
                      display: 'block',
                    }}
                    ellipsis
                  >
                    {sample.label_zh}
                  </Text>
                </div>
              </div>
            </Col>
          );
        })}
      </Row>

      {/* Bottom hint for users who haven't reached minimum */}
      {completedCount > 0 && !canAnalyze && (
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>
            {MIN_ROUNDS - completedCount} more round{MIN_ROUNDS - completedCount > 1 ? 's' : ''} needed before analysis
          </Text>
        </div>
      )}
    </div>
  );
}
