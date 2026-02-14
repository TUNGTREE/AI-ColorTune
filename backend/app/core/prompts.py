"""Prompt templates for AI providers.

All prompts instruct the AI to output structured JSON conforming to ColorParams schema.
Uses perceptual color science principles (LAB/LCH color space concepts, warm/cool
classification, complementary palette theory) to ensure maximally distinctive yet
tasteful style options.
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


STYLE_OPTIONS_PROMPT = """You are an expert colorist with deep knowledge of perceptual color science (LAB/LCH color spaces, CIEDE2000 color difference, warm/cool hue classification).

Given the photograph and its scene analysis, generate exactly {num_styles} color grading styles that are MAXIMALLY PERCEPTUALLY DISTINCT from each other while all remaining tasteful and appropriate for this image.

Scene analysis:
{scene_info}

## DIVERSITY FRAMEWORK — Each style MUST occupy a different position along these perceptual axes:

**Axis 1: Color Temperature Direction**
- Warm-shifted (temperature > 6500K, orange/amber tones)
- Neutral/faithful (temperature ≈ 6500K)
- Cool-shifted (temperature < 6500K, blue/cyan tones)

**Axis 2: Tonal Character (Lightness distribution)**
- Bright & airy (lifted shadows, positive exposure, lower contrast)
- Balanced & natural (neutral exposure, moderate contrast)
- Deep & moody (crushed blacks, negative exposure, higher contrast)

**Axis 3: Chroma/Saturation Strategy**
- Vivid & saturated (boosted vibrance/saturation, enhanced HSL chroma)
- Selective saturation (vibrance boost with saturation neutral, accent specific hues)
- Desaturated/muted (reduced saturation, faded look)

**Axis 4: Split Toning Harmony (using color wheel)**
- Complementary split: highlights warm (30-60°) / shadows cool (200-240°)
- Analogous split: highlights and shadows within 60° of each other
- Monochromatic: no split toning (saturation = 0)

## MANDATORY: You MUST generate styles that differ across AT LEAST 2 of these 4 axes. No two styles should share the same position on more than 2 axes.

## ARCHETYPE LIBRARY — 16 reference styles. Select the {num_styles} most appropriate for THIS specific scene (see scene-adaptive rules below), then customize parameters to work WITH the image's existing palette.

1. **Clean & Natural** — Faithful colors, balanced exposure, minimal processing, slight clarity boost. Like a well-exposed DSLR shot. (Neutral temp, balanced tone, moderate chroma, no split tone)

2. **Warm Cinematic** — Warm highlights with teal/blue shadows. Classic orange-teal cinema look. Slightly lifted blacks, gentle S-curve. (Warm temp, balanced-to-deep tone, selective chroma, complementary split)

3. **Cool & Ethereal** — Cool temperature, lifted shadows, soft contrast. Dreamy, airy feel. Slight desaturation with blue-purple split toning. (Cool temp, bright tone, muted chroma, analogous cool split)

4. **Rich & Vivid** — Enhanced saturation and vibrance, strong clarity. Punchy colors with good contrast. Like a high-end travel photograph. (Neutral-warm temp, balanced tone, vivid chroma, monochromatic)

5. **Moody Film** — Faded blacks (lift shadow end of tone curve), slight desaturation, warm tint. Analog film nostalgia. (Warm temp, deep tone, muted chroma, warm analogous split)

6. **High Contrast Editorial** — Strong contrast, reduced saturation, dramatic shadows. Desaturated editorial look. (Neutral-cool temp, deep tone, very muted chroma, monochromatic)

7. **Golden Hour Glow** — Golden-amber warmth, soft highlights, slight orange push in HSL, gentle vignette. Emulates magic-hour light. (Very warm temp, bright tone, selective warm chroma, warm analogous split)

8. **Nordic Minimal** — Very clean, slightly cool, low saturation, high clarity, lifted midtones. Scandinavian design aesthetic. (Cool-neutral temp, bright tone, muted chroma, no split tone)

9. **Vintage Faded** — Lifted blacks via tone curve, cross-process color shift (green shadows, magenta highlights), low contrast. 70s retro palette. (Warm-neutral temp, balanced tone, muted chroma, cross-process split)

10. **Teal & Orange Cinema** — Pronounced complementary orange-teal split. Stronger than Warm Cinematic, with HSL pushing orange/teal separation. Blockbuster movie look. (Warm temp, balanced tone, selective chroma, strong complementary split)

11. **Soft Pastel** — Lifted shadows, gentle desaturation, slight pink/lavender tint via split toning. Dreamy, light-hearted. (Neutral-warm temp, very bright tone, muted chroma, pastel analogous split)

12. **Dramatic Low-Key** — Very dark, rich shadows, minimal highlight recovery, negative exposure. Selective highlights create drama. (Neutral temp, very deep tone, selective chroma, monochromatic)

