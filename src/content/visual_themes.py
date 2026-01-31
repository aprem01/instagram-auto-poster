"""
Visual Theme System for Authentic, Diverse Image Generation.

This module provides:
- 25+ diverse visual theme categories
- Anti-AI photography modifiers
- Trending 2024-2025 visual styles
- Dynamic theme selection with anti-repetition logic
"""

import random
from datetime import datetime
from typing import Dict, List, Optional


# ============== VISUAL THEME CATEGORIES ==============
# 25+ diverse themes to avoid repetition

VISUAL_THEME_CATEGORIES = {
    # ABSTRACT HOPE IMAGERY
    "light_rays": {
        "category": "abstract_hope",
        "seasonal": None,
        "prompts": [
            "Soft golden light rays filtering through morning mist, warm atmosphere, shot on iPhone 14, slight lens flare, natural overexposure, grainy film texture",
            "Hazy sunbeams breaking through foggy morning, diffused warm light, documentary style, Canon mirrorless natural grain, imperfect exposure",
            "Gentle sunlight streaming through clouds after rain, atmospheric moisture, Fujifilm colors, slight motion blur, real weather"
        ]
    },

    "bokeh_lights": {
        "category": "abstract_hope",
        "seasonal": None,
        "prompts": [
            "Out-of-focus warm evening lights creating soft bokeh, golden hour fading to dusk, shallow depth of field, nostalgic film grain, accidentally aesthetic",
            "Blurred city lights at twilight forming abstract warm gradient, intentional camera movement, iPhone night mode look, urban poetry"
        ]
    },

    # URBAN SCENES
    "city_dawn": {
        "category": "urban",
        "seasonal": None,
        "prompts": [
            "Empty Chester County main street at first light, small town morning, puddles from overnight rain, documentary photography, authentic local scene",
            "Quiet urban park bench at dawn, dew on grass, soft pink sky reflected in wet pavement, mirrorless camera, realistic morning light"
        ]
    },

    "community_spaces": {
        "category": "urban",
        "seasonal": None,
        "prompts": [
            "Local community garden gate slightly ajar, morning light on weathered wood, authentic neighborhood vibe, iPhone candid style, earth tones",
            "Empty farmers market stalls being set up at dawn, authentic vendor tables, slight motion blur, documentary moment, warm natural light"
        ]
    },

    # HANDS/CONNECTION (NO FACES)
    "supportive_gestures": {
        "category": "connection",
        "seasonal": None,
        "prompts": [
            "Close-up of two hands holding gently, natural window light on real skin texture, warm supportive moment, iPhone photo, slight motion blur, authentic grain",
            "Hands wrapped around warm mug of tea, natural indoor light, cozy sweater sleeve visible, documentary detail shot, Fujifilm colors",
            "Hand gently resting on shoulder cropped no face, natural fabric texture, soft ambient window light, supportive gesture, candid moment"
        ]
    },

    # COZY COMFORT SCENES
    "warm_drinks": {
        "category": "cozy",
        "seasonal": ["fall", "winter"],
        "prompts": [
            "Steaming cup of tea on rainy windowsill, condensation on glass, soft grey outdoor light, cozy indoor atmosphere, authentic home moment, warm ceramic mug",
            "Hot coffee in ceramic mug on worn wooden table, morning light streaks, slight steam visible, candid kitchen moment, natural imperfections"
        ]
    },

    "rain_windows": {
        "category": "cozy",
        "seasonal": ["fall", "spring"],
        "prompts": [
            "Rain droplets on window glass with blurred warm lights inside, moody atmosphere, natural condensation patterns, authentic weather moment, soft focus",
            "Rainy day view from inside, water streaks on glass, muted outdoor colors, warm interior glow reflected, candid home moment"
        ]
    },

    "cozy_textiles": {
        "category": "cozy",
        "seasonal": ["fall", "winter"],
        "prompts": [
            "Soft knit blanket draped over chair arm, afternoon window light, cozy texture detail, warm neutral tones, comfort and safety",
            "Stack of folded sweaters in soft natural light, tactile comfort textures, hygge aesthetic, authentic home moment"
        ]
    },

    # STRENGTH SYMBOLS
    "hills_landscape": {
        "category": "strength",
        "seasonal": None,
        "prompts": [
            "Chester County rolling hills at golden hour, grounding earth tones, morning mist in valleys, documentary landscape, natural colors not oversaturated",
            "Single hill silhouette against dawn sky, simple powerful composition, slight atmospheric haze, film photography aesthetic, strength symbol"
        ]
    },

    "bridges_structures": {
        "category": "strength",
        "seasonal": None,
        "prompts": [
            "Old covered bridge in Chester County, weathered wood textures, afternoon light, authentic Pennsylvania landmark, documentary photography, sturdy structure",
            "Stone arch bridge over quiet stream, solid foundations, natural ivy growth, realistic textures, connection symbol"
        ]
    },

    "anchors_rocks": {
        "category": "strength",
        "seasonal": None,
        "prompts": [
            "Large boulder in meadow with wildflowers around base, grounding presence, morning light, natural landscape detail, stability symbol",
            "Weathered fence post standing firm in field, authentic rural texture, documentary style, endurance and strength"
        ]
    },

    # GROWTH/RENEWAL
    "seedlings": {
        "category": "growth",
        "seasonal": ["spring"],
        "prompts": [
            "Small green seedling pushing through soil, natural garden light, macro detail, real dirt textures, Fujifilm colors, new growth symbol, slightly imperfect framing",
            "First spring shoots emerging from mulch, soft morning light, dewdrops, documentary garden photography, hope and renewal"
        ]
    },

    "spring_blooms": {
        "category": "growth",
        "seasonal": ["spring"],
        "prompts": [
            "Early crocuses emerging through last snow, hopeful spring moment, natural garden setting, candid outdoor photo, slightly overexposed, film grain",
            "Cherry blossoms against soft grey sky, delicate pink petals, not oversaturated, authentic spring colors, bokeh branches"
        ]
    },

    "empty_journals": {
        "category": "growth",
        "seasonal": None,
        "prompts": [
            "Open blank journal on wooden desk, morning light, pen beside it, new beginnings symbol, cozy workspace, authentic stationery, warm tones",
            "Fresh notebook page with soft natural light, possibility and hope, minimal composition, real paper texture"
        ]
    },

    # MOVEMENT/FREEDOM
    "birds_flight": {
        "category": "freedom",
        "seasonal": None,
        "prompts": [
            "Single bird silhouette against soft morning sky, not centered perfectly, motion blur on wings, documentary wildlife, freedom symbol, muted sky colors",
            "Small flock taking flight at dawn, slightly chaotic natural movement, iPhone candid capture, freedom and hope, not overly composed"
        ]
    },

    "butterflies": {
        "category": "freedom",
        "seasonal": ["spring", "summer"],
        "prompts": [
            "Monarch butterfly on wildflower, natural meadow setting, slightly imperfect focus, documentary nature moment, transformation symbol, Pennsylvania garden",
            "Butterfly wing close-up, natural outdoor light, delicate detail, macro photography feel, authentic garden moment"
        ]
    },

    "open_paths": {
        "category": "freedom",
        "seasonal": None,
        "prompts": [
            "Country road stretching ahead through Chester County farmland, morning mist, journey ahead, documentary landscape, authentic rural scene",
            "Walking path through local park, dappled light, leaves on ground, inviting forward motion, candid outdoor scene"
        ]
    },

    # SEASONAL - FALL
    "fall_leaves": {
        "category": "seasonal_fall",
        "seasonal": ["fall"],
        "prompts": [
            "Fallen autumn leaves on wet pavement after rain, rich orange and brown tones, Chester County fall, candid street scene, iPhone snapshot",
            "Single maple leaf on park bench, morning dew, soft autumn light, contemplative moment, documentary detail, nostalgic fall feeling"
        ]
    },

    "fall_harvest": {
        "category": "seasonal_fall",
        "seasonal": ["fall"],
        "prompts": [
            "Pumpkins at local farm stand, rustic wooden display, warm afternoon light, Chester County harvest, authentic market scene",
            "Apple orchard at golden hour, fruit-laden branches, Pennsylvania fall colors, documentary agricultural scene"
        ]
    },

    # SEASONAL - WINTER
    "winter_cozy": {
        "category": "seasonal_winter",
        "seasonal": ["winter"],
        "prompts": [
            "Frosted window with warm interior light glowing through, winter morning, cozy inside vs cold outside, authentic home moment",
            "Knit blanket corner with mug of cocoa, winter afternoon light, texture focus, comfort and warmth, candid home scene"
        ]
    },

    # SEASONAL - SUMMER
    "summer_light": {
        "category": "seasonal_summer",
        "seasonal": ["summer"],
        "prompts": [
            "Long summer evening shadows on grass, golden hour warmth, end of day peace, documentary suburban moment, warm tones",
            "Sunflowers in Chester County field, natural afternoon light, not perfectly arranged, authentic farm aesthetic"
        ]
    },

    "summer_water": {
        "category": "seasonal_summer",
        "seasonal": ["summer"],
        "prompts": [
            "Sprinkler creating rainbow in summer afternoon light, backyard moment, nostalgic summer feeling, candid capture",
            "Creek water sparkling in afternoon sun, Chester County stream, natural woodland setting, peaceful summer scene"
        ]
    },

    # COMMUNITY
    "farmers_market": {
        "category": "community",
        "seasonal": ["spring", "summer", "fall"],
        "prompts": [
            "Local farmers market produce display, natural stall lighting, Chester County community, colorful vegetables, documentary market scene",
            "Fresh flowers at market stand, morning setup, community moment, warm natural light, authentic local business"
        ]
    },

    "parks_benches": {
        "category": "community",
        "seasonal": None,
        "prompts": [
            "Empty park picnic table in morning light, community gathering spot, Chester County park, invitation to connect, natural wood weathering",
            "Two park benches facing each other, conversation space, community connection, soft morning light"
        ]
    },

    # PEACE/HEALING
    "calm_water": {
        "category": "peace",
        "seasonal": None,
        "prompts": [
            "Still pond reflecting sky at dawn, mist on water surface, peaceful Chester County scene, calm and healing, soft natural colors",
            "Gentle stream flowing over rocks, contemplative moment, natural woodland setting, peace and continuity"
        ]
    },

    "candlelight": {
        "category": "remembrance",
        "seasonal": None,
        "prompts": [
            "Single candle flame in soft dark background, warm glow, remembrance moment, not perfectly centered, authentic low light photo, gentle hope",
            "Candle reflected in window at dusk, purple twilight sky visible, memorial moment, natural light mixing, contemplative and hopeful"
        ]
    },

    # MINIMALIST
    "single_flower": {
        "category": "minimalist",
        "seasonal": None,
        "prompts": [
            "Single purple flower against simple background, natural windowsill placement, minimalist hope symbol, candid still life, soft window light",
            "One wildflower in small vase, morning light, simple beauty, authentic home moment, not styled"
        ]
    },

    "simple_objects": {
        "category": "minimalist",
        "seasonal": None,
        "prompts": [
            "Smooth stone on weathered wood, simple grounding moment, natural textures, minimal composition, calming simplicity",
            "Cup of water with lemon slice, morning light through window, simple self-care moment, clean minimal aesthetic"
        ]
    },

    # DREAMY/TRENDING
    "soft_focus": {
        "category": "dreamy",
        "seasonal": None,
        "prompts": [
            "Soft focus morning through sheer curtains, ethereal diffused light, dreamy atmosphere, gentle bokeh, sanctuary feeling, film grain",
            "Intentionally blurred wildflower field, impressionist photography style, soft color washes, peaceful and calming"
        ]
    },

    "golden_hour": {
        "category": "dreamy",
        "seasonal": None,
        "prompts": [
            "Everything bathed in golden hour light, warm amber tones, magic hour photography, nostalgic feeling, soft shadows",
            "Backlit scene at sunset, lens flare included, warm dreamy atmosphere, naturally imperfect exposure"
        ]
    }
}


