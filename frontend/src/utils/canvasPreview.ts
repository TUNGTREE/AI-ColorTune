/**
 * Client-side CSS-filter-based real-time preview.
 *
 * Maps ColorParams basic & color to CSS filter properties for instant feedback.
 * This is an approximation — the server-side preview is the source of truth.
 */

interface BasicPreviewParams {
  exposure: number;   // [-3, 3]
  contrast: number;   // [-100, 100]
  highlights: number; // [-100, 100]
  shadows: number;    // [-100, 100]
  whites: number;     // [-100, 100]
  blacks: number;     // [-100, 100]
}

interface ColorPreviewParams {
  temperature: number;  // [2000, 12000]
  tint: number;         // [-100, 100]
  vibrance: number;     // [-100, 100] → approximate with saturate
  saturation: number;   // [-100, 100]
}

interface EffectsPreviewParams {
  clarity: number;      // [-100, 100]
  dehaze: number;       // [-100, 100]
  vignette: number;     // [-100, 100]
  grain: number;        // [0, 100]
  texture: number;      // [-100, 100]
  fade: number;         // [0, 100]
  sharpening: number;   // [0, 100]
  sharpen_radius: number; // [0.5, 5]
}

export interface PreviewParams {
  basic: BasicPreviewParams;
  color: ColorPreviewParams;
  effects: EffectsPreviewParams;
}

/**
 * Convert color grading params to a CSS filter string.
 */
export function paramsToCssFilter(params: PreviewParams): string {
  const filters: string[] = [];

  // Exposure → brightness: 2^EV
  const brightness = Math.pow(2, params.basic.exposure);
  filters.push(`brightness(${brightness.toFixed(3)})`);

  // Contrast: map [-100, 100] → [0.5, 1.5]
  const contrast = 1 + params.basic.contrast / 200;
  filters.push(`contrast(${contrast.toFixed(3)})`);

  // Saturation: combine saturation + vibrance
  const satBoost = params.color.saturation / 100;
  const vibBoost = params.color.vibrance / 200; // vibrance has milder effect
  const saturate = 1 + satBoost + vibBoost;
  filters.push(`saturate(${Math.max(0, saturate).toFixed(3)})`);

  // Temperature → sepia + hue-rotate approximation
  const tempDiff = params.color.temperature - 6500;
  if (tempDiff > 0) {
    const sepia = Math.min(tempDiff / 8000, 0.3);
    filters.push(`sepia(${sepia.toFixed(3)})`);
  } else if (tempDiff < 0) {
    const hueShift = (tempDiff / 6500) * 30;
    filters.push(`hue-rotate(${hueShift.toFixed(1)}deg)`);
  }

  // Clarity → extra contrast on midtones (approximate)
  if (params.effects.clarity !== 0) {
    const clarityContrast = 1 + params.effects.clarity / 400;
    filters.push(`contrast(${clarityContrast.toFixed(3)})`);
  }

  // Texture → slight contrast for detail emphasis
  if (params.effects.texture !== 0) {
    const textureContrast = 1 + params.effects.texture / 600;
    filters.push(`contrast(${textureContrast.toFixed(3)})`);
  }

  // Dehaze → slight brightness and contrast boost
  if (params.effects.dehaze !== 0) {
    const dehazeBright = 1 + params.effects.dehaze / 400;
    const dehazeContrast = 1 + params.effects.dehaze / 300;
    filters.push(`brightness(${dehazeBright.toFixed(3)})`);
    filters.push(`contrast(${dehazeContrast.toFixed(3)})`);
  }

  // Fade → lift blacks by reducing contrast + slight brightness increase
  if (params.effects.fade > 0) {
    const fadeAmount = params.effects.fade / 100;
    const fadeBright = 1 + fadeAmount * 0.1;
    const fadeContrast = 1 - fadeAmount * 0.2;
    filters.push(`brightness(${fadeBright.toFixed(3)})`);
    filters.push(`contrast(${fadeContrast.toFixed(3)})`);
  }

  // Tint → slight hue-rotate for green-magenta shift
  if (params.color.tint !== 0) {
    const tintShift = params.color.tint / 100 * 10;
    filters.push(`hue-rotate(${tintShift.toFixed(1)}deg)`);
  }

  return filters.join(' ');
}

/**
 * Generate CSS for vignette overlay using radial-gradient.
 */
export function vignetteGradient(amount: number): string {
  if (amount >= 0) return 'none';
  const strength = Math.abs(amount) / 100;
  const alpha = (strength * 0.8).toFixed(2);
  return `radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,${alpha}) 100%)`;
}