13. **Autumn Warm** — Rich warm oranges/reds boosted via HSL (orange +sat, yellow +sat, green shifted toward yellow). Earthy, cozy tones. (Warm temp, balanced tone, vivid warm chroma, warm analogous split)

14. **Neon Urban** — Cool shadows with vibrant saturated highlights, high clarity, punchy colors. Urban night/street energy. (Cool temp, deep tone, vivid chroma, cool complementary split)

15. **Bleach Bypass** — Desaturated with high contrast, silver/metallic feel. Mimics bleach bypass film process. Strong S-curve with low saturation. (Neutral-cool temp, deep tone, very muted chroma, monochromatic)

16. **Luminous Soft-Light** — Bright, airy, gently blown highlights, warm pastel shadows, low contrast. Soft natural light feeling. (Neutral-warm temp, very bright tone, moderate chroma, warm analogous split)

## SCENE-ADAPTIVE ARCHETYPE SELECTION — Choose archetypes that COMPLEMENT the scene:

- **Landscape / Nature / Ocean / Lake**: Prioritize Clean & Natural, Rich & Vivid, Cool & Ethereal, Golden Hour Glow, Moody Film, Nordic Minimal, Dramatic Low-Key, Luminous Soft-Light
- **Portrait / People**: Prioritize Clean & Natural, Warm Cinematic, Soft Pastel, Golden Hour Glow, High Contrast Editorial, Luminous Soft-Light, Moody Film, Cool & Ethereal
- **Street / Urban / Architecture**: Prioritize Warm Cinematic, High Contrast Editorial, Neon Urban, Bleach Bypass, Teal & Orange Cinema, Moody Film, Vintage Faded, Rich & Vivid
- **Night / Blue Hour / City Lights**: Prioritize Neon Urban, Teal & Orange Cinema, Dramatic Low-Key, Cool & Ethereal, Moody Film, Bleach Bypass, High Contrast Editorial, Warm Cinematic
- **Golden Hour / Sunset / Sunrise**: Prioritize Golden Hour Glow, Warm Cinematic, Autumn Warm, Rich & Vivid, Soft Pastel, Moody Film, Teal & Orange Cinema, Luminous Soft-Light
- **Indoor / Food / Still Life**: Prioritize Clean & Natural, Warm Cinematic, Rich & Vivid, Soft Pastel, Luminous Soft-Light, Nordic Minimal, Vintage Faded, Golden Hour Glow
- **Forest / Mountain / Valley**: Prioritize Moody Film, Rich & Vivid, Cool & Ethereal, Nordic Minimal, Autumn Warm, Dramatic Low-Key, Clean & Natural, Bleach Bypass
- **Snow / Winter / Fog**: Prioritize Nordic Minimal, Cool & Ethereal, Bleach Bypass, Soft Pastel, Luminous Soft-Light, Clean & Natural, Dramatic Low-Key, High Contrast Editorial
- **Desert / Arid**: Prioritize Golden Hour Glow, Autumn Warm, Warm Cinematic, Bleach Bypass, Rich & Vivid, High Contrast Editorial, Dramatic Low-Key, Vintage Faded
- **Beach / Tropical**: Prioritize Rich & Vivid, Clean & Natural, Teal & Orange Cinema, Golden Hour Glow, Cool & Ethereal, Soft Pastel, Luminous Soft-Light, Warm Cinematic

Use the scene analysis to match the scene to the closest category above, then select {num_styles} archetypes from the recommended list. Do NOT use archetypes that would fight the scene's natural palette — instead adapt their core character to complement it.

{avoid_section}

## PARAMETER GUIDELINES (professional ranges):
- exposure: -0.8 to +0.8 EV (use the FULL range to create visible differences between styles)
- contrast: -30 to +40 (vary significantly between styles)
- highlights: -50 to +30
- shadows: -30 to +50
- whites/blacks: -30 to +30
- temperature: 5000-8000K (vary by at least 500K between warm/cool styles)
- tint: -15 to +15
- vibrance: -25 to +30 (MUST differ between styles)
- saturation: -30 to +20 (MUST differ between styles)
- clarity: -10 to 25
- dehaze: 0 to 15
- grain: ALWAYS 0 (never add grain)
- vignette: -25 to 0
- HSL hue shifts: ±15 (use to push specific color families)
- HSL saturation: ±20 (use to accent or mute specific hues)
- HSL luminance: ±20
- Split toning saturation: 0-20
- Tone curve: use S-curves (darken shadows, brighten highlights) or inverse-S, or lifted blacks. DO NOT leave all styles with the default flat curve.

## CRITICAL: Make styles VISUALLY DISTINGUISHABLE
- At least one style should be noticeably warmer and one cooler
- At least one should be brighter/airier and one deeper/moodier
- At least one should have more saturated colors and one more muted
- The tone curve should differ between styles (some with S-curve, some with lifted blacks, some flat)
- Use split toning to create different color character between styles

{schema}