# ============== CAMERA STYLES ==============
# Make images look like real photos from real devices

CAMERA_STYLES = [
    "shot on iPhone 14 Pro",
    "shot on iPhone 13",
    "Canon mirrorless capture",
    "Fujifilm X-T4 colors",
    "vintage 50mm lens",
    "smartphone snapshot",
    "Ricoh GR street style",
    "old film camera look"
]


# ============== IMPERFECTION MODIFIERS ==============
# Add realistic flaws that real photos have

IMPERFECTION_MODIFIERS = [
    "slight motion blur",
    "not perfectly centered",
    "natural uneven lighting",
    "subtle grain",
    "authentic shadows",
    "minor lens flare",
    "slightly underexposed",
    "slightly overexposed",
    "handheld slight shake",
    "natural color cast"
]


# ============== FILM AESTHETIC MODIFIERS ==============
# Trending film photography looks

FILM_AESTHETIC_MODIFIERS = [
    "film grain texture",
    "35mm film look",
    "Kodak Portra colors",
    "Fujifilm simulation",
    "nostalgic film warmth",
    "faded analog tones",
    "vintage color grading"
]


# ============== ANTI-PERFECTIONISM ==============
# Words that signal authentic moments

ANTI_PERFECTIONISM = [
    "documentary style",
    "candid moment",
    "accidentally aesthetic",
    "authentic captured moment",
    "unposed natural scene",
    "everyday beauty",
    "found moment"
]


