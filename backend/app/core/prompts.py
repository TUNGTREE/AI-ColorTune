"""Prompt templates for AI providers.

All prompts instruct the AI to output structured JSON conforming to ColorParams schema.
"""

COLOR_PARAMS_SCHEMA_DESCRIPTION = """
The color grading parameters must follow this exact JSON structure:
{
  "version": "1.0",
  "basic": {
    "exposure": <float, -3.0 to 3.0, EV stops>,
    "contrast": <float, -100 to 100>,
    "highlights": <float, -100 to 100>,
    "shadows": <float, -100 to 100>,
    "whites": <float, -100 to 100>,
    "blacks": <float, -100 to 100>
  },
  "color": {
    "temperature": <float, 2000 to 12000, Kelvin>,
    "tint": <float, -100 to 100, Green(-) to Magenta(+)>,
    "vibrance": <float, -100 to 100>,
    "saturation": <float, -100 to 100>
  },
  "tone_curve": {
    "points": [[0,0],[64,64],[128,128],[192,192],[255,255]],
    "red": null,
    "green": null,
    "blue": null
  },
  "hsl": {
    "red": {"hue": 0, "saturation": 0, "luminance": 0},
    "orange": {"hue": 0, "saturation": 0, "luminance": 0},
    "yellow": {"hue": 0, "saturation": 0, "luminance": 0},
    "green": {"hue": 0, "saturation": 0, "luminance": 0},
    "aqua": {"hue": 0, "saturation": 0, "luminance": 0},
    "blue": {"hue": 0, "saturation": 0, "luminance": 0},
    "purple": {"hue": 0, "saturation": 0, "luminance": 0},
    "magenta": {"hue": 0, "saturation": 0, "luminance": 0}
  },
  "split_toning": {
    "highlights": {"hue": <0-360>, "saturation": <0-100>},
    "shadows": {"hue": <0-360>, "saturation": <0-100>},
    "balance": <float, -100 to 100>
  },
  "effects": {
    "clarity": <float, -100 to 100>,
    "dehaze": <float, -100 to 100>,
    "vignette": <float, -100 to 100>,
    "grain": <float, 0 to 100>
  }
}
""".strip()


SCENE_ANALYSIS_PROMPT = """Analyze this photograph and describe:
1. Scene type (landscape, portrait, street, indoor, architecture, food, nature, etc.)
2. Time of day (dawn, morning, afternoon, golden_hour, blue_hour, night, unknown)
3. Weather/lighting (sunny, cloudy, overcast, rainy, foggy, snowy, artificial, mixed)
4. Dominant colors and color temperature feel
5. Overall mood and atmosphere
6. Key subjects and composition

Respond in JSON format:
{
  "scene_type": "string",
  "time_of_day": "string",
  "weather": "string",
  "dominant_colors": ["string"],
  "color_temperature_feel": "warm|neutral|cool",
  "mood": "string",
  "subjects": ["string"],
  "composition": "string"
}
"""


STYLE_OPTIONS_PROMPT = """You are a professional colorist. Given the photograph and its scene analysis below, generate {num_styles} distinctly different color grading styles.

Scene analysis:
{scene_info}

Requirements:
- Each style must be visually distinct from the others
- Include a variety: at least one warm/cool, one high/low contrast, one vivid/muted
- Name each style descriptively (e.g., "Cinematic Teal & Orange", "Soft Pastel Morning", "Bold & Punchy")
- Provide complete parameter sets that create noticeable visual differences

{schema}

Respond with a JSON array of style objects:
[
  {{
    "style_name": "descriptive name",
    "description": "brief description of the look",
    "parameters": <complete ColorParams JSON>
  }},
  ...
]

Output ONLY the JSON array, no other text.
"""


PREFERENCE_ANALYSIS_PROMPT = """Analyze the user's color grading style preferences based on their selections across multiple rounds.

User selections:
{selections}

For each round, the user was shown multiple style options and selected their preferred one.
Analyze patterns in their choices regarding:
1. Color temperature preference (warm vs cool)
2. Contrast preference (high vs low)
3. Saturation preference (vivid vs muted)
4. Tone preference (bright/airy vs dark/moody)
5. Common color palette tendencies
6. Effects preferences (clarity, grain, vignette)

Respond in JSON format:
{{
  "temperature_preference": "warm|neutral|cool",
  "contrast_preference": "high|medium|low",
  "saturation_preference": "vivid|moderate|muted",
  "tone_preference": "bright|balanced|dark",
  "color_tendencies": ["description of color patterns"],
  "effects_notes": "description of effects preferences",
  "overall_style_summary": "2-3 sentence summary of their style",
  "reference_styles": ["closest professional style references"]
}}
"""


GRADING_SUGGESTION_PROMPT = """You are a professional colorist. Based on the user's style profile and the new photograph, generate {num_suggestions} personalized color grading suggestions.

User style profile:
{user_profile}

Requirements:
- All suggestions should align with the user's demonstrated preferences
- Each suggestion should offer a variation within their preferred style range
- Name each suggestion clearly
- Provide complete, specific parameter values (not generic/zero values)

{schema}

Respond with a JSON array:
[
  {{
    "suggestion_name": "descriptive name",
    "description": "why this suits their style and this photo",
    "parameters": <complete ColorParams JSON>
  }},
  ...
]

Output ONLY the JSON array, no other text.
"""
