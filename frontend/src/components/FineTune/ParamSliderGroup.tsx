import { Slider, Typography, Row, Col } from 'antd';

const { Text } = Typography;

interface SliderDef {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
}

interface Props {
  title: string;
  sliders: SliderDef[];
  values: Record<string, number>;
  onChange: (key: string, value: number) => void;
}

export default function ParamSliderGroup({ title, sliders, values, onChange }: Props) {
  return (
    <div style={{ marginBottom: 16 }}>
      {title && (
        <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>
          {title}
        </Text>
      )}
      {sliders.map((s) => (
        <Row key={s.key} align="middle" gutter={8} style={{ marginBottom: 4 }}>
          <Col span={5}>
            <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>
              {s.label}
            </Text>
          </Col>
          <Col span={15}>
            <Slider
              min={s.min}
              max={s.max}
              step={s.step}
              value={values[s.key] ?? s.defaultValue}
              onChange={(v) => onChange(s.key, v)}
            />
          </Col>
          <Col span={4}>
            <Text style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)' }}>
              {(values[s.key] ?? s.defaultValue).toFixed(s.step < 1 ? 1 : 0)}
            </Text>
          </Col>
        </Row>
      ))}
    </div>
  );
}