# ============== TRENDING STYLES 2024-2025 ==============

TRENDING_STYLES = {
    "soft_dreamy": {
        "modifiers": ["soft focus", "dreamy atmosphere", "hazy light", "gentle bokeh"],
        "colors": "muted pastels, soft whites"
    },
    "earth_tones": {
        "modifiers": ["earthy palette", "warm browns", "sage greens", "terracotta warmth"],
        "colors": "brown, beige, sage, terracotta"
    },
    "nostalgic_film": {
        "modifiers": ["nostalgic grain", "analog warmth", "vintage color cast"],
        "colors": "warm yellows, faded tones"
    },
    "minimalist": {
        "modifiers": ["minimal composition", "negative space", "single subject"],
        "colors": "monochromatic, muted"
    },
    "cozy_hygge": {
        "modifiers": ["cozy atmosphere", "warm glow", "comfort textures"],
        "colors": "warm amber, cream, soft brown"
    }
}


# ============== THEME SELECTOR CLASS ==============

class VisualThemeSelector:
    """Selects visual themes with variety and anti-repetition."""

    def __init__(self):
        self.recently_used = []
        self.max_recent = 8

    def get_current_season(self) -> str:
        """Determine current season."""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        else:
            return "winter"

    def build_authenticity_modifier(self) -> str:
        """Build randomized authenticity modifier string."""
        modifiers = []

        # Camera style
        modifiers.append(random.choice(CAMERA_STYLES))

        # 1-2 imperfections
        imperfections = random.sample(IMPERFECTION_MODIFIERS, k=random.randint(1, 2))
        modifiers.extend(imperfections)

        # Sometimes add film aesthetic
        if random.random() > 0.4:
            modifiers.append(random.choice(FILM_AESTHETIC_MODIFIERS))

        # Anti-perfectionism
        modifiers.append(random.choice(ANTI_PERFECTIONISM))

        return ", ".join(modifiers)

    def select_theme(
        self,
        topic: Optional[str] = None,
        campaign_mode: Optional[str] = None,
        category_preference: Optional[str] = None
    ) -> Dict:
        """
        Select a visual theme with anti-repetition logic.

        Args:
            topic: Post topic for semantic matching
            campaign_mode: awareness, fundraising, events, youth
            category_preference: Specific category to prefer

        Returns:
            Dict with theme_key, prompt, category, modifiers
        """
        current_season = self.get_current_season()

        # Build candidate pool
        candidates = []
        for theme_key, theme_data in VISUAL_THEME_CATEGORIES.items():
            # Skip recently used themes
            if theme_key in self.recently_used[-5:]:
                continue

            weight = 1.0

            # Boost seasonal content
            if theme_data.get("seasonal"):
                if current_season in theme_data["seasonal"]:
                    weight *= 2.5
                else:
                    weight *= 0.3

            # Boost category matches
            if category_preference and category_preference in theme_data["category"]:
                weight *= 3.0

            # Campaign mode matching
            if campaign_mode:
                category = theme_data["category"]
                if campaign_mode == "fundraising" and category in ["community", "connection", "strength"]:
                    weight *= 2.0
                elif campaign_mode == "awareness" and category in ["abstract_hope", "peace", "strength"]:
                    weight *= 2.0
                elif campaign_mode == "youth" and category in ["freedom", "growth", "urban", "dreamy"]:
                    weight *= 2.0

            candidates.append((theme_key, theme_data, weight))

        # Fallback if all themes recently used
        if not candidates:
            self.recently_used = []
            return self.select_theme(topic, campaign_mode, category_preference)

        # Weighted random selection
        total_weight = sum(c[2] for c in candidates)
        r = random.uniform(0, total_weight)

        cumulative = 0
        selected = candidates[0]
        for candidate in candidates:
            cumulative += candidate[2]
            if r <= cumulative:
                selected = candidate
                break

        theme_key, theme_data, _ = selected

        # Select specific prompt from theme
        prompt = random.choice(theme_data["prompts"])

        # Track usage
        self.recently_used.append(theme_key)
        if len(self.recently_used) > self.max_recent:
            self.recently_used.pop(0)

        # Build final prompt with authenticity
        authenticity = self.build_authenticity_modifier()

        # Apply trending style sometimes
        if random.random() > 0.5:
            style_name = random.choice(list(TRENDING_STYLES.keys()))
            style = TRENDING_STYLES[style_name]
            style_mod = random.choice(style["modifiers"])
            final_prompt = f"{prompt}, {authenticity}, {style_mod}, {style['colors']}"
        else:
            final_prompt = f"{prompt}, {authenticity}"

        return {
            "theme_key": theme_key,
            "category": theme_data["category"],
            "prompt": final_prompt,
            "season_matched": current_season in (theme_data.get("seasonal") or [])
        }