Respond with a JSON array of exactly {num_styles} style objects:
[
  {{
    "style_name": "descriptive name",
    "description": "brief description of the look and which archetype it's based on",
    "parameters": <complete ColorParams JSON>
  }},
  ...
]

Output ONLY the JSON array, no other text.
"""


PREFERENCE_ANALYSIS_PROMPT = """You are a color science expert analyzing a user's color grading preferences. Use perceptual color theory to identify their aesthetic patterns.

User selections across {num_rounds} rounds of style discovery:
{selections}

For each round, the user was shown multiple distinct style options (varying in color temperature, tonal character, chroma strategy, and split toning) and selected their preferred one.

Analyze their choices along these PERCEPTUAL DIMENSIONS:

1. **Temperature axis (LAB b-channel tendency):**
   - Do they consistently pick warm-shifted styles (b > 0, orange/amber)?
   - Or cool-shifted styles (b < 0, blue/cyan)?
   - Or neutral/faithful?

2. **Lightness distribution (LAB L-channel):**
   - Do they prefer bright/airy looks (lifted shadows, high average L)?
   - Or deep/moody looks (crushed blacks, low average L)?
   - Or balanced midtones?

3. **Chroma preference (LCH C-channel):**
   - Do they favor vivid, high-chroma colors?
   - Or muted, desaturated palettes?
   - Or selective saturation (vibrance > saturation)?

4. **Tone curve shape preference:**
   - S-curve (high contrast)?
   - Lifted blacks (film look)?
   - Linear (natural)?

5. **Color harmony pattern:**
   - Complementary splits (orange-teal)?
   - Analogous color families?
   - Monochromatic/minimal color grading?

6. **Scene adaptation:**
   - Do they grade differently for different scenes, or maintain a consistent style?

Respond in JSON format:
{{
  "temperature_preference": "warm|neutral|cool",
  "temperature_detail": "specific description of their temperature tendencies",
  "contrast_preference": "high|medium|low",
  "lightness_preference": "bright|balanced|dark",
  "saturation_preference": "vivid|moderate|muted",
  "chroma_strategy": "global_boost|selective_vibrance|desaturated",
  "tone_curve_preference": "s_curve|lifted_blacks|linear|varies",
  "color_harmony": "complementary|analogous|monochromatic|mixed",
  "color_tendencies": ["specific color patterns observed, e.g. 'favors teal shadows', 'boosts orange/red warmth'"],
  "effects_notes": "clarity, vignette, and processing preferences",
  "overall_style_summary": "2-3 sentence summary of their style in professional colorist terms",
  "reference_styles": ["closest professional/cinematic style references, e.g. 'Wes Anderson warm pastels', 'Fincher desaturated teal'"]
}}
"""


GRADING_SUGGESTION_PROMPT = """You are an expert colorist. Based on the user's analyzed style profile and this new photograph, generate {num_suggestions} personalized color grading suggestions.

User style profile:
{user_profile}

## YOUR TASK:
Apply the user's preferred aesthetic (temperature, contrast, chroma, tone curve, color harmony) to this specific photograph. Each suggestion should be a variation that aligns with their taste but offers a slightly different interpretation.

## ADAPTATION RULES:
1. **Respect the photograph's existing palette.** Analyze the image's dominant colors and work WITH them. If the image is naturally warm, and the user prefers warm styles, enhance the warmth. If the image is naturally cool but the user prefers warm, create a subtle warm shift that doesn't fight the scene.

2. **Apply the user's profile intelligently:**
   - If they prefer "warm" temperature → shift temperature toward 7000-7500K
   - If they prefer "cool" temperature → shift temperature toward 5500-6000K
   - If they prefer "high contrast" → use S-curve and contrast +20 to +35
   - If they prefer "vivid" → boost vibrance +15 to +25, saturation +5 to +15
   - If they prefer "muted" → reduce saturation -10 to -25, keep vibrance near 0
   - If they prefer "bright" → lift shadows +20 to +40, exposure +0.2 to +0.5
   - If they prefer "dark/moody" → deepen shadows -10 to -30, slight negative exposure

3. **Create meaningful variations between suggestions:**
   - Suggestion 1: Closest match to their profile (most faithful interpretation)
   - Suggestion 2: A bolder version pushing their preferences further
   - Suggestion 3: A complementary variation (e.g., if they prefer warm, try a warm-neutral that's more restrained)

4. **Parameter ranges (professional, not extreme):**
   - exposure: -0.8 to +0.8 EV
   - contrast: -25 to +35
   - highlights/shadows: -50 to +50
   - temperature: 5000-8000K
   - saturation: -30 to +20
   - vibrance: -20 to +30
   - clarity: -10 to 25
   - dehaze: 0 to 15
   - grain: ALWAYS 0
   - vignette: -25 to 0

{schema}

Respond with a JSON array:
[
  {{
    "suggestion_name": "descriptive name",
    "description": "why this suits their style and this specific photo",
    "parameters": <complete ColorParams JSON>
  }},
  ...
]

Output ONLY the JSON array, no other text.
"""
