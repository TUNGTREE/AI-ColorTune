/** Shared TypeScript types for the ColorTune app. */

export interface SampleScene {
  id: string;
  scene_type: string;
  time_of_day: string;
  label_zh: string;
  label_en: string;
  thumbnail_url: string;
}

export interface ColorParams {
  version: string;
  basic: {
    exposure: number;
    contrast: number;
    highlights: number;
    shadows: number;
    whites: number;
    blacks: number;
  };
  color: {
    temperature: number;
    tint: number;
    vibrance: number;
    saturation: number;
  };
  tone_curve: {
    points: number[][];
    red: number[][] | null;
    green: number[][] | null;
    blue: number[][] | null;
  };
  hsl: Record<string, { hue: number; saturation: number; luminance: number }>;
  split_toning: {
    highlights: { hue: number; saturation: number };
    shadows: { hue: number; saturation: number };
    balance: number;
  };
  effects: {
    clarity: number;
    dehaze: number;
    vignette: number;
    grain: number;
  };
}

export interface StyleOption {
  id: string;
  style_name: string;
  description: string;
  parameters: ColorParams;
  preview_url: string | null;
  is_selected: boolean;
}

export interface StyleRound {
  id: string;
  session_id: string;
  scene_type: string | null;
  time_of_day: string | null;
  weather: string | null;
  original_image_url: string | null;
  options: StyleOption[];
}

export interface StyleSession {
  id: string;
  user_id: string;
  status: string;
  rounds: StyleRound[];
}

export interface UserProfile {
  id: string;
  user_id: string;
  session_id: string;
  profile_data: Record<string, unknown>;
}

export interface GradingSuggestion {
  id: string;
  suggestion_name: string;
  description: string;
  parameters: ColorParams;
  preview_url: string | null;
  is_selected: boolean;
}

export interface GradingTask {
  id: string;
  user_id: string;
  profile_id: string | null;
  original_image_url: string | null;
  status: string;
  suggestions: GradingSuggestion[];
}
