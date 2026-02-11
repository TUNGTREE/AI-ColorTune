/**
 * Client-side CSS-filter-based real-time preview.
 *
 * Maps ColorParams basic & color to CSS filter properties for instant feedback.
 * This is an approximation — the server-side preview is the source of truth.
 */

interface BasicPreviewParams {
  exposure: number;   // [-3, 3]
  contrast: number;   // [-100, 100]
  highlights: number; // [-100, 100] (not directly mappable, ignored)
  shadows: number;    // [-100, 100] (not directly mappable, ignored)
  whites: number;     // [-100, 100] (not directly mappable, ignored)
  blacks: number;     // [-100, 100] (not directly mappable, ignored)
}

interface ColorPreviewParams {
  temperature: number;  // [2000, 12000]
  tint: number;         // [-100, 100]
  vibrance: number;     // [-100, 100] → approximate with saturate
  saturation: number;   // [-100, 100]
}

interface EffectsPreviewParams {
  clarity: number;   // [-100, 100] → contrast boost
  dehaze: number;    // [-100, 100]
  vignette: number;  // [-100, 100]
  grain: number;     // [0, 100]
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
  // Warm (>6500): add slight sepia
  // Cool (<6500): add slight hue-rotate toward blue
  const tempDiff = params.color.temperature - 6500;
  if (tempDiff > 0) {
    const sepia = Math.min(tempDiff / 8000, 0.3);
    filters.push(`sepia(${sepia.toFixed(3)})`);
  } else if (tempDiff < 0) {
    const hueShift = (tempDiff / 6500) * 30; // max ~30deg toward blue
    filters.push(`hue-rotate(${hueShift.toFixed(1)}deg)`);
  }

  // Clarity → extra contrast on midtones (approximate as slight contrast boost)
  if (params.effects.clarity !== 0) {
    const clarityContrast = 1 + params.effects.clarity / 400;
    filters.push(`contrast(${clarityContrast.toFixed(3)})`);
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