# Singleton instance
theme_selector = VisualThemeSelector()


def get_diverse_prompt(topic: str = None, campaign_mode: str = None) -> str:
    """
    Get a diverse, authentic-looking image prompt.

    Args:
        topic: Optional topic for semantic matching
        campaign_mode: Optional campaign mode

    Returns:
        Complete DALL-E prompt
    """
    # Determine category preference from topic
    category_preference = None
    if topic:
        topic_lower = topic.lower()
        if any(w in topic_lower for w in ["hope", "light", "new", "beginning"]):
            category_preference = "abstract_hope"
        elif any(w in topic_lower for w in ["strong", "strength", "resilient"]):
            category_preference = "strength"
        elif any(w in topic_lower for w in ["heal", "peace", "calm", "safe"]):
            category_preference = "peace"
        elif any(w in topic_lower for w in ["grow", "change", "transform"]):
            category_preference = "growth"
        elif any(w in topic_lower for w in ["free", "freedom", "break"]):
            category_preference = "freedom"
        elif any(w in topic_lower for w in ["support", "together", "community"]):
            category_preference = "connection"
        elif any(w in topic_lower for w in ["comfort", "warm", "cozy"]):
            category_preference = "cozy"
        elif any(w in topic_lower for w in ["remember", "honor", "memorial"]):
            category_preference = "remembrance"

    result = theme_selector.select_theme(
        topic=topic,
        campaign_mode=campaign_mode,
        category_preference=category_preference
    )

    # Add safety requirements
    safety = ", no faces, no identifiable people, no text, no words, no letters"

    return result["prompt"] + safety
