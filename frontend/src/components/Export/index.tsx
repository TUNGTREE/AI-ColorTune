import { useState, useCallback } from 'react';
import {
  Card,
  Button,
  Row,
  Col,
  Typography,
  Select,
  Slider,
  Spin,
  message,
  Result,
} from 'antd';
import { DownloadOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useAppStore } from '../../stores/appStore';
import { gradingApi } from '../../api';

const { Title, Text } = Typography;

const API_BASE = 'http://localhost:8000';

const FORMAT_OPTIONS = [
  { value: 'jpeg', label: 'JPEG (smaller file, good quality)' },
  { value: 'png', label: 'PNG (lossless, larger file)' },
  { value: 'tiff', label: 'TIFF (highest quality, very large)' },
];

export default function ExportPanel() {
  const { gradingTask, finalParams, selectedSuggestion, localAdjustments } = useAppStore();
  const [format, setFormat] = useState<string>('jpeg');
  const [quality, setQuality] = useState<number>(95);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{
    id: string;
    output_url: string | null;
  } | null>(null);

  const params = finalParams || selectedSuggestion?.parameters || null;

  const handleExport = useCallback(async () => {
    if (!gradingTask || !params) return;
    setExporting(true);
    try {
      const localAdj = localAdjustments.length > 0
        ? localAdjustments.map((a) => ({
            region: a.region as unknown as Record<string, unknown>,
            parameters: a.parameters as unknown as Record<string, unknown>,
          }))
        : undefined;
      const result = await gradingApi.exportImage(
        gradingTask.id,
        params as unknown as Record<string, unknown>,
        format,
        quality,
        localAdj,
      );
      setExportResult({ id: result.id, output_url: result.output_url });
      message.success('Export completed!');
    } catch {
      message.error('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  }, [gradingTask, params, format, quality, localAdjustments]);

  const handleDownload = useCallback(() => {
    if (!exportResult) return;
    const url = gradingApi.downloadExport(exportResult.id);
    window.open(url, '_blank');
  }, [exportResult]);

  if (!gradingTask || !params) {
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
          Please complete the previous steps first.
        </Text>
      </div>
    );
  }

  if (exportResult) {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <Card>
          <Result
            icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            title="Export Complete!"
            subTitle={`Format: ${format.toUpperCase()} | Quality: ${quality}%`}
            extra={[
              <Button
                key="download"
                type="primary"
                size="large"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                style={{ borderRadius: 10 }}
              >
                Download Image
              </Button>,
              <Button
                key="preview"
                size="large"
                onClick={() =>
                  exportResult.output_url &&
                  window.open(`${API_BASE}${exportResult.output_url}`, '_blank')
                }
                style={{ borderRadius: 10 }}
              >
                View in Browser
              </Button>,
              <Button
                key="another"
                onClick={() => setExportResult(null)}
                style={{ borderRadius: 10 }}
              >
                Export Again
              </Button>,
            ]}
          />
          {exportResult.output_url && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <img
                src={`${API_BASE}${exportResult.output_url}`}
                alt="Exported"
                style={{ maxWidth: '100%', maxHeight: 400, objectFit: 'contain', borderRadius: 8 }}
              />
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card>
        <Title level={3} style={{ textAlign: 'center' }}>
          Export Your Image
        </Title>

        <Row gutter={[16, 24]}>
          {/* Preview */}
          <Col span={24}>
            {gradingTask.original_image_url && (
              <div style={{ textAlign: 'center' }}>
                <img
                  src={`${API_BASE}${gradingTask.original_image_url}`}
                  alt="Original"
                  style={{
                    maxWidth: '100%',
                    maxHeight: 300,
                    objectFit: 'contain',
                    borderRadius: 8,
                  }}
                />
                <Text style={{ display: 'block', marginTop: 8, color: 'rgba(255,255,255,0.45)' }}>
                  Original image — final grading will be applied at full resolution
                </Text>
              </div>
            )}
          </Col>

          {/* Format selection */}
          <Col span={24}>
            <Text strong>Output Format</Text>
            <Select
              value={format}
              onChange={setFormat}
              options={FORMAT_OPTIONS}
              style={{ width: '100%', marginTop: 8 }}
              size="large"
            />
          </Col>

          {/* Quality slider (only for JPEG) */}
          {format === 'jpeg' && (
            <Col span={24}>
              <Text strong>Quality: {quality}%</Text>
              <Slider
                min={50}
                max={100}
                value={quality}
                onChange={setQuality}
                marks={{ 50: '50%', 75: '75%', 95: '95%', 100: '100%' }}
              />
            </Col>
          )}

          {/* Export button */}
          <Col span={24} style={{ textAlign: 'center' }}>
            <Button
              type="primary"
              size="large"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              loading={exporting}
              style={{
                minWidth: 200,
                height: 48,
                borderRadius: 12,
                fontWeight: 600,
              }}
            >
              {exporting ? 'Exporting...' : 'Export Image'}
            </Button>
            {exporting && (
              <div style={{ marginTop: 16 }}>
                <Spin />
                <Text style={{ display: 'block', marginTop: 8, color: 'rgba(255,255,255,0.45)' }}>
                  Applying color grading at full resolution...
                </Text>
              </div>
            )}
          </Col>
        </Row>
      </Card>
    </div>
  );
}
