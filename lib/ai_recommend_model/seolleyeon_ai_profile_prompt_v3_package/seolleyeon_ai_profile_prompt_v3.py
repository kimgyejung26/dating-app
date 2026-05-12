#!/usr/bin/env python3
"""
Seolleyeon AI Profile Prompt Builder v3

Purpose
-------
Build controlled, metadata-first prompts for Seolleyeon's
"AI에게 내 취향 알려주기" feature.

Core principles
---------------
- AI profiles are synthetic profile assets for cold-start preference learning.
- They should look like realistic adult university-student profile photos.
- They must not look like influencer shoots, idol profiles, school-uniform photos,
  or lightweight dating-app face-rating cards.
- Metadata is kept separate from prompt text so generation distribution can be audited.

Compatibility
-------------
Current CLIP code can read legacy storage paths such as:
    ai_profiles/female/137.png

This builder also emits v3 multi-shot paths such as:
    ai_profiles/female/137/face_card.png
    ai_profiles/female/137/silhouette_card.png
    ai_profiles/female/137/vibe_card.png

Recommended flow
----------------
1. Generate identity-level metadata.
2. Generate canonical face_card first.
3. Generate silhouette_card and vibe_card as same-person variations.
4. QA images manually or with vision checks.
5. Upload approved images to Firebase Storage.
6. Use profileId like female_137 / male_084 as recEvents.targetId.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple


Gender = Literal["female", "male"]
ShotType = Literal["face_card", "silhouette_card", "vibe_card"]

GENDERS: Tuple[Gender, ...] = ("female", "male")
SHOT_TYPES: Tuple[ShotType, ...] = ("face_card", "silhouette_card", "vibe_card")
SCHEMA_VERSION = "ai_profile_image_v3"
PROMPT_BUILDER_VERSION = "ai_profile_prompt_v4"
METADATA_VERSION = "ai_profile_image_v4_compatible"

FACE_TYPE_ORDER: Tuple[str, ...] = (
    "cat_like",
    "dog_like",
    "hamster_like",
    "bear_like",
    "fox_like",
    "deer_like",
    "horse_like",
    "mixed_neutral",
)
FACE_TYPE_ALIASES: Dict[str, str] = {
    "neutral_mixed": "mixed_neutral",
    "mixed_neutral": "mixed_neutral",
}
LOOKS_LEVEL_BANDS: Tuple[str, ...] = ("1.5-2.4", "2.5-3.2", "3.3-3.8", "3.9-4.3", "4.4-5.0")
LOOKS_LEVEL_BAND_RANGES: Dict[str, Tuple[float, float]] = {
    "1.5-2.4": (1.5, 2.4),
    "2.5-3.2": (2.5, 3.2),
    "3.3-3.8": (3.3, 3.8),
    "3.9-4.3": (3.9, 4.3),
    "4.4-5.0": (4.4, 5.0),
}

FACE_TYPE_TARGETS: Dict[str, Dict[str, int]] = {
    "global": {
        "cat_like": 34,
        "dog_like": 38,
        "hamster_like": 24,
        "bear_like": 29,
        "fox_like": 29,
        "deer_like": 43,
        "horse_like": 19,
        "mixed_neutral": 24,
    },
    "female": {
        "cat_like": 17,
        "dog_like": 19,
        "hamster_like": 12,
        "bear_like": 15,
        "fox_like": 14,
        "deer_like": 22,
        "horse_like": 9,
        "mixed_neutral": 12,
    },
    "male": {
        "cat_like": 17,
        "dog_like": 19,
        "hamster_like": 12,
        "bear_like": 14,
        "fox_like": 15,
        "deer_like": 21,
        "horse_like": 10,
        "mixed_neutral": 12,
    },
}

LOOKS_LEVEL_BAND_TARGETS: Dict[str, Dict[str, int]] = {
    "global": {"1.5-2.4": 36, "2.5-3.2": 108, "3.3-3.8": 72, "3.9-4.3": 24, "4.4-5.0": 0},
    "female": {"1.5-2.4": 18, "2.5-3.2": 54, "3.3-3.8": 36, "3.9-4.3": 12, "4.4-5.0": 0},
    "male": {"1.5-2.4": 18, "2.5-3.2": 54, "3.3-3.8": 36, "3.9-4.3": 12, "4.4-5.0": 0},
}

EYEWEAR_TARGETS: Dict[str, Dict[str, int]] = {
    "female": {"with_eyewear": 12, "without_eyewear": 108},
    "male": {"with_eyewear": 24, "without_eyewear": 96},
}
EYEWEAR_RESERVE_TARGETS: Dict[str, Dict[str, int]] = {
    "female": {"with_eyewear": 2, "without_eyewear": 18},
    "male": {"with_eyewear": 4, "without_eyewear": 16},
}
SEASON_TARGETS: Dict[str, int] = {"spring": 60, "summer": 53, "autumn": 79, "winter": 48}


# -----------------------------------------------------------------------------
# Visual translation maps
# -----------------------------------------------------------------------------

FACE_TYPE_WEIGHTS: Dict[str, float] = {
    "cat_like": 0.14,
    "dog_like": 0.16,
    "hamster_like": 0.10,
    "bear_like": 0.12,
    "fox_like": 0.12,
    "deer_like": 0.18,
    "horse_like": 0.08,
    "mixed_neutral": 0.10,
}

FACE_TYPE_VISUAL: Dict[str, str] = {
    "cat_like": (
        "almond-shaped eyes, slightly lifted outer eye corners, a composed expression, "
        "a defined but not sharp jawline"
    ),
    "dog_like": (
        "rounder medium eyes, soft cheeks, a gentle approachable expression, "
        "a warm relaxed smile"
    ),
    "hamster_like": (
        "a compact rounded face, fuller cheeks, a small soft nose, "
        "a warm and gentle expression"
    ),
    "bear_like": (
        "a stable warm impression, slightly broader facial structure, "
        "thicker natural brows, a calm grounded expression"
    ),
    "fox_like": (
        "slightly narrow eyes, a refined face line, a subtle chic expression, "
        "a clean medium nose bridge"
    ),
    "deer_like": (
        "a soft oval face, medium-large calm eyes, a delicate jawline, "
        "a gentle quiet expression"
    ),
    "horse_like": (
        "a slightly longer face proportion, a higher nose bridge, defined cheekbones, "
        "an elegant mature expression"
    ),
    "mixed_neutral": (
        "balanced natural facial proportions, medium eyes, a soft defined jawline, "
        "a calm sincere expression"
    ),
    "neutral_mixed": (
        "balanced natural facial proportions, medium eyes, a soft defined jawline, "
        "a calm sincere expression"
    ),
}

FACE_SHAPE_VISUAL: Dict[str, str] = {
    "soft_oval": "soft oval face shape",
    "round": "naturally rounded face shape",
    "soft_rectangular": "soft rectangular face shape",
    "slightly_long": "slightly longer face shape",
    "heart": "subtle heart-shaped face line",
    "balanced": "balanced natural face shape",
}

EYE_SIZE_VISUAL: Dict[str, str] = {
    "small_medium": "small-to-medium eyes",
    "medium": "medium-sized eyes",
    "medium_large": "medium-large eyes",
    "round_medium": "round medium eyes",
    "narrow_medium": "slightly narrow medium eyes",
}

EYE_TILT_VISUAL: Dict[str, str] = {
    "neutral": "neutral eye tilt",
    "slightly_lifted": "slightly lifted outer eye corners",
    "neutral_slight_downturned": "neutral to slightly downturned eye shape",
    "soft_downturned": "soft slightly downturned eye shape",
}

JAWLINE_VISUAL: Dict[str, str] = {
    "soft": "soft jawline",
    "soft_defined": "soft but defined jawline",
    "defined": "naturally defined jawline",
    "rounded": "rounded jawline",
    "slightly_angular": "slightly angular but realistic jawline",
}

CHEEK_VISUAL: Dict[str, str] = {
    "low": "subtle cheek fullness",
    "moderate": "moderate cheek fullness",
    "full": "fuller cheeks",
    "defined": "lightly defined cheekbones",
}

NOSE_VISUAL: Dict[str, str] = {
    "soft_low": "soft low-to-medium nose bridge",
    "soft_medium": "soft medium nose bridge",
    "medium": "natural medium nose bridge",
    "high_medium": "medium-high nose bridge",
}

LIP_VISUAL: Dict[str, str] = {
    "thin_natural": "natural thinner lips",
    "natural_medium": "natural medium lips",
    "soft_full": "soft fuller lips",
}

BROW_VISUAL: Dict[str, str] = {
    "light_natural": "light natural brows",
    "natural": "natural brows",
    "straight_natural": "natural straight brows",
    "thick_natural": "thicker natural brows",
}

SKIN_VISUAL: Dict[str, str] = {
    "natural": "natural skin texture",
    "natural_clear": "clear natural skin texture",
    "healthy": "healthy natural skin texture",
    "slightly_textured": "real skin texture with very mild imperfections",
}

VIBE_VISUAL: Dict[str, str] = {
    "soft": "soft and gentle mood",
    "chic": "subtle chic mood without looking cold",
    "intellectual": "calm intellectual mood",
    "sporty": "healthy sporty mood",
    "calm": "quiet calm mood",
    "warm": "warm sincere mood",
    "calm_intellectual": "calm intellectual mood",
    "warm_sporty": "warm sporty mood",
    "clear_trust": "clear trustworthy mood",
    "quiet_romance": "quiet romantic but mature mood",
}

BODY_FAT_VISUAL: Dict[str, str] = {
    "slim": "slim build",
    "soft_slim": "soft slim build",
    "healthy_average": "healthy average build",
    "average_soft": "average build with a soft natural body line",
    "fit_natural": "naturally fit build",
    "athletic_natural": "naturally athletic but not bodybuilder-like build",
    "solid_average": "solid average build",
}

FRAME_VISUAL: Dict[str, str] = {
    "small": "small frame",
    "small_medium": "small-to-medium frame",
    "medium": "medium frame",
    "medium_broad": "medium-to-broad frame",
    "broad": "broad frame",
}

MUSCULARITY_VISUAL: Dict[str, str] = {
    "low_natural": "low natural muscularity",
    "natural": "natural muscularity",
    "moderate_natural": "moderate natural muscularity",
    "athletic_moderate": "moderate athletic muscularity",
}

SHOULDER_VISUAL: Dict[str, str] = {
    "narrow": "narrow shoulders",
    "narrow_medium": "narrow-to-medium shoulders",
    "medium": "medium shoulder width",
    "medium_broad": "medium-broad shoulders",
    "broad": "broad shoulders",
}

WAIST_VISUAL: Dict[str, str] = {
    "straight": "straight natural waist line",
    "soft_defined": "softly defined waist",
    "defined": "naturally defined waist",
    "not_emphasized": "waist not strongly emphasized",
}

HIP_VISUAL: Dict[str, str] = {
    "narrow": "narrow hip line",
    "medium": "medium hip line",
    "soft_medium": "soft medium hip line",
    "not_emphasized": "hip line not emphasized",
}

LEG_RATIO_VISUAL: Dict[str, str] = {
    "balanced": "balanced leg proportion",
    "slightly_long": "slightly long leg proportion",
    "long": "long leg proportion while still realistic",
}

TORSO_VISUAL: Dict[str, str] = {
    "short_balanced": "slightly short but balanced torso length",
    "balanced": "balanced torso length",
    "slightly_long": "slightly longer torso length",
}

HEAD_BODY_RATIO_VISUAL: Dict[str, str] = {
    "realistic": "realistic adult head-to-body ratio",
    "slightly_small_head": "slightly small head-to-body impression but still realistic",
    "balanced": "balanced adult head-to-body ratio",
}

HAIR_LENGTH_VISUAL: Dict[str, str] = {
    "short": "short",
    "medium": "medium-length",
    "medium_long": "medium-long",
    "long": "long",
    "bob": "bob-length",
}

HAIR_TEXTURE_VISUAL: Dict[str, str] = {
    "soft_straight": "soft straight",
    "natural_straight": "natural straight",
    "slightly_wavy": "slightly wavy",
    "soft_wavy": "soft wavy",
    "textured": "soft textured",
}

HAIR_COLOR_VISUAL: Dict[str, str] = {
    "natural_black": "natural black",
    "natural_dark_brown": "natural dark brown",
    "dark_brown": "dark brown",
}

BANGS_VISUAL: Dict[str, str] = {
    "none": "no bangs",
    "side_bangs": "soft side bangs",
    "see_through_bangs": "light natural bangs",
    "soft_fringe": "soft natural fringe",
}

MAKEUP_VISUAL: Dict[str, str] = {
    "none": "no visible makeup, clean natural grooming",
    "light_natural": "light natural makeup",
    "natural": "natural makeup",
    "clean_grooming": "clean natural grooming",
}

FASHION_VISUAL: Dict[str, str] = {
    "campus_neat": "neat campus everyday fashion",
    "campus_casual": "casual campus everyday fashion",
    "minimal_clean": "minimal clean everyday fashion",
    "soft_romantic": "soft mature romantic everyday fashion",
    "sporty_casual": "sporty casual campus fashion",
    "intellectual_neat": "intellectual neat campus fashion",
    "classic_neat": "classic neat campus fashion",
    "mori_soft": "soft natural campus fashion",
    "dandy_cozy": "cozy neat campus fashion",
    "dandy_nerd": "bookish neat campus fashion",
    "street_vintage_soft": "soft vintage campus fashion",
    "gorpcore_clean": "clean functional campus fashion",
}

OUTFIT_FIT_VISUAL: Dict[str, str] = {
    "regular_fit": "regular fit",
    "relaxed_fit": "relaxed fit",
    "neat_regular": "neat regular fit",
    "slim_regular": "slim-regular fit without being tight",
}

FACE_CARD_OUTFITS: Dict[Gender, List[str]] = {
    "female": [
        "ivory knit cardigan over a simple inner top",
        "muted rose blouse with a light cardigan",
        "cream sweatshirt with a simple collar detail",
        "soft beige cardigan with a plain white top",
        "minimal navy knit top with a calm campus mood",
    ],
    "male": [
        "simple navy sweatshirt over a white T-shirt",
        "cream knit sweater with a clean crew neck",
        "light gray hoodie layered under a simple jacket",
        "minimal beige cardigan over a plain T-shirt",
        "clean oxford shirt under a casual knit vest",
    ],
}

FULL_BODY_OUTFITS: Dict[Gender, List[str]] = {
    "female": [
        "regular-fit light cardigan, relaxed straight pants, simple campus tote bag, clean sneakers",
        "soft knit top, ankle-length straight skirt, simple tote bag, clean flats or sneakers",
        "minimal sweatshirt, straight denim pants, canvas tote bag, clean sneakers",
        "neat blouse, regular-fit slacks, light cardigan, campus tote bag",
        "soft cardigan, relaxed wide-leg pants, minimal sneakers",
    ],
    "male": [
        "regular-fit navy sweatshirt, straight-fit beige chinos, simple backpack, clean sneakers",
        "cream knit sweater, straight denim pants, canvas backpack, clean sneakers",
        "casual jacket over a plain T-shirt, regular-fit slacks, simple backpack",
        "oxford shirt with a light knit vest, straight chinos, clean sneakers",
        "minimal hoodie, straight-fit dark pants, simple canvas bag, clean sneakers",
    ],
}

VIBE_ACTIVITIES: Dict[Gender, List[str]] = {
    "female": [
        "sitting by a window in a quiet campus cafe, reading lecture notes with a warm drink nearby",
        "walking slowly on a tree-lined campus path while holding a few books",
        "standing in a small exhibition space and looking at a framed artwork",
        "sitting in a quiet library lounge with a notebook and tablet on the table",
        "standing near a campus garden with a relaxed sincere expression",
    ],
    "male": [
        "sitting by a window in a quiet campus cafe, reviewing lecture notes with a warm drink nearby",
        "walking naturally on a tree-lined campus path with a backpack",
        "standing near an outdoor campus basketball court after a casual game, holding a water bottle",
        "sitting in a quiet library lounge with a notebook and laptop on the table",
        "standing near a campus garden with a relaxed sincere expression",
    ],
}

VIBE_LOCATIONS: List[str] = [
    "quiet campus cafe or study lounge, warm neutral interior, no brand logos, no readable text",
    "quiet university walkway with trees and neutral campus buildings, no visible school logo, no readable text",
    "small local exhibition space near campus, neutral walls, no readable text",
    "calm library lounge or study area, no visible school name, no readable text",
    "small park near campus with soft greenery, no identifiable personal information",
]

SKIN_TONE_VISUAL: Dict[str, str] = {
    "fair_warm": "fair warm skin tone with realistic natural texture",
    "light_rosy": "light skin tone with a subtle natural rosy undertone",
    "natural_beige": "natural beige Korean skin tone with realistic texture",
    "medium_warm": "medium warm beige skin tone with healthy natural texture",
    "sun_kissed": "slightly sun-kissed healthy skin tone",
    "warm_tan": "warm lightly tanned skin tone with natural texture",
}

EYEWEAR_VISUAL: Dict[str, str] = {
    "none": "no glasses",
    "thin_round_metal": "thin round metal-frame glasses",
    "black_acetate": "simple black acetate-frame glasses",
    "soft_rectangular_metal": "soft rectangular metal-frame glasses",
    "clear_frame": "subtle clear-frame glasses",
}

SEASON_VISUAL: Dict[str, str] = {
    "spring": "spring campus season",
    "summer": "summer campus season with modest light layers",
    "autumn": "autumn campus season",
    "winter": "winter campus season with readable silhouette",
}

WEATHER_VISUAL: Dict[str, str] = {
    "clear": "clear soft weather",
    "cloudy": "calm cloudy weather",
    "light_rain_after": "after light rain with clean pavement and no face obstruction",
    "snowy": "gentle snowy weather without hiding the face",
    "mild_breeze": "mild breeze with natural movement",
}

TIME_OF_DAY_VISUAL: Dict[str, str] = {
    "daylight": "natural daylight",
    "golden_hour": "soft golden-hour daylight",
    "early_evening": "early evening ambient daylight, still bright enough to read face and body",
}

TEMPERATURE_VISUAL: Dict[str, str] = {
    "warm": "warm temperature feel",
    "mild": "mild temperature feel",
    "cool": "cool temperature feel",
    "cold": "cold temperature feel with moderate layers",
}

LOCATION_CATALOG: Dict[str, Dict[str, Any]] = {
    "campus_walkway": {
        "scene": "quiet tree-lined university walkway with neutral buildings, no visible school logo, no readable text",
        "allowedShots": ["silhouette_card", "vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "safe open campus path with non-identifiable background",
    },
    "campus_cafe": {
        "scene": "quiet campus cafe or study lounge, warm neutral interior, no visible logo, no readable text",
        "allowedShots": ["face_card", "vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "ordinary study-friendly cafe setting",
    },
    "library_lounge": {
        "scene": "calm library lounge or study area, no visible school name, no readable text",
        "allowedShots": ["face_card", "vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "quiet academic interior",
    },
    "lecture_building_hallway": {
        "scene": "neutral lecture building hallway with soft daylight, no visible school name, no readable text",
        "allowedShots": ["silhouette_card", "vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "requires no visible logo, no readable text, no identifiable school name",
    },
    "student_union_lounge": {
        "scene": "student union lounge with neutral seating and soft daylight, no visible logo, no readable text",
        "allowedShots": ["face_card", "vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "requires no visible logo, no readable text, no identifiable school name",
    },
    "small_exhibition": {
        "scene": "small local exhibition space near campus, neutral walls, no readable artwork labels or text",
        "allowedShots": ["vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "quiet cultural visit without readable labels",
    },
    "bookstore_near_campus": {
        "scene": "small independent bookstore near campus with neutral shelves, no readable covers or signs",
        "allowedShots": ["vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "requires no visible logo, no readable text, no identifiable shop name",
    },
    "local_park_near_campus": {
        "scene": "small local park near campus with soft greenery and non-identifiable background",
        "allowedShots": ["silhouette_card", "vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn"],
        "notes": "ordinary near-campus outdoor setting",
    },
    "campus_garden": {
        "scene": "quiet campus garden with soft greenery, no visible school logo, no readable text",
        "allowedShots": ["silhouette_card", "vibe_card"],
        "privacyRisk": "low",
        "logoTextRisk": "low",
        "seasonCompatibility": ["spring", "summer", "autumn"],
        "notes": "calm garden setting",
    },
    "campus_sports_court": {
        "scene": "outdoor campus sports court after casual activity, no team marks, no readable text",
        "allowedShots": ["vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn"],
        "notes": "casual after-activity only, no visible logo, no readable text, no body-focused pose",
    },
    "quiet_study_room": {
        "scene": "quiet study room with neutral desk area, no visible school name, no readable text",
        "allowedShots": ["face_card", "vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "requires no visible logo, no readable text, no identifiable school name",
    },
    "dorm_common_lounge": {
        "scene": "shared dorm common lounge with neutral seating, no private bedroom details, no readable text",
        "allowedShots": ["vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "shared public lounge only, no private intimate room",
    },
    "neutral_outdoor_street_near_campus": {
        "scene": "quiet neutral street near campus with soft daylight and non-identifiable storefronts",
        "allowedShots": ["silhouette_card", "vibe_card"],
        "privacyRisk": "medium",
        "logoTextRisk": "medium",
        "seasonCompatibility": ["spring", "summer", "autumn", "winter"],
        "notes": "requires no visible logo, no readable text, no identifiable shop name",
    },
}

SAFE_FASHION_CATALOG: Dict[Gender, Dict[str, Dict[str, Any]]] = {
    "female": {
        "campus_casual": {
            "outerwear": {"spring": ["light cardigan"], "summer": [None], "autumn": ["cotton overshirt"], "winter": ["short wool-blend jacket"]},
            "tops": ["plain sweatshirt", "soft hoodie", "simple collar knit"],
            "bottoms": ["straight denim pants", "relaxed cotton pants", "wide-leg casual pants"],
            "shoes": ["clean sneakers"],
            "bags": ["canvas_tote", "backpack"],
            "palettes": ["ivory and denim blue", "soft gray and navy", "oatmeal and muted green"],
            "material": "cotton knit and denim",
            "fit": "regular relaxed fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "minimal_clean": {
            "outerwear": {"spring": ["light cardigan"], "summer": [None], "autumn": ["simple jacket"], "winter": ["short neat coat"]},
            "tops": ["fine knit top", "plain oxford shirt", "simple crew-neck knit"],
            "bottoms": ["straight slacks", "straight denim pants", "relaxed ankle pants"],
            "shoes": ["clean sneakers", "simple flats"],
            "bags": ["shoulder_bag", "canvas_tote"],
            "palettes": ["white and charcoal", "navy and beige", "soft gray and cream"],
            "material": "cotton, light wool, and clean woven fabric",
            "fit": "neat regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "soft_romantic": {
            "outerwear": {"spring": ["soft cardigan"], "summer": ["thin cardigan"], "autumn": ["knit cardigan"], "winter": ["short soft coat"]},
            "tops": ["soft knit top", "muted blouse", "round-neck cardigan"],
            "bottoms": ["knee-or-longer skirt", "ankle-length straight skirt", "wide-leg pants"],
            "shoes": ["clean flats", "minimal sneakers"],
            "bags": ["shoulder_bag", "canvas_tote"],
            "palettes": ["muted rose and ivory", "cream and soft brown", "dusty pink and gray"],
            "material": "soft knit and matte woven fabric",
            "fit": "soft regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "intellectual_neat": {
            "outerwear": {"spring": ["light cardigan"], "summer": [None], "autumn": ["knit vest"], "winter": ["short duffle-style coat"]},
            "tops": ["oxford shirt", "knit vest over a shirt", "simple stripe-free shirt"],
            "bottoms": ["straight pants", "neat slacks", "relaxed chinos"],
            "shoes": ["clean sneakers", "simple loafers"],
            "bags": ["canvas_tote", "backpack"],
            "palettes": ["navy and cream", "soft brown and ivory", "gray and white"],
            "material": "cotton shirting and soft knit",
            "fit": "neat regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "classic_neat": {
            "outerwear": {"spring": ["simple blazer"], "summer": [None], "autumn": ["simple blazer"], "winter": ["short wool jacket"]},
            "tops": ["plain knit", "simple blouse", "clean shirt"],
            "bottoms": ["straight slacks", "long skirt", "straight denim pants"],
            "shoes": ["simple loafers", "clean sneakers"],
            "bags": ["shoulder_bag", "canvas_tote"],
            "palettes": ["navy and ivory", "charcoal and cream", "brown and soft gray"],
            "material": "matte woven fabric and knit",
            "fit": "classic regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "mori_soft": {
            "outerwear": {"spring": ["linen cardigan"], "summer": ["thin linen overshirt"], "autumn": ["soft cardigan"], "winter": ["short textured coat"]},
            "tops": ["linen shirt", "soft knit", "plain cotton blouse"],
            "bottoms": ["long skirt", "wide pants", "relaxed straight pants"],
            "shoes": ["simple flats", "minimal sneakers"],
            "bags": ["canvas_tote", "shoulder_bag"],
            "palettes": ["sage and ivory", "linen beige and muted blue", "soft brown and cream"],
            "material": "linen, cotton, and soft knit",
            "fit": "relaxed but readable fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "sporty_casual": {
            "outerwear": {"spring": ["light windbreaker"], "summer": [None], "autumn": ["casual windbreaker"], "winter": ["short fleece jacket"]},
            "tops": ["plain sweatshirt", "casual crew-neck top", "simple hoodie"],
            "bottoms": ["straight jogger pants", "relaxed track pants", "straight denim pants"],
            "shoes": ["clean sneakers"],
            "bags": ["backpack", "canvas_tote"],
            "palettes": ["navy and white", "gray and muted green", "cream and charcoal"],
            "material": "cotton fleece and matte nylon",
            "fit": "relaxed sport-casual fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
    },
    "male": {
        "campus_casual": {
            "outerwear": {"spring": ["light overshirt"], "summer": [None], "autumn": ["casual jacket"], "winter": ["short padded jacket with readable shape"]},
            "tops": ["plain T-shirt", "simple hoodie", "plain sweatshirt"],
            "bottoms": ["chinos", "straight denim pants", "relaxed cotton pants"],
            "shoes": ["clean sneakers"],
            "bags": ["backpack", "canvas_tote"],
            "palettes": ["navy and beige", "gray and denim blue", "cream and olive"],
            "material": "cotton and denim",
            "fit": "regular relaxed fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "minimal_clean": {
            "outerwear": {"spring": ["simple jacket"], "summer": [None], "autumn": ["minimal jacket"], "winter": ["short wool-blend coat"]},
            "tops": ["fine knit", "plain shirt", "clean crew-neck knit"],
            "bottoms": ["slacks", "straight denim pants", "relaxed chinos"],
            "shoes": ["clean sneakers", "simple loafers"],
            "bags": ["backpack", "shoulder_bag"],
            "palettes": ["white and charcoal", "navy and gray", "cream and black"],
            "material": "cotton, light wool, and matte woven fabric",
            "fit": "neat regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "dandy_cozy": {
            "outerwear": {"spring": ["light cardigan"], "summer": [None], "autumn": ["corduroy jacket"], "winter": ["calm short coat"]},
            "tops": ["warm knit", "plain shirt", "soft cardigan"],
            "bottoms": ["corduroy pants", "chinos", "straight slacks"],
            "shoes": ["simple loafers", "clean sneakers"],
            "bags": ["shoulder_bag", "backpack"],
            "palettes": ["brown and cream", "navy and oatmeal", "warm gray and ivory"],
            "material": "knit, corduroy, and cotton",
            "fit": "cozy regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "dandy_nerd": {
            "outerwear": {"spring": ["light cardigan"], "summer": [None], "autumn": ["knit vest"], "winter": ["short wool jacket"]},
            "tops": ["oxford shirt", "check shirt", "knit vest over a shirt"],
            "bottoms": ["chinos", "straight pants", "neat slacks"],
            "shoes": ["clean sneakers", "simple loafers"],
            "bags": ["backpack", "canvas_tote"],
            "palettes": ["navy and cream", "brown and white", "gray and muted blue"],
            "material": "cotton shirting and soft knit",
            "fit": "bookish regular fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "sporty_casual": {
            "outerwear": {"spring": ["light windbreaker"], "summer": [None], "autumn": ["casual windbreaker"], "winter": ["short fleece jacket"]},
            "tops": ["plain sweatshirt", "simple athletic crew-neck top", "casual hoodie"],
            "bottoms": ["track pants", "straight jogger pants", "relaxed cotton pants"],
            "shoes": ["clean sneakers"],
            "bags": ["backpack"],
            "palettes": ["navy and white", "gray and black", "cream and muted green"],
            "material": "cotton fleece and matte nylon",
            "fit": "relaxed sport-casual fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "street_vintage_soft": {
            "outerwear": {"spring": ["work jacket"], "summer": [None], "autumn": ["flannel overshirt"], "winter": ["short work jacket"]},
            "tops": ["plain T-shirt", "flannel shirt", "soft sweatshirt"],
            "bottoms": ["wide denim pants", "straight cotton pants", "relaxed chinos"],
            "shoes": ["clean sneakers"],
            "bags": ["backpack", "shoulder_bag"],
            "palettes": ["washed blue and cream", "brown and navy", "muted green and gray"],
            "material": "cotton twill, flannel, and denim",
            "fit": "relaxed but clean fit",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
        "gorpcore_clean": {
            "outerwear": {"spring": ["functional light jacket"], "summer": ["light nylon overshirt"], "autumn": ["clean functional jacket"], "winter": ["short outdoor-style jacket"]},
            "tops": ["plain sweatshirt", "simple knit", "clean crew-neck top"],
            "bottoms": ["nylon pants", "straight cargo-style pants", "relaxed cotton pants"],
            "shoes": ["clean sneakers"],
            "bags": ["backpack"],
            "palettes": ["olive and charcoal", "gray and navy", "cream and muted green"],
            "material": "matte nylon and cotton",
            "fit": "functional regular fit with face fully visible",
            "bottomVisible": True,
            "silhouetteReadable": True,
        },
    },
}

for _gender_fashion_catalog in SAFE_FASHION_CATALOG.values():
    for _fashion_entry in _gender_fashion_catalog.values():
        _fashion_entry.setdefault("modest", True)

PHOTO_REALISM_VISUAL: Dict[str, str] = {
    "ordinary_smartphone": "realistic ordinary smartphone profile photo with mild natural digital noise",
    "clean_smartphone": "clean smartphone photo, natural color, not glossy commercial photography",
    "casual_profile": "casual profile image with slightly imperfect everyday composition",
}

SPECIAL_CASE_CATALOG: Dict[str, Dict[str, Any]] = {
    "none": {
        "allowedShots": ["face_card", "silhouette_card", "vibe_card"],
        "allowed": True,
        "bottomVisibleOverride": None,
        "notes": None,
        "ratioWeight": 0.94,
    },
    "four_cut_photo": {
        "allowedShots": ["face_card", "vibe_card"],
        "allowed": True,
        "bottomVisibleOverride": False,
        "notes": "simple four-cut photo strip style, natural expression, no booth logo, no readable text, not over-filtered",
        "ratioWeight": 0.015,
    },
    "id_photo": {
        "allowedShots": ["face_card"],
        "allowed": True,
        "bottomVisibleOverride": False,
        "notes": "adult student ID-like neutral portrait, plain clothes, realistic and not high-school-like",
        "ratioWeight": 0.005,
    },
    "snowy_walk": {
        "allowedShots": ["silhouette_card", "vibe_card"],
        "allowed": True,
        "bottomVisibleOverride": None,
        "notes": "gentle winter campus walk, face visible, moderate layers, body shape still readable",
        "ratioWeight": 0.015,
    },
    "exhibition_visit": {
        "allowedShots": ["vibe_card"],
        "allowed": True,
        "bottomVisibleOverride": None,
        "notes": "quiet small exhibition visit, no readable artwork labels or text",
        "ratioWeight": 0.015,
    },
    "campus_sports_after_activity": {
        "allowedShots": ["vibe_card"],
        "allowed": True,
        "bottomVisibleOverride": None,
        "notes": "casual campus sports after-activity moment, no marked jersey, no body-focused pose",
        "ratioWeight": 0.01,
    },
}

BANNED_POSITIVE_TERMS: Tuple[str, ...] = (
    "school uniform",
    "교복",
    "swimsuit",
    "수영복",
    "bikini",
    "lingerie",
    "nightclub",
    "club",
    "bar",
    "LP bar",
    "idol",
    "celebrity",
    "influencer",
    "visible logo",
    "team logo",
    "brand logo",
    "North Face",
    "Nike",
    "Adidas",
    "Musinsa",
    "Barcelona",
    "Bayern",
    "children",
    "아이들과",
    "bathroom",
    "화장실",
    "hotel",
    "luxury hotel",
    "halter neck",
    "tank top",
    "crop top",
    "sexualized",
    "revealing",
    "body-emphasizing",
    "gym mirror",
    "mirror shot in bathroom",
    "balaclava",
    "face-covering mask",
    "sunglasses",
    "tinted lenses",
    "colored fashion lenses",
    "team jersey",
    "street_punk",
    "street punk",
    "glam",
    "ably",
    "teto",
    "face-covering gorpcore",
)
_CATALOG_SAFETY_VALIDATED = False

COMMON_NEGATIVE = (
    "Avoid: childlike appearance, teenager, school uniform, idol trainee look, "
    "celebrity lookalike, influencer photoshoot, glamour studio lighting, "
    "heavy retouching, plastic skin, exaggerated beauty filter, revealing outfit, "
    "swimsuit, lingerie, nightclub, party scene, neon lighting, sexualized pose, "
    "luxury hotel background, identifiable school logo, visible real university name, "
    "text, watermark, distorted face, distorted hands, extra fingers, unrealistic body proportions."
)

QA_CHECKLIST: List[str] = [
    "adult_visual_age_20_plus",
    "not_childlike_or_school_uniform",
    "not_influencer_or_celebrity_like",
    "not_glamour_studio_or_idol_profile",
    "no_revealing_or_sexualized_styling",
    "campus_or_neutral_context",
    "no_readable_school_logo_or_personal_text",
    "realistic_smartphone_profile_photo",
    "face_readable_for_face_card",
    "silhouette_readable_for_silhouette_card",
    "vibe_readable_for_vibe_card",
    "metadata_matches_image",
    "identity_consistent_across_shots",
]


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------


def _pick_weighted(rng: random.Random, weighted: Mapping[str, float]) -> str:
    keys = list(weighted.keys())
    weights = list(weighted.values())
    return rng.choices(keys, weights=weights, k=1)[0]


def _pick(rng: random.Random, values: Sequence[str]) -> str:
    if not values:
        raise ValueError("Cannot pick from an empty sequence.")
    return values[rng.randrange(len(values))]


def _visual(mapping: Mapping[str, str], key: Optional[str], fallback: str = "") -> str:
    if not key:
        return fallback
    return mapping.get(str(key), str(key).replace("_", " "))


def _join_nonempty(parts: Iterable[str], sep: str = ", ") -> str:
    cleaned = [p.strip().rstrip(".") for p in parts if p and p.strip()]
    return sep.join(cleaned)


def _canonical_face_type(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "mixed_neutral"
    return FACE_TYPE_ALIASES.get(raw, raw)


def looks_level_band(value: Any) -> str:
    try:
        level = float(value)
    except (TypeError, ValueError):
        return "2.5-3.2"
    if level <= 2.4:
        return "1.5-2.4"
    if level <= 3.2:
        return "2.5-3.2"
    if level <= 3.8:
        return "3.3-3.8"
    if level <= 4.3:
        return "3.9-4.3"
    if level <= 5.0:
        return "4.4-5.0"
    return "over_5.0"


def _profile_sort_key(spec: Mapping[str, Any]) -> Tuple[int, int]:
    gender_rank = 0 if spec.get("gender") == "female" else 1
    try:
        numeric = int(_profile_number_token(str(spec.get("profileId", ""))))
    except ValueError:
        numeric = 0
    return gender_rank, numeric


def _stable_stride(length: int) -> int:
    if length <= 1:
        return 1
    for stride in (37, 31, 29, 23, 19, 17, 13, 11, 7, 5, 3):
        if length % stride:
            return stride
    return 1


def _spread_values_by_counts(counts: Mapping[str, int], order: Sequence[str], *, seed: int) -> List[str]:
    values: List[str] = []
    for key in order:
        values.extend([key] * max(0, int(counts.get(key, 0))))
    n = len(values)
    if n <= 1:
        return values
    stride = _stable_stride(n)
    positions = [(index * stride + int(seed)) % n for index in range(n)]
    out = [""] * n
    for value, position in zip(values, positions):
        out[position] = value
    return out


def _scale_counts_largest_remainder(
    targets: Mapping[str, int],
    *,
    count: int,
    order: Sequence[str],
) -> Dict[str, int]:
    total = sum(max(0, int(targets.get(key, 0))) for key in order)
    if count <= 0:
        return {key: 0 for key in order}
    if total <= 0:
        out = {key: 0 for key in order}
        out[order[0]] = count
        return out
    raw = {key: max(0, int(targets.get(key, 0))) * int(count) / total for key in order}
    base = {key: int(raw[key]) for key in order}
    remaining = int(count) - sum(base.values())
    ranked = sorted(order, key=lambda key: (raw[key] - base[key], int(targets.get(key, 0)), key), reverse=True)
    for key in ranked[:remaining]:
        base[key] += 1
    return base


def _gender_target_counts(
    targets: Mapping[str, Any],
    gender: Gender,
    count: int,
    order: Sequence[str],
) -> Dict[str, int]:
    source = targets.get(gender) if isinstance(targets.get(gender), Mapping) else targets
    normalized = {key: int(source.get(key, 0)) for key in order} if isinstance(source, Mapping) else {key: 0 for key in order}
    if sum(normalized.values()) == int(count):
        return normalized
    return _scale_counts_largest_remainder(normalized, count=int(count), order=order)


def _eyewear_target_counts(targets: Mapping[str, Any], gender: Gender, count: int) -> Dict[str, int]:
    source = targets.get(gender) if isinstance(targets.get(gender), Mapping) else {}
    source = source if isinstance(source, Mapping) else {}
    with_default = int(source.get("with_eyewear", round(0.1 * count if gender == "female" else 0.2 * count)))
    without_default = int(source.get("without_eyewear", max(0, int(count) - with_default)))
    counts = {"with_eyewear": max(0, with_default), "without_eyewear": max(0, without_default)}
    if sum(counts.values()) == int(count):
        return counts
    return _scale_counts_largest_remainder(counts, count=int(count), order=("with_eyewear", "without_eyewear"))


def _weather_for_season(season: str, rng: random.Random) -> str:
    options = {
        "spring": ["clear", "cloudy", "mild_breeze", "light_rain_after"],
        "summer": ["clear", "cloudy", "mild_breeze", "light_rain_after"],
        "autumn": ["clear", "cloudy", "mild_breeze"],
        "winter": ["clear", "cloudy", "snowy"],
    }
    return _pick(rng, options.get(season, options["spring"]))


def _temperature_for_season(season: str, weather: str) -> str:
    if season == "summer":
        return "warm"
    if season == "winter" or weather == "snowy":
        return "cold"
    if season == "autumn":
        return "cool"
    return "mild"


def _profile_number_token(profile_id: str) -> str:
    m = re.match(r"^(female|male)_(\d+)$", str(profile_id))
    if not m:
        raise ValueError(f"Invalid profileId: {profile_id}. Expected female_137 or male_084.")
    return m.group(2)


def make_profile_id(gender: Gender, numeric_id: int, *, width: int = 3) -> str:
    if gender not in GENDERS:
        raise ValueError(f"gender must be one of {GENDERS}")
    if numeric_id <= 0:
        raise ValueError("numeric_id must be positive")
    token = str(int(numeric_id)).zfill(max(0, int(width))) if width else str(int(numeric_id))
    return f"{gender}_{token}"


def is_ai_profile_id(profile_id: str) -> bool:
    return bool(re.match(r"^(female|male)_\d+$", str(profile_id or "")))


def storage_paths(profile_id: str, shot_type: Optional[ShotType] = None) -> Dict[str, str]:
    """Return legacy and v3 storage paths for an AI profile."""
    m = re.match(r"^(female|male)_(\d+)$", str(profile_id))
    if not m:
        raise ValueError(f"Invalid profileId: {profile_id}")
    gender, pid = m.group(1), m.group(2)
    out = {
        "legacy": f"ai_profiles/{gender}/{pid}.png",
        "face_card": f"ai_profiles/{gender}/{pid}/face_card.png",
        "silhouette_card": f"ai_profiles/{gender}/{pid}/silhouette_card.png",
        "vibe_card": f"ai_profiles/{gender}/{pid}/vibe_card.png",
    }
    if shot_type is not None:
        return {"legacy": out["legacy"], "storagePath": out[shot_type]}
    return out


def looks_level_to_visual(level: float) -> str:
    """Translate internal looksLevel into non-gamified visual language."""
    level = float(level)
    if level < 2.0:
        return (
            "ordinary and natural real student look, mild facial asymmetry allowed, "
            "not polished or model-like"
        )
    if level < 3.0:
        return (
            "neat and likable impression, naturally balanced features, "
            "casual grooming without looking staged"
        )
    if level < 4.0:
        return (
            "realistic attractive appearance, balanced facial symmetry, "
            "clear natural skin, well-kept but not influencer-like"
        )
    return (
        "noticeably attractive but still realistic, refined natural grooming, "
        "not a polished media profile, not a photoshoot model"
    )


def face_to_visual(face: Mapping[str, Any]) -> str:
    face_type = _canonical_face_type(face.get("faceType", "mixed_neutral"))
    parts = [
        FACE_TYPE_VISUAL.get(face_type, FACE_TYPE_VISUAL["mixed_neutral"]),
        _visual(FACE_SHAPE_VISUAL, face.get("faceShape")),
        _visual(EYE_SIZE_VISUAL, face.get("eyeSize")),
        _visual(EYE_TILT_VISUAL, face.get("eyeTilt")),
        _visual(JAWLINE_VISUAL, face.get("jawline")),
        _visual(CHEEK_VISUAL, face.get("cheekFullness")),
        _visual(NOSE_VISUAL, face.get("noseBridge")),
        _visual(LIP_VISUAL, face.get("lipFullness")),
        _visual(BROW_VISUAL, face.get("browThickness")),
        _visual(SKIN_VISUAL, face.get("skinFinish")),
        looks_level_to_visual(float(face.get("looksLevel", 3.0))),
        _visual(VIBE_VISUAL, face.get("vibe")),
    ]
    return _join_nonempty(parts)


def body_to_visual(body: Mapping[str, Any], *, include_internal_weight: bool = False) -> str:
    """Translate body metadata into visible, non-objectifying silhouette language."""
    height = body.get("heightCm")
    height_text = f"height impression around {int(height)}cm" if height else "realistic adult height impression"
    parts = [
        height_text,
        _visual(FRAME_VISUAL, body.get("frame")),
        _visual(BODY_FAT_VISUAL, body.get("bodyFatVisual")),
        _visual(MUSCULARITY_VISUAL, body.get("muscularity")),
        _visual(SHOULDER_VISUAL, body.get("shoulderWidth")),
        _visual(WAIST_VISUAL, body.get("waistDefinition")),
        _visual(HIP_VISUAL, body.get("hipWidth")),
        _visual(LEG_RATIO_VISUAL, body.get("legRatio")),
        _visual(TORSO_VISUAL, body.get("torsoLength")),
        _visual(HEAD_BODY_RATIO_VISUAL, body.get("headBodyRatio")),
        "realistic adult body proportions",
        "natural posture",
    ]
    if include_internal_weight and body.get("weightKgInternal") is not None:
        # Normally not used in prompts. Kept only for debugging.
        parts.append(f"internal metadata weight {body.get('weightKgInternal')}kg")
    return _join_nonempty(parts)


def hair_to_visual(hair: Mapping[str, Any]) -> str:
    parts = [
        _visual(HAIR_LENGTH_VISUAL, hair.get("length")),
        _visual(HAIR_COLOR_VISUAL, hair.get("color")),
        _visual(HAIR_TEXTURE_VISUAL, hair.get("texture")),
    ]
    bangs = _visual(BANGS_VISUAL, hair.get("bangs"))
    base = _join_nonempty(parts)
    if base:
        base = f"{base} hair"
    if bangs and bangs != "no bangs":
        return f"{base} with {bangs}"
    if bangs == "no bangs":
        return f"{base}, no bangs"
    return base


def styling_to_visual(styling: Mapping[str, Any]) -> str:
    return _join_nonempty([
        _visual(MAKEUP_VISUAL, styling.get("makeupLevel")),
        _visual(FASHION_VISUAL, styling.get("fashionMood")),
        _visual(OUTFIT_FIT_VISUAL, styling.get("outfitFit")),
        "campus-appropriate and modest",
    ])


def skin_to_visual(skin: Mapping[str, Any]) -> str:
    tone = _visual(SKIN_TONE_VISUAL, skin.get("tone"), SKIN_TONE_VISUAL["natural_beige"])
    texture = _visual(SKIN_VISUAL, skin.get("texture"), "natural skin texture")
    retouching = str(skin.get("retouching") or "minimal")
    return f"{tone}, {texture}, {retouching} retouching"


def eyewear_prompt_text(accessories: Mapping[str, Any], *, include_none: bool = False) -> str:
    if accessories.get("eyewearGroup") == "glasses":
        eyewear = _visual(EYEWEAR_VISUAL, accessories.get("eyewear"))
        return f"{eyewear}, eyes clearly visible, no lens glare hiding the eyes"
    if include_none:
        return EYEWEAR_VISUAL["none"]
    return ""


def environment_to_visual(environment: Mapping[str, Any]) -> str:
    return _join_nonempty([
        _visual(SEASON_VISUAL, environment.get("season")),
        _visual(WEATHER_VISUAL, environment.get("weather")),
        _visual(TIME_OF_DAY_VISUAL, environment.get("timeOfDay")),
        _visual(TEMPERATURE_VISUAL, environment.get("temperatureFeel")),
    ])


def location_scene(spec: Mapping[str, Any], shot_type: Optional[ShotType] = None) -> str:
    location = spec.get("location", {}) if isinstance(spec.get("location"), Mapping) else {}
    location_type = str(location.get("locationType") or "campus_walkway")
    entry = LOCATION_CATALOG.get(location_type, LOCATION_CATALOG["campus_walkway"])
    allowed = entry.get("allowedShots", [])
    use_spec_scene = True
    if shot_type and shot_type not in allowed:
        fallback_type = "campus_cafe" if shot_type == "face_card" else "campus_walkway"
        if shot_type == "vibe_card" and location_type == "small_exhibition":
            fallback_type = "small_exhibition"
        entry = LOCATION_CATALOG[fallback_type]
        use_spec_scene = False
    scene = str(location.get("scene") or entry["scene"]) if use_spec_scene else str(entry["scene"])
    if location.get("privacyRisk") == "medium" or location.get("logoTextRisk") == "medium":
        scene = f"{scene}, no visible logo, no readable text, no identifiable school name"
    return scene


def fashion_upper_outfit(fashion: Mapping[str, Any]) -> str:
    outerwear = fashion.get("outerwear")
    top = fashion.get("top")
    parts = [str(outerwear) if outerwear else "", str(top) if top else ""]
    return _join_nonempty(parts)


def fashion_full_outfit(fashion: Mapping[str, Any]) -> str:
    return _join_nonempty([
        str(fashion.get("outerwear")) if fashion.get("outerwear") else "",
        str(fashion.get("top")) if fashion.get("top") else "",
        str(fashion.get("bottom")) if fashion.get("bottom") else "",
        str(fashion.get("shoes")) if fashion.get("shoes") else "",
        str(fashion.get("bag")).replace("_", " ") if fashion.get("bag") else "",
    ])


def fashion_to_visual(fashion: Mapping[str, Any], *, full: bool) -> str:
    outfit = fashion_full_outfit(fashion) if full else fashion_upper_outfit(fashion)
    return _join_nonempty([
        outfit,
        _visual(FASHION_VISUAL, fashion.get("category")),
        str(fashion.get("palette") or ""),
        str(fashion.get("material") or ""),
        str(fashion.get("fit") or ""),
        "modest adult campus-appropriate clothing",
    ])


def photo_realism_block(photo: Mapping[str, Any]) -> str:
    realism = _visual(PHOTO_REALISM_VISUAL, photo.get("realismProfile"), PHOTO_REALISM_VISUAL["ordinary_smartphone"])
    return (
        f"{realism}, camera mode {photo.get('cameraMode', 'auto')}, mild natural digital noise, "
        "not a professional photoshoot, slightly imperfect everyday composition, natural skin texture, no heavy beauty filter, "
        "clean but not glossy, not overly sharp commercial photography, authentic campus profile image"
    )


def special_case_note(spec: Mapping[str, Any], shot_type: ShotType) -> str:
    special = spec.get("specialCase", {}) if isinstance(spec.get("specialCase"), Mapping) else {}
    case_type = str(special.get("type") or "none")
    if case_type == "none":
        return ""
    allowed = SPECIAL_CASE_CATALOG.get(case_type, {}).get("allowedShots", [])
    if shot_type not in allowed:
        return ""
    return str(special.get("notes") or SPECIAL_CASE_CATALOG.get(case_type, {}).get("notes") or "")


def subject_block(spec: Mapping[str, Any]) -> str:
    gender = str(spec.get("gender"))
    visual_age = int(spec.get("visualAge", 22))
    adult_label = "adult woman" if gender == "female" else "adult man"
    return (
        f"A realistic adult Korean university student, approximately {visual_age} years old, "
        f"an {adult_label}, natural everyday profile photo, ordinary non-commercial appearance, "
        "authentic campus-based relationship profile style, calm and trustworthy impression."
    )


def identity_consistency_block(spec: Mapping[str, Any]) -> str:
    face = spec.get("face", {}) if isinstance(spec.get("face"), Mapping) else {}
    hair = spec.get("hair", {}) if isinstance(spec.get("hair"), Mapping) else {}
    skin = spec.get("skin", {}) if isinstance(spec.get("skin"), Mapping) else {}
    accessories = spec.get("accessories", {}) if isinstance(spec.get("accessories"), Mapping) else {}
    face_type = FACE_TYPE_VISUAL.get(_canonical_face_type(face.get("faceType", "mixed_neutral")), FACE_TYPE_VISUAL["mixed_neutral"])
    hair_desc = hair_to_visual(hair)
    skin_desc = _visual(SKIN_TONE_VISUAL, skin.get("tone"), "same natural Korean skin tone")
    eyewear_desc = ""
    if accessories.get("eyewearGroup") == "glasses":
        eyewear_desc = f", same {_visual(EYEWEAR_VISUAL, accessories.get('eyewear'))}, eyes clearly visible with no glare"
    return (
        "same person as the canonical portrait, same general facial structure, "
        f"{face_type}, same {skin_desc}, same {hair_desc}, same natural grooming{eyewear_desc}, same adult visual age"
    )


# -----------------------------------------------------------------------------
# Prompt builders
# -----------------------------------------------------------------------------


def build_prompt(spec: Mapping[str, Any], shot_type: ShotType, *, _skip_validation: bool = False) -> str:
    """Build the final English prompt for a single shot family."""
    if shot_type not in SHOT_TYPES:
        raise ValueError(f"shot_type must be one of {SHOT_TYPES}")
    normalized = normalize_spec_defaults(spec)
    if not _skip_validation:
        validate_spec(normalized)

    rng = random.Random(int(normalized.get("identitySeed", 0)) + {"face_card": 11, "silhouette_card": 22, "vibe_card": 33}[shot_type])
    shot_spec = apply_safe_special_case_overrides(normalized, shot_type, rng)
    gender: Gender = shot_spec["gender"]  # type: ignore[assignment]
    face = shot_spec["face"]
    body = shot_spec["body"]
    hair = shot_spec["hair"]
    styling = shot_spec["styling"]
    skin = shot_spec["skin"]
    accessories = shot_spec["accessories"]
    environment = shot_spec["environment"]
    fashion = shot_spec["fashion"]
    photo = shot_spec["photo"]
    subject = subject_block(shot_spec)
    hair_desc = hair_to_visual(hair)
    styling_desc = styling_to_visual(styling)
    eyewear_desc = eyewear_prompt_text(accessories)
    special_note = special_case_note(shot_spec, shot_type)

    vibe_activity = shot_spec.get("vibeActivity") or _pick(random.Random(int(shot_spec.get("identitySeed", 0)) + 500), VIBE_ACTIVITIES[gender])
    vibe_location = location_scene(shot_spec, "vibe_card")
    location_text = location_scene(shot_spec, shot_type)
    season_text = environment_to_visual(environment)
    realism_text = photo_realism_block(photo)

    if shot_type == "face_card":
        eyewear_line = f"\nEyewear:\n{eyewear_desc}.\n" if eyewear_desc else ""
        special_line = f"\nSpecial safe variation:\n{special_note}.\n" if special_note else ""
        return f"""
{subject}

Face details:
{face_to_visual(face)}, {skin_to_visual(skin)}.
{eyewear_line}
Hair and grooming:
{hair_desc}, {styling_desc}.

Upper outfit only:
{fashion_to_visual(fashion, full=False)}. Keep the crop above the waist; lower garments are outside the frame.

Composition:
head-and-shoulders portrait, face clearly visible, {photo.get("gaze")}, natural relaxed expression, simple warm off-white or campus-neutral background, face remains readable.
{special_line}
Lighting and camera:
{_visual(TIME_OF_DAY_VISUAL, environment.get("timeOfDay"))}, {realism_text}.

Rules:
one image only, no text in image, no watermark, no visible logo, adult Korean university student, realistic, calm, trustworthy, ordinary campus profile image.

{COMMON_NEGATIVE}
""".strip()

    if shot_type == "silhouette_card":
        eyewear_line = f" Same {_visual(EYEWEAR_VISUAL, accessories.get('eyewear'))} if the face is visible." if eyewear_desc else ""
        special_line = f"\nSpecial safe variation:\n{special_note}.\n" if special_note else ""
        return f"""
{subject}

Body and silhouette:
{body_to_visual(body)}. Full outfit shows the overall silhouette with modest coverage and no body-focused styling, bottom visible: {bool(fashion.get("bottomVisible"))}, silhouette readable: {bool(fashion.get("silhouetteReadable"))}.{eyewear_line}

Full outfit:
{fashion_to_visual(fashion, full=True)}.

Season and environment:
{season_text}.

Composition:
three-quarter body or full-body photo, {photo.get("pose")}, body proportions readable, no oversized padding, no heavy winter coat hiding body shape, no extreme wide-angle distortion, camera at chest height, enough space around the body, face and posture remain learnable.

Location:
{location_text}.
{special_line}
Lighting and camera:
{realism_text}.

Rules:
one image only, no text in image, no watermark, no visible logo, adult Korean university student, readable modest outfit, authentic campus profile image.

{COMMON_NEGATIVE}
""".strip()

    # vibe_card
    eyewear_line = f"\nEyewear consistency:\nPreserve the same {_visual(EYEWEAR_VISUAL, accessories.get('eyewear'))}; eyes remain clearly visible with no glare.\n" if eyewear_desc else ""
    special_line = f"\nSpecial safe variation:\n{special_note}.\n" if special_note else ""
    return f"""
{subject}

Identity consistency:
{identity_consistency_block(shot_spec)}.
{eyewear_line}
Season and setting:
{season_text}.

Mood and lifestyle:
{vibe_activity}, {_visual(FASHION_VISUAL, fashion.get("category"))}, calm, sincere, trust-based campus relationship platform mood, quiet everyday activity, face recognizable.

Composition:
half-body or environmental portrait, {photo.get("pose")}, relaxed shoulders, gentle expression, more environmental context while preserving identity consistency.

Location:
{vibe_location}.
{special_line}
Lighting and camera:
{realism_text}.

Rules:
one image only, no text in image, no watermark, no visible logo, adult Korean university student, realistic, calm, trustworthy, ordinary campus profile image, not influencer content.

{COMMON_NEGATIVE}
""".strip()


def build_asset_record(spec: Mapping[str, Any], shot_type: ShotType) -> Dict[str, Any]:
    normalized = normalize_spec_defaults(spec)
    profile_id = str(normalized["profileId"])
    paths = storage_paths(profile_id, shot_type)
    metadata = identity_metadata_summary(normalized)
    fashion = normalized["fashion"]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "promptBuilderVersion": PROMPT_BUILDER_VERSION,
        "metadataVersion": METADATA_VERSION,
        "profileId": profile_id,
        "assetId": f"{profile_id}__{shot_type}__v001",
        "gender": normalized["gender"],
        "shotType": shot_type,
        "legacyStoragePath": paths["legacy"],
        "storagePath": paths["storagePath"],
        "prompt": build_prompt(normalized, shot_type),
        "negative": COMMON_NEGATIVE,
        "metadata": normalized,
        "skinTone": metadata["skinTone"],
        "skinTexture": metadata["skinTexture"],
        "eyewear": metadata["eyewear"],
        "eyewearGroup": metadata["eyewearGroup"],
        "hasEyewear": metadata["hasEyewear"],
        "season": metadata["season"],
        "weather": metadata["weather"],
        "timeOfDay": metadata["timeOfDay"],
        "locationType": metadata["locationType"],
        "fashionCategory": metadata["fashionCategory"],
        "fashionPalette": metadata["fashionPalette"],
        "specialCase": metadata["specialCase"],
        "bottomVisible": bool(fashion.get("bottomVisible")),
        "silhouetteReadable": bool(fashion.get("silhouetteReadable")),
        "faceType": metadata["faceType"],
        "looksLevel": metadata["looksLevel"],
        "looksLevelBand": metadata["looksLevelBand"],
        "targetFaceType": metadata["faceType"],
        "targetLooksLevel": metadata["looksLevel"],
        "targetLooksLevelBand": metadata["looksLevelBand"],
        "qaChecklist": QA_CHECKLIST,
    }


def build_asset_records(spec: Mapping[str, Any], shot_types: Sequence[ShotType] = SHOT_TYPES) -> List[Dict[str, Any]]:
    return [build_asset_record(spec, shot_type) for shot_type in shot_types]


def make_rec_event_context(asset_record: Mapping[str, Any]) -> Dict[str, Any]:
    """Context payload to store in recEvents when a user reacts to an AI profile card."""
    return {
        "surface": "ai_preference_onboarding",
        "targetType": "ai_profile",
        "assetId": asset_record["assetId"],
        "shotType": asset_record["shotType"],
        "metadataVersion": str(asset_record.get("metadataVersion") or METADATA_VERSION),
        "storagePath": asset_record["storagePath"],
        "legacyStoragePath": asset_record["legacyStoragePath"],
    }


# -----------------------------------------------------------------------------
# Spec generation
# -----------------------------------------------------------------------------


def _looks_level(rng: random.Random) -> float:
    bucket = rng.random()
    if bucket < 0.15:
        return round(rng.uniform(1.7, 2.4), 1)
    if bucket < 0.60:
        return round(rng.uniform(2.5, 3.2), 1)
    if bucket < 0.90:
        return round(rng.uniform(3.3, 3.8), 1)
    return round(rng.uniform(3.9, 4.2), 1)


def _face_shape_for(face_type: str, rng: random.Random) -> str:
    face_type = _canonical_face_type(face_type)
    options = {
        "cat_like": ["soft_oval", "balanced", "heart"],
        "dog_like": ["round", "soft_oval", "balanced"],
        "hamster_like": ["round", "soft_oval"],
        "bear_like": ["soft_rectangular", "balanced", "round"],
        "fox_like": ["slightly_long", "soft_oval", "heart"],
        "deer_like": ["soft_oval", "slightly_long", "balanced"],
        "horse_like": ["slightly_long", "soft_rectangular"],
        "mixed_neutral": ["balanced", "soft_oval", "soft_rectangular"],
    }
    return _pick(rng, options.get(face_type, options["mixed_neutral"]))


def _eye_size_for(face_type: str, rng: random.Random) -> str:
    face_type = _canonical_face_type(face_type)
    options = {
        "cat_like": ["medium", "narrow_medium", "medium_large"],
        "dog_like": ["round_medium", "medium_large", "medium"],
        "hamster_like": ["round_medium", "medium"],
        "bear_like": ["medium", "round_medium"],
        "fox_like": ["narrow_medium", "medium"],
        "deer_like": ["medium_large", "medium"],
        "horse_like": ["medium", "small_medium"],
        "mixed_neutral": ["medium", "round_medium", "small_medium"],
    }
    return _pick(rng, options.get(face_type, options["mixed_neutral"]))


def _eye_tilt_for(face_type: str, rng: random.Random) -> str:
    face_type = _canonical_face_type(face_type)
    options = {
        "cat_like": ["slightly_lifted", "neutral"],
        "dog_like": ["neutral", "soft_downturned"],
        "hamster_like": ["neutral", "soft_downturned"],
        "bear_like": ["neutral", "soft_downturned"],
        "fox_like": ["slightly_lifted", "neutral"],
        "deer_like": ["neutral_slight_downturned", "neutral"],
        "horse_like": ["neutral", "neutral_slight_downturned"],
        "mixed_neutral": ["neutral", "neutral_slight_downturned", "slightly_lifted"],
    }
    return _pick(rng, options.get(face_type, options["mixed_neutral"]))


def sample_face_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    face_type = _canonical_face_type(_pick_weighted(rng, FACE_TYPE_WEIGHTS))
    looks_level = _looks_level(rng)
    vibe_options = [
        "soft",
        "calm",
        "warm",
        "intellectual",
        "clear_trust",
        "quiet_romance",
    ]
    if face_type in {"cat_like", "fox_like"}:
        vibe_options.extend(["chic", "calm_intellectual"])
    if face_type in {"dog_like", "bear_like"}:
        vibe_options.extend(["warm_sporty", "warm"])
    return {
        "faceType": face_type,
        "looksLevel": looks_level,
        "looksLevelBand": looks_level_band(looks_level),
        "faceShape": _face_shape_for(face_type, rng),
        "eyeSize": _eye_size_for(face_type, rng),
        "eyeTilt": _eye_tilt_for(face_type, rng),
        "jawline": _pick(rng, ["soft", "soft_defined", "defined", "rounded", "slightly_angular"]),
        "cheekFullness": _pick(rng, ["low", "moderate", "full", "defined"]),
        "noseBridge": _pick(rng, ["soft_low", "soft_medium", "medium", "high_medium"]),
        "lipFullness": _pick(rng, ["thin_natural", "natural_medium", "soft_full"]),
        "browThickness": _pick(rng, ["light_natural", "natural", "straight_natural", "thick_natural"]),
        "skinFinish": _pick(rng, ["natural", "natural_clear", "healthy", "slightly_textured"]),
        "vibe": _pick(rng, vibe_options),
    }


def sample_body_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    if gender == "female":
        height = int(round(rng.triangular(155, 174, 163)))
        body_visual = _pick(rng, ["slim", "soft_slim", "healthy_average", "average_soft", "fit_natural"])
        frame = _pick(rng, ["small", "small_medium", "medium"])
        muscularity = _pick(rng, ["low_natural", "natural", "moderate_natural"])
        shoulder = _pick(rng, ["narrow", "narrow_medium", "medium"])
        waist = _pick(rng, ["straight", "soft_defined", "defined", "not_emphasized"])
        hip = _pick(rng, ["narrow", "medium", "soft_medium"])
        weight = int(round(rng.triangular(45, 64, 52)))
    else:
        height = int(round(rng.triangular(168, 188, 176)))
        body_visual = _pick(rng, ["healthy_average", "solid_average", "fit_natural", "athletic_natural"])
        frame = _pick(rng, ["medium", "medium_broad", "broad"])
        muscularity = _pick(rng, ["natural", "moderate_natural", "athletic_moderate"])
        shoulder = _pick(rng, ["medium", "medium_broad", "broad"])
        waist = _pick(rng, ["straight", "not_emphasized", "soft_defined"])
        hip = _pick(rng, ["not_emphasized", "medium"])
        weight = int(round(rng.triangular(58, 84, 70)))

    return {
        "heightCm": height,
        "weightKgInternal": weight,
        "bodyFatVisual": body_visual,
        "frame": frame,
        "muscularity": muscularity,
        "shoulderWidth": shoulder,
        "waistDefinition": waist,
        "hipWidth": hip,
        "legRatio": _pick(rng, ["balanced", "slightly_long", "long"]),
        "torsoLength": _pick(rng, ["short_balanced", "balanced", "slightly_long"]),
        "headBodyRatio": _pick(rng, ["realistic", "balanced", "slightly_small_head"]),
    }


def sample_hair_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    if gender == "female":
        return {
            "length": _pick(rng, ["medium", "medium_long", "long", "bob"]),
            "texture": _pick(rng, ["soft_straight", "natural_straight", "slightly_wavy", "soft_wavy"]),
            "color": _pick(rng, ["natural_black", "natural_dark_brown", "dark_brown"]),
            "bangs": _pick(rng, ["none", "side_bangs", "see_through_bangs"]),
        }
    return {
        "length": _pick(rng, ["short", "medium"]),
        "texture": _pick(rng, ["natural_straight", "soft_straight", "textured", "slightly_wavy"]),
        "color": _pick(rng, ["natural_black", "natural_dark_brown", "dark_brown"]),
        "bangs": _pick(rng, ["none", "soft_fringe"]),
    }


def sample_styling_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    if gender == "female":
        makeup = _pick(rng, ["light_natural", "natural"])
        fashion = _pick(rng, ["campus_neat", "campus_casual", "minimal_clean", "soft_romantic", "intellectual_neat"])
    else:
        makeup = "clean_grooming"
        fashion = _pick(rng, ["campus_casual", "minimal_clean", "sporty_casual", "intellectual_neat", "campus_neat"])
    return {
        "makeupLevel": makeup,
        "fashionMood": fashion,
        "outfitFit": _pick(rng, ["regular_fit", "relaxed_fit", "neat_regular", "slim_regular"]),
        "avoidSexualizedStyling": True,
    }


def sample_skin_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    _ = gender
    return {
        "tone": _pick(rng, list(SKIN_TONE_VISUAL.keys())),
        "texture": _pick(rng, ["natural", "natural_clear", "healthy", "slightly_textured"]),
        "retouching": "minimal",
    }


def sample_accessory_spec(gender: Gender, rng: random.Random, eyewear_group: Optional[str] = None) -> Dict[str, Any]:
    if eyewear_group is None:
        ratio = 0.10 if gender == "female" else 0.20
        eyewear_group = "glasses" if rng.random() < ratio else "none"
    if eyewear_group not in {"none", "glasses"}:
        raise ValueError("eyewear_group must be none, glasses, or None")
    eyewear = "none" if eyewear_group == "none" else _pick(rng, [key for key in EYEWEAR_VISUAL.keys() if key != "none"])
    return {
        "eyewear": eyewear,
        "eyewearGroup": eyewear_group,
        "hasEyewear": eyewear_group == "glasses",
        "hat": _pick(rng, ["none", "none", "none", "simple_cap", "beanie"]),
        "bag": _pick(rng, ["canvas_tote", "backpack", "shoulder_bag", "none"]),
        "jewelry": _pick(rng, ["none", "none", "minimal_silver", "simple_watch"]),
    }


def sample_environment_spec(gender: Gender, rng: random.Random) -> Dict[str, Any]:
    _ = gender
    season = _pick(rng, ["spring", "summer", "autumn", "winter"])
    weather = _weather_for_season(season, rng)
    time_options = ["daylight", "golden_hour", "early_evening"]
    return {
        "season": season,
        "weather": weather,
        "timeOfDay": _pick(rng, time_options),
        "temperatureFeel": _temperature_for_season(season, weather),
    }


def _environment_for_season(season: str, rng: random.Random) -> Dict[str, Any]:
    weather = _weather_for_season(season, rng)
    return {
        "season": season,
        "weather": weather,
        "timeOfDay": _pick(rng, ["daylight", "golden_hour", "early_evening"]),
        "temperatureFeel": _temperature_for_season(season, weather),
    }


def sample_location_spec(gender: Gender, rng: random.Random, shot_type: Optional[ShotType] = None) -> Dict[str, Any]:
    _ = gender
    candidates = [
        (location_type, entry)
        for location_type, entry in LOCATION_CATALOG.items()
        if shot_type is None or shot_type in entry.get("allowedShots", [])
    ]
    if not candidates:
        candidates = [("campus_walkway", LOCATION_CATALOG["campus_walkway"])]
    location_type, entry = candidates[rng.randrange(len(candidates))]
    return {
        "locationType": location_type,
        "scene": entry["scene"],
        "privacyRisk": entry["privacyRisk"],
        "logoTextRisk": entry["logoTextRisk"],
        "allowedShots": list(entry["allowedShots"]),
    }


def _sample_location_for_season(
    gender: Gender,
    rng: random.Random,
    *,
    season: str,
    shot_type: Optional[ShotType] = None,
) -> Dict[str, Any]:
    _ = gender
    candidates = [
        (location_type, entry)
        for location_type, entry in LOCATION_CATALOG.items()
        if (shot_type is None or shot_type in entry.get("allowedShots", []))
        and season in entry.get("seasonCompatibility", [])
    ]
    if not candidates:
        return sample_location_spec(gender, rng, shot_type)
    location_type, entry = candidates[rng.randrange(len(candidates))]
    return {
        "locationType": location_type,
        "scene": entry["scene"],
        "privacyRisk": entry["privacyRisk"],
        "logoTextRisk": entry["logoTextRisk"],
        "allowedShots": list(entry["allowedShots"]),
    }


def _seasonal_outerwear(category: Mapping[str, Any], season: str, rng: random.Random) -> Optional[str]:
    seasonal = category.get("outerwear") if isinstance(category.get("outerwear"), Mapping) else {}
    options = seasonal.get(season) if isinstance(seasonal, Mapping) else None
    if not options:
        options = [None]
    return _pick(rng, list(options))  # type: ignore[arg-type]


def sample_fashion_spec(
    gender: Gender,
    rng: random.Random,
    season: Optional[str] = None,
    shot_type: Optional[ShotType] = None,
) -> Dict[str, Any]:
    _ = shot_type
    season = season or _pick(rng, ["spring", "summer", "autumn", "winter"])
    categories = SAFE_FASHION_CATALOG[gender]
    category = _pick(rng, list(categories.keys()))
    config = categories[category]
    outerwear = _seasonal_outerwear(config, season, rng)
    bag = _pick(rng, config["bags"])
    return {
        "category": category,
        "palette": _pick(rng, config["palettes"]),
        "outerwear": outerwear,
        "top": _pick(rng, config["tops"]),
        "bottom": _pick(rng, config["bottoms"]),
        "shoes": _pick(rng, config["shoes"]),
        "bag": bag,
        "fit": config["fit"],
        "material": config["material"],
        "bottomVisible": bool(config["bottomVisible"]),
        "silhouetteReadable": bool(config["silhouetteReadable"]),
        "modest": True,
    }


def sample_photo_spec(gender: Gender, rng: random.Random, shot_type: Optional[ShotType] = None) -> Dict[str, Any]:
    _ = gender
    pose_by_shot = {
        "face_card": ["relaxed head-and-shoulders pose", "natural slight three-quarter face pose"],
        "silhouette_card": ["standing naturally", "walking slowly with readable posture"],
        "vibe_card": ["naturally engaged in a quiet campus activity", "relaxed environmental portrait pose"],
    }
    gaze_by_shot = {
        "face_card": ["looking near the camera", "gentle direct gaze"],
        "silhouette_card": ["looking naturally forward", "soft gaze near camera"],
        "vibe_card": ["face recognizable with relaxed gaze", "looking naturally toward the activity"],
    }
    crop_by_shot = {
        "face_card": ["head-and-shoulders crop"],
        "silhouette_card": ["three-quarter body or full-body crop"],
        "vibe_card": ["half-body or environmental portrait crop"],
    }
    key = shot_type or "face_card"
    return {
        "realismProfile": _pick(rng, list(PHOTO_REALISM_VISUAL.keys())),
        "cameraMode": "auto",
        "imperfectionLevel": "mild",
        "pose": _pick(rng, pose_by_shot.get(key, pose_by_shot["face_card"])),
        "gaze": _pick(rng, gaze_by_shot.get(key, gaze_by_shot["face_card"])),
        "crop": _pick(rng, crop_by_shot.get(key, crop_by_shot["face_card"])),
    }


def sample_special_case_spec(gender: Gender, rng: random.Random, season: Optional[str] = None) -> Dict[str, Any]:
    _ = gender
    weighted = {key: float(value["ratioWeight"]) for key, value in SPECIAL_CASE_CATALOG.items()}
    case_type = _pick_weighted(rng, weighted)
    if season != "winter" and case_type == "snowy_walk":
        case_type = "none"
    entry = SPECIAL_CASE_CATALOG[case_type]
    return {
        "type": case_type,
        "allowed": bool(entry["allowed"]),
        "bottomVisibleOverride": entry["bottomVisibleOverride"],
        "notes": entry["notes"],
    }


def apply_safe_special_case_overrides(spec: Mapping[str, Any], shot_type: ShotType, rng: random.Random) -> Dict[str, Any]:
    out = normalize_spec_defaults(spec)
    special = out.get("specialCase", {}) if isinstance(out.get("specialCase"), Mapping) else {}
    case_type = str(special.get("type") or "none")
    if case_type == "none":
        return out
    entry = SPECIAL_CASE_CATALOG.get(case_type)
    if not entry or shot_type not in entry.get("allowedShots", []):
        return out
    out["specialCase"] = {**dict(special), "allowed": True, "notes": special.get("notes") or entry.get("notes")}
    fashion = dict(out.get("fashion", {}))
    if entry.get("bottomVisibleOverride") is not None:
        fashion["bottomVisible"] = bool(entry["bottomVisibleOverride"])
    if case_type == "snowy_walk":
        out["environment"] = _environment_for_season("winter", rng)
        fashion["silhouetteReadable"] = True
    if case_type == "exhibition_visit":
        out["location"] = sample_location_spec(str(out["gender"]), rng, "vibe_card")  # type: ignore[arg-type]
        out["location"]["locationType"] = "small_exhibition"
        out["location"]["scene"] = LOCATION_CATALOG["small_exhibition"]["scene"]
    if case_type == "campus_sports_after_activity":
        out["location"] = dict(LOCATION_CATALOG["campus_sports_court"])
        out["location"]["locationType"] = "campus_sports_court"
    out["fashion"] = fashion
    return out


def sample_spec(gender: Gender, numeric_id: int, *, seed: Optional[int] = None, id_width: int = 3) -> Dict[str, Any]:
    if gender not in GENDERS:
        raise ValueError(f"gender must be one of {GENDERS}")
    identity_seed = int(seed if seed is not None else (10_000 if gender == "female" else 20_000) + int(numeric_id))
    rng = random.Random(identity_seed)
    profile_id = make_profile_id(gender, numeric_id, width=id_width)
    visual_age = int(rng.triangular(20, 25, 22))
    if visual_age < 20:
        visual_age = 20

    face = sample_face_spec(gender, rng)
    body = sample_body_spec(gender, rng)
    hair = sample_hair_spec(gender, rng)
    styling = sample_styling_spec(gender, rng)
    skin = sample_skin_spec(gender, rng)
    accessories = sample_accessory_spec(gender, rng)
    environment = sample_environment_spec(gender, rng)
    location = _sample_location_for_season(gender, rng, season=environment["season"], shot_type="vibe_card")
    fashion = sample_fashion_spec(gender, rng, season=environment["season"])
    photo = sample_photo_spec(gender, rng)
    special_case = sample_special_case_spec(gender, rng, season=environment["season"])

    spec: Dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "promptBuilderVersion": PROMPT_BUILDER_VERSION,
        "metadataVersion": METADATA_VERSION,
        "profileId": profile_id,
        "gender": gender,
        "visualAge": visual_age,
        "identitySeed": identity_seed,
        "isSynthetic": True,
        "face": face,
        "body": body,
        "hair": hair,
        "styling": styling,
        "skin": skin,
        "accessories": accessories,
        "environment": environment,
        "location": location,
        "fashion": fashion,
        "photo": photo,
        "specialCase": special_case,
        "shotOutfits": {
            "faceCard": fashion_upper_outfit(fashion) or _pick(rng, FACE_CARD_OUTFITS[gender]),
            "fullBody": fashion_full_outfit(fashion) or _pick(rng, FULL_BODY_OUTFITS[gender]),
        },
        "vibeActivity": _pick(rng, VIBE_ACTIVITIES[gender]),
        "vibeLocation": location["scene"],
        "storagePaths": storage_paths(profile_id),
        "shotPlan": [
            {"shotType": shot_type, "storagePath": storage_paths(profile_id, shot_type)["storagePath"]}
            for shot_type in SHOT_TYPES
        ],
        "qa": {
            "adultVisual": None,
            "campusRealism": None,
            "noSchoolUniform": None,
            "noRevealingClothes": None,
            "noInfluencerPhotoshoot": None,
            "identityConsistentAcrossShots": None,
            "approved": None,
        },
    }
    spec["metadata"] = identity_metadata_summary(spec)
    validate_spec(spec)
    return spec


def identity_metadata_summary(spec: Mapping[str, Any]) -> Dict[str, Any]:
    face = spec.get("face", {}) if isinstance(spec.get("face"), Mapping) else {}
    skin = spec.get("skin", {}) if isinstance(spec.get("skin"), Mapping) else {}
    accessories = spec.get("accessories", {}) if isinstance(spec.get("accessories"), Mapping) else {}
    environment = spec.get("environment", {}) if isinstance(spec.get("environment"), Mapping) else {}
    location = spec.get("location", {}) if isinstance(spec.get("location"), Mapping) else {}
    fashion = spec.get("fashion", {}) if isinstance(spec.get("fashion"), Mapping) else {}
    special = spec.get("specialCase", {}) if isinstance(spec.get("specialCase"), Mapping) else {}
    return {
        "promptBuilderVersion": PROMPT_BUILDER_VERSION,
        "metadataVersion": METADATA_VERSION,
        "faceType": _canonical_face_type(face.get("faceType")),
        "looksLevel": float(face.get("looksLevel", 3.0)),
        "looksLevelBand": str(face.get("looksLevelBand") or looks_level_band(face.get("looksLevel", 3.0))),
        "skinTone": skin.get("tone"),
        "skinTexture": skin.get("texture"),
        "eyewear": accessories.get("eyewear"),
        "eyewearGroup": accessories.get("eyewearGroup"),
        "hasEyewear": bool(accessories.get("hasEyewear")),
        "season": environment.get("season"),
        "weather": environment.get("weather"),
        "timeOfDay": environment.get("timeOfDay"),
        "locationType": location.get("locationType"),
        "fashionCategory": fashion.get("category"),
        "fashionPalette": fashion.get("palette"),
        "specialCase": special.get("type"),
        "bottomVisible": bool(fashion.get("bottomVisible")),
        "silhouetteReadable": bool(fashion.get("silhouetteReadable")),
    }


def _sync_metadata(spec: Dict[str, Any]) -> Dict[str, Any]:
    face = spec.get("face") if isinstance(spec.get("face"), Mapping) else {}
    if isinstance(face, Mapping):
        face_out = dict(face)
        face_out["faceType"] = _canonical_face_type(face_out.get("faceType"))
        face_out["looksLevelBand"] = str(face_out.get("looksLevelBand") or looks_level_band(face_out.get("looksLevel", 3.0)))
        spec["face"] = face_out
    spec["metadata"] = identity_metadata_summary(spec)
    return spec


def _sample_looks_level_in_band(band: str, rng: random.Random) -> float:
    if band == "4.4-5.0":
        raise ValueError("looksLevelBand 4.4-5.0 is blocked for final prompt specs")
    low, high = LOOKS_LEVEL_BAND_RANGES[band]
    return round(rng.uniform(low, high), 1)


def assign_face_type_groups_for_batch(
    specs: Sequence[Mapping[str, Any]],
    targets: Mapping[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    out = [normalize_spec_defaults(spec) for spec in specs]
    for gender in GENDERS:
        indexed = [(index, spec) for index, spec in enumerate(out) if spec.get("gender") == gender]
        indexed.sort(key=lambda pair: _profile_sort_key(pair[1]))
        counts = _gender_target_counts(targets, gender, len(indexed), FACE_TYPE_ORDER)
        sequence = _spread_values_by_counts(counts, FACE_TYPE_ORDER, seed=int(seed) + (0 if gender == "female" else 10_000))
        for offset, ((index, spec), face_type) in enumerate(zip(indexed, sequence)):
            rng = random.Random(int(seed) + int(spec.get("identitySeed", 0)) + offset * 97)
            face = dict(spec["face"])
            face["faceType"] = _canonical_face_type(face_type)
            face["faceShape"] = _face_shape_for(face_type, rng)
            face["eyeSize"] = _eye_size_for(face_type, rng)
            face["eyeTilt"] = _eye_tilt_for(face_type, rng)
            out[index]["face"] = face
            _sync_metadata(out[index])
    return out


def assign_looks_level_bands_for_batch(
    specs: Sequence[Mapping[str, Any]],
    targets: Mapping[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    out = [normalize_spec_defaults(spec) for spec in specs]
    for gender in GENDERS:
        indexed = [(index, spec) for index, spec in enumerate(out) if spec.get("gender") == gender]
        indexed.sort(key=lambda pair: _profile_sort_key(pair[1]))
        counts = _gender_target_counts(targets, gender, len(indexed), LOOKS_LEVEL_BANDS)
        if counts.get("4.4-5.0", 0):
            raise ValueError("Exact looksLevelBand assignment cannot include 4.4-5.0")
        sequence = _spread_values_by_counts(counts, LOOKS_LEVEL_BANDS, seed=int(seed) + (1_000 if gender == "female" else 11_000))
        for offset, ((index, spec), band) in enumerate(zip(indexed, sequence)):
            rng = random.Random(int(seed) + int(spec.get("identitySeed", 0)) + offset * 193)
            face = dict(spec["face"])
            face["looksLevelBand"] = band
            face["looksLevel"] = _sample_looks_level_in_band(band, rng)
            out[index]["face"] = face
            _sync_metadata(out[index])
    return out


def _balanced_eyewear_indices(indexed: Sequence[Tuple[int, Dict[str, Any]]], count: int, seed: int) -> set[int]:
    if count <= 0:
        return set()
    groups: Dict[Tuple[str, str], List[Tuple[int, Dict[str, Any]]]] = {}
    for index, spec in indexed:
        face = spec.get("face", {}) if isinstance(spec.get("face"), Mapping) else {}
        key = (_canonical_face_type(face.get("faceType")), str(face.get("looksLevelBand") or looks_level_band(face.get("looksLevel"))))
        groups.setdefault(key, []).append((index, spec))
    rng = random.Random(seed)
    for rows in groups.values():
        rows.sort(key=lambda pair: str(pair[1].get("profileId")))
        rng.shuffle(rows)
    keys = sorted(groups, key=lambda key: (len(groups[key]), key[0], key[1]), reverse=True)
    selected: set[int] = set()
    cursor = 0
    while len(selected) < count and any(groups.values()):
        key = keys[cursor % len(keys)]
        if groups[key]:
            selected.add(groups[key].pop()[0])
        cursor += 1
        if cursor > len(keys) * 10_000:
            break
    return selected


def assign_eyewear_groups_for_batch(
    specs: Sequence[Mapping[str, Any]],
    targets: Mapping[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    out = [normalize_spec_defaults(spec) for spec in specs]
    for gender in GENDERS:
        indexed = [(index, spec) for index, spec in enumerate(out) if spec.get("gender") == gender]
        indexed.sort(key=lambda pair: _profile_sort_key(pair[1]))
        counts = _eyewear_target_counts(targets, gender, len(indexed))
        selected = _balanced_eyewear_indices(indexed, counts["with_eyewear"], int(seed) + (2_000 if gender == "female" else 12_000))
        for index, spec in indexed:
            eyewear_group = "glasses" if index in selected else "none"
            rng = random.Random(int(seed) + int(spec.get("identitySeed", 0)) + (31 if eyewear_group == "glasses" else 17))
            out[index]["accessories"] = sample_accessory_spec(gender, rng, eyewear_group=eyewear_group)
            _sync_metadata(out[index])
    return out


def assign_environment_for_batch(
    specs: Sequence[Mapping[str, Any]],
    targets: Optional[Mapping[str, int]] = None,
    seed: int = 20260504,
) -> List[Dict[str, Any]]:
    out = [normalize_spec_defaults(spec) for spec in specs]
    order = ("spring", "summer", "autumn", "winter")
    counts = _scale_counts_largest_remainder(targets or SEASON_TARGETS, count=len(out), order=order)
    indexed = sorted(list(enumerate(out)), key=lambda pair: _profile_sort_key(pair[1]))
    sequence = _spread_values_by_counts(counts, order, seed=int(seed) + 3_000)
    for offset, ((index, spec), season) in enumerate(zip(indexed, sequence)):
        gender = spec["gender"]  # type: ignore[assignment]
        rng = random.Random(int(seed) + int(spec.get("identitySeed", 0)) + offset * 53)
        out[index]["environment"] = _environment_for_season(season, rng)
        out[index]["location"] = _sample_location_for_season(gender, rng, season=season, shot_type="vibe_card")
        out[index]["fashion"] = sample_fashion_spec(gender, rng, season=season)
        out[index]["shotOutfits"] = {
            "faceCard": fashion_upper_outfit(out[index]["fashion"]),
            "fullBody": fashion_full_outfit(out[index]["fashion"]),
        }
        out[index]["vibeLocation"] = out[index]["location"]["scene"]
        out[index]["specialCase"] = sample_special_case_spec(gender, rng, season=season)
        _sync_metadata(out[index])
    return out


def _distribution_counts(specs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    face_counts: Counter[str] = Counter()
    looks_counts: Counter[str] = Counter()
    eyewear_counts: Counter[str] = Counter()
    gender_eyewear_counts: Counter[str] = Counter()
    season_counts: Counter[str] = Counter()
    skin_counts: Counter[str] = Counter()
    location_counts: Counter[str] = Counter()
    fashion_counts: Counter[str] = Counter()
    special_counts: Counter[str] = Counter()
    for spec in specs:
        normalized = normalize_spec_defaults(spec)
        face = normalized["face"]
        skin = normalized["skin"]
        accessories = normalized["accessories"]
        environment = normalized["environment"]
        location = normalized["location"]
        fashion = normalized["fashion"]
        special = normalized["specialCase"]
        gender = str(normalized["gender"])
        eyewear_key = "with_eyewear" if accessories["eyewearGroup"] == "glasses" else "without_eyewear"
        face_counts[_canonical_face_type(face.get("faceType"))] += 1
        looks_counts[str(face.get("looksLevelBand") or looks_level_band(face.get("looksLevel")))] += 1
        eyewear_counts[eyewear_key] += 1
        gender_eyewear_counts[f"{gender}_{eyewear_key}"] += 1
        season_counts[str(environment.get("season"))] += 1
        skin_counts[str(skin.get("tone"))] += 1
        location_counts[str(location.get("locationType"))] += 1
        fashion_counts[str(fashion.get("category"))] += 1
        special_counts[str(special.get("type"))] += 1
    for key in FACE_TYPE_ORDER:
        face_counts.setdefault(key, 0)
    for key in LOOKS_LEVEL_BANDS:
        looks_counts.setdefault(key, 0)
    for key in ("with_eyewear", "without_eyewear"):
        eyewear_counts.setdefault(key, 0)
    for gender in GENDERS:
        for key in ("with_eyewear", "without_eyewear"):
            gender_eyewear_counts.setdefault(f"{gender}_{key}", 0)
    gender_eyewear_counts["total_with_eyewear"] = eyewear_counts["with_eyewear"]
    gender_eyewear_counts["total_without_eyewear"] = eyewear_counts["without_eyewear"]
    for key in SEASON_TARGETS:
        season_counts.setdefault(key, 0)
    return {
        "faceType": dict(face_counts),
        "looksLevelBand": dict(looks_counts),
        "eyewear": dict(eyewear_counts),
        "genderEyewear": dict(gender_eyewear_counts),
        "season": dict(season_counts),
        "skinTone": dict(skin_counts),
        "locationType": dict(location_counts),
        "fashionCategory": dict(fashion_counts),
        "specialCase": dict(special_counts),
    }


def audit_prompt_distribution(specs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = _distribution_counts(specs)
    total = len(specs)
    expected: Dict[str, Any] = {}
    mismatches: List[str] = []
    if total == 240:
        expected = {
            "faceType": FACE_TYPE_TARGETS["global"],
            "looksLevelBand": LOOKS_LEVEL_BAND_TARGETS["global"],
            "eyewear": {"with_eyewear": 36, "without_eyewear": 204},
            "genderEyewear": {
                "female_with_eyewear": 12,
                "female_without_eyewear": 108,
                "male_with_eyewear": 24,
                "male_without_eyewear": 96,
                "total_with_eyewear": 36,
                "total_without_eyewear": 204,
            },
            "season": SEASON_TARGETS,
        }
        for section, target in expected.items():
            observed = counts.get(section, {})
            for key, value in target.items():
                if int(observed.get(key, 0)) != int(value):
                    mismatches.append(f"{section}.{key}: expected {value}, got {observed.get(key, 0)}")
    return {
        "promptBuilderVersion": PROMPT_BUILDER_VERSION,
        "metadataVersion": METADATA_VERSION,
        "countingUnit": "identity",
        "identityCount": total,
        "counts": counts,
        "expected": expected,
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def audit_asset_distribution(asset_records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    asset_counts: Counter[str] = Counter()
    profile_to_eyewear: Dict[str, str] = {}
    for asset in asset_records:
        group = str(asset.get("eyewearGroup") or "none")
        key = "with_eyewear" if group == "glasses" else "without_eyewear"
        asset_counts[key] += 1
        profile_to_eyewear[str(asset.get("profileId"))] = key
    identity_counts = Counter(profile_to_eyewear.values())
    return {
        "countingUnit": {"assets": "image", "identities": "identity"},
        "assetCount": len(asset_records),
        "identityCount": len(profile_to_eyewear),
        "eyewearAssetCounts": dict(asset_counts),
        "eyewearIdentityCounts": dict(identity_counts),
    }


def generate_specs(
    *,
    female_count: int = 0,
    male_count: int = 0,
    start_female: int = 1,
    start_male: int = 1,
    seed: int = 20260504,
    id_width: int = 3,
    exact_distribution: bool = True,
) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    # Stable but distinct seeds by profile.
    for i in range(int(female_count)):
        numeric_id = int(start_female) + i
        specs.append(sample_spec("female", numeric_id, seed=seed + numeric_id, id_width=id_width))
    for i in range(int(male_count)):
        numeric_id = int(start_male) + i
        specs.append(sample_spec("male", numeric_id, seed=seed + 100_000 + numeric_id, id_width=id_width))
    if exact_distribution:
        specs = assign_face_type_groups_for_batch(specs, FACE_TYPE_TARGETS, seed)
        specs = assign_looks_level_bands_for_batch(specs, LOOKS_LEVEL_BAND_TARGETS, seed + 101)
        specs = assign_eyewear_groups_for_batch(specs, EYEWEAR_TARGETS, seed + 202)
        specs = assign_environment_for_batch(specs, SEASON_TARGETS, seed + 303)
        for spec in specs:
            validate_spec(spec)
        audit = audit_prompt_distribution(specs)
        if len(specs) == 240 and not audit["passed"]:
            raise ValueError(f"Exact distribution audit failed: {audit['mismatches']}")
    return specs


# -----------------------------------------------------------------------------
# Validation / export
# -----------------------------------------------------------------------------


def split_positive_and_negative_prompt(prompt: str) -> Tuple[str, str]:
    text = str(prompt or "")
    match = re.search(r"(?im)^Avoid:\s*", text)
    if not match:
        match = re.search(r"(?im)^Negative prompt:\s*", text)
    if not match:
        return text, ""
    return text[: match.start()].strip(), text[match.start() :].strip()


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if re.match(r"^[A-Za-z0-9 _-]+$", term):
        escaped = escaped.replace(r"\ ", r"\s+").replace(r"\-", r"[-_ ]?")
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def _is_negated_context(text: str, start: int) -> bool:
    prefix = text[max(0, start - 36) : start].lower()
    return bool(re.search(r"(avoid|no|not|never|without|free of|blocked|forbidden)\s+([\w -]+\s+){0,4}$", prefix))


def scan_prompt_for_banned_terms(prompt: str, *, include_negative: bool = False) -> List[str]:
    positive, negative = split_positive_and_negative_prompt(prompt)
    scan_text = f"{positive}\n{negative}" if include_negative else positive
    hits: List[str] = []
    for term in BANNED_POSITIVE_TERMS:
        pattern = _term_pattern(term)
        for match in pattern.finditer(scan_text):
            if not include_negative and _is_negated_context(scan_text, match.start()):
                continue
            hits.append(term)
            break
    return sorted(set(hits), key=str.lower)


def validate_no_banned_positive_terms(prompt: str) -> None:
    hits = scan_prompt_for_banned_terms(prompt, include_negative=False)
    if hits:
        raise ValueError(f"Prompt positive block contains banned terms: {', '.join(hits)}")


def validate_catalog_safety() -> None:
    global _CATALOG_SAFETY_VALIDATED
    if _CATALOG_SAFETY_VALIDATED:
        return
    rows: List[Tuple[str, str]] = []
    required_location_fields = {"scene", "allowedShots", "privacyRisk", "logoTextRisk", "seasonCompatibility", "notes"}
    for key, value in LOCATION_CATALOG.items():
        missing = required_location_fields - set(value.keys())
        if missing:
            raise ValueError(f"LOCATION_CATALOG.{key} missing fields: {sorted(missing)}")
        if value.get("privacyRisk") == "high" or value.get("logoTextRisk") == "high":
            raise ValueError(f"LOCATION_CATALOG.{key} has high privacy/logo risk")
        if not set(value.get("allowedShots", [])) <= set(SHOT_TYPES):
            raise ValueError(f"LOCATION_CATALOG.{key} has unsupported allowedShots")
        rows.append((f"LOCATION_CATALOG.{key}.scene", str(value.get("scene", ""))))
        rows.append((f"LOCATION_CATALOG.{key}.notes", str(value.get("notes", ""))))
    required_fashion_fields = {
        "outerwear",
        "tops",
        "bottoms",
        "shoes",
        "bags",
        "palettes",
        "material",
        "fit",
        "bottomVisible",
        "silhouetteReadable",
        "modest",
    }
    for gender, categories in SAFE_FASHION_CATALOG.items():
        for category, value in categories.items():
            missing = required_fashion_fields - set(value.keys())
            if missing:
                raise ValueError(f"SAFE_FASHION_CATALOG.{gender}.{category} missing fields: {sorted(missing)}")
            if value.get("modest") is not True or value.get("silhouetteReadable") is not True:
                raise ValueError(f"SAFE_FASHION_CATALOG.{gender}.{category} must be modest and silhouette-readable")
            for field in ("outerwear", "tops", "bottoms", "shoes", "bags", "palettes", "material", "fit"):
                rows.append((f"SAFE_FASHION_CATALOG.{gender}.{category}.{field}", json.dumps(value.get(field, ""), ensure_ascii=False)))
    for key, value in SPECIAL_CASE_CATALOG.items():
        rows.append((f"SPECIAL_CASE_CATALOG.{key}.notes", str(value.get("notes", ""))))
    problems = [(name, scan_prompt_for_banned_terms(text)) for name, text in rows]
    problems = [(name, hits) for name, hits in problems if hits]
    if problems:
        details = "; ".join(f"{name}: {hits}" for name, hits in problems)
        raise ValueError(f"Unsafe catalog positive terms detected: {details}")
    _CATALOG_SAFETY_VALIDATED = True


def normalize_spec_defaults(spec: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = deepcopy(dict(spec))
    gender = out.get("gender")
    if gender not in GENDERS:
        gender = "female"
        out["gender"] = gender
    profile_id = str(out.get("profileId") or make_profile_id(gender, 1))  # type: ignore[arg-type]
    identity_seed = int(out.get("identitySeed", 10_000 if gender == "female" else 20_000))
    rng = random.Random(identity_seed)
    out.setdefault("schemaVersion", SCHEMA_VERSION)
    out.setdefault("promptBuilderVersion", PROMPT_BUILDER_VERSION)
    out.setdefault("metadataVersion", METADATA_VERSION)
    out.setdefault("profileId", profile_id)
    out.setdefault("visualAge", 22)
    out.setdefault("identitySeed", identity_seed)
    out.setdefault("isSynthetic", True)

    if not isinstance(out.get("face"), Mapping):
        out["face"] = sample_face_spec(gender, rng)  # type: ignore[arg-type]
    face = dict(out["face"])
    face["faceType"] = _canonical_face_type(face.get("faceType"))
    face.setdefault("looksLevel", 3.0)
    face["looksLevelBand"] = str(face.get("looksLevelBand") or looks_level_band(face.get("looksLevel")))
    face.setdefault("faceShape", _face_shape_for(face["faceType"], rng))
    face.setdefault("eyeSize", _eye_size_for(face["faceType"], rng))
    face.setdefault("eyeTilt", _eye_tilt_for(face["faceType"], rng))
    face.setdefault("jawline", "soft_defined")
    face.setdefault("cheekFullness", "moderate")
    face.setdefault("noseBridge", "soft_medium")
    face.setdefault("lipFullness", "natural_medium")
    face.setdefault("browThickness", "natural")
    face.setdefault("skinFinish", "natural")
    face.setdefault("vibe", "calm")
    out["face"] = face

    out.setdefault("body", sample_body_spec(gender, rng))  # type: ignore[arg-type]
    out.setdefault("hair", sample_hair_spec(gender, rng))  # type: ignore[arg-type]
    out.setdefault("styling", sample_styling_spec(gender, rng))  # type: ignore[arg-type]
    out.setdefault("skin", {"tone": "natural_beige", "texture": face.get("skinFinish", "natural"), "retouching": "minimal"})
    out.setdefault("accessories", sample_accessory_spec(gender, rng, eyewear_group="none"))  # type: ignore[arg-type]
    out.setdefault("environment", sample_environment_spec(gender, rng))  # type: ignore[arg-type]
    season = str(out["environment"].get("season", "spring")) if isinstance(out.get("environment"), Mapping) else "spring"
    out.setdefault("location", _sample_location_for_season(gender, rng, season=season, shot_type="vibe_card"))  # type: ignore[arg-type]
    out.setdefault("fashion", sample_fashion_spec(gender, rng, season=season))  # type: ignore[arg-type]
    out.setdefault("photo", sample_photo_spec(gender, rng))  # type: ignore[arg-type]
    out.setdefault("specialCase", {"type": "none", "allowed": True, "bottomVisibleOverride": None, "notes": None})

    skin = dict(out["skin"])
    skin.setdefault("tone", "natural_beige")
    skin.setdefault("texture", face.get("skinFinish", "natural"))
    skin.setdefault("retouching", "minimal")
    out["skin"] = skin

    accessories = dict(out["accessories"])
    accessories.setdefault("eyewearGroup", "none")
    accessories.setdefault("eyewear", "none" if accessories.get("eyewearGroup") == "none" else "thin_round_metal")
    accessories.setdefault("hasEyewear", accessories.get("eyewearGroup") == "glasses")
    accessories.setdefault("hat", "none")
    accessories.setdefault("bag", "canvas_tote")
    accessories.setdefault("jewelry", "none")
    out["accessories"] = accessories

    environment = dict(out["environment"])
    environment.setdefault("season", "spring")
    environment.setdefault("weather", "clear")
    environment.setdefault("timeOfDay", "daylight")
    environment.setdefault("temperatureFeel", _temperature_for_season(str(environment["season"]), str(environment["weather"])))
    out["environment"] = environment

    location = dict(out["location"])
    location_type = str(location.get("locationType") or "campus_walkway")
    entry = LOCATION_CATALOG.get(location_type, LOCATION_CATALOG["campus_walkway"])
    location.setdefault("locationType", location_type if location_type in LOCATION_CATALOG else "campus_walkway")
    location.setdefault("scene", entry["scene"])
    location.setdefault("privacyRisk", entry["privacyRisk"])
    location.setdefault("logoTextRisk", entry["logoTextRisk"])
    location.setdefault("allowedShots", list(entry["allowedShots"]))
    out["location"] = location

    fashion = dict(out["fashion"])
    if "category" not in fashion:
        replacement = sample_fashion_spec(gender, rng, season=str(environment["season"]))  # type: ignore[arg-type]
        replacement.update({key: fashion[key] for key in fashion.keys() & {"bottomVisible", "silhouetteReadable", "modest"}})
        fashion = replacement
    fashion.setdefault("modest", True)
    fashion.setdefault("bottomVisible", True)
    fashion.setdefault("silhouetteReadable", True)
    out["fashion"] = fashion

    photo = dict(out["photo"])
    photo.setdefault("realismProfile", "ordinary_smartphone")
    photo.setdefault("cameraMode", "auto")
    photo.setdefault("imperfectionLevel", "mild")
    photo.setdefault("pose", "relaxed natural pose")
    photo.setdefault("gaze", "looking near the camera")
    photo.setdefault("crop", "profile photo crop")
    out["photo"] = photo

    special = dict(out["specialCase"])
    special.setdefault("type", "none")
    entry = SPECIAL_CASE_CATALOG.get(str(special["type"]), SPECIAL_CASE_CATALOG["none"])
    special.setdefault("allowed", bool(entry["allowed"]))
    special.setdefault("bottomVisibleOverride", entry["bottomVisibleOverride"])
    special.setdefault("notes", entry["notes"])
    out["specialCase"] = special

    out.setdefault("shotOutfits", {})
    if isinstance(out["shotOutfits"], Mapping):
        shot_outfits = dict(out["shotOutfits"])
    else:
        shot_outfits = {}
    shot_outfits.setdefault("faceCard", fashion_upper_outfit(fashion))
    shot_outfits.setdefault("fullBody", fashion_full_outfit(fashion))
    out["shotOutfits"] = shot_outfits
    out.setdefault("vibeActivity", _pick(rng, VIBE_ACTIVITIES[gender]))  # type: ignore[index]
    out.setdefault("vibeLocation", location["scene"])
    out.setdefault("storagePaths", storage_paths(str(out["profileId"])))
    out.setdefault(
        "shotPlan",
        [{"shotType": shot_type, "storagePath": storage_paths(str(out["profileId"]), shot_type)["storagePath"]} for shot_type in SHOT_TYPES],
    )
    out.setdefault(
        "qa",
        {
            "adultVisual": None,
            "campusRealism": None,
            "noSchoolUniform": None,
            "noRevealingClothes": None,
            "noInfluencerPhotoshoot": None,
            "identityConsistentAcrossShots": None,
            "approved": None,
        },
    )
    _sync_metadata(out)
    return out


def validate_special_case(spec: Mapping[str, Any]) -> None:
    special = spec.get("specialCase", {}) if isinstance(spec.get("specialCase"), Mapping) else {}
    case_type = str(special.get("type") or "none")
    if case_type not in SPECIAL_CASE_CATALOG:
        raise ValueError(f"Disallowed special case: {case_type}")
    if not bool(special.get("allowed", True)):
        raise ValueError(f"Special case is not allowed: {case_type}")
    if special.get("bottomVisibleOverride") not in (True, False, None):
        raise ValueError("specialCase.bottomVisibleOverride must be true, false, or null")


def validate_spec(spec: Mapping[str, Any], *, strict: bool = False) -> None:
    normalized = dict(spec) if strict else normalize_spec_defaults(spec)
    required_top = [
        "schemaVersion",
        "profileId",
        "gender",
        "visualAge",
        "identitySeed",
        "face",
        "body",
        "hair",
        "styling",
        "skin",
        "accessories",
        "environment",
        "location",
        "fashion",
        "photo",
        "specialCase",
    ]
    for key in required_top:
        if key not in normalized:
            raise ValueError(f"spec missing required key: {key}")
    if normalized["schemaVersion"] != SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {SCHEMA_VERSION}")
    if normalized["gender"] not in GENDERS:
        raise ValueError(f"gender must be one of {GENDERS}")
    if not is_ai_profile_id(str(normalized["profileId"])):
        raise ValueError("profileId must look like female_137 or male_084")
    if int(normalized["visualAge"]) < 20:
        raise ValueError("visualAge must be 20+ for adult university-student profile assets")

    face = normalized["face"]
    body = normalized["body"]
    hair = normalized["hair"]
    styling = normalized["styling"]
    skin = normalized["skin"]
    accessories = normalized["accessories"]
    environment = normalized["environment"]
    location = normalized["location"]
    fashion = normalized["fashion"]
    photo = normalized["photo"]
    if not isinstance(face, Mapping) or not isinstance(body, Mapping) or not isinstance(hair, Mapping) or not isinstance(styling, Mapping):
        raise ValueError("face/body/hair/styling must be objects")
    if not all(isinstance(section, Mapping) for section in (skin, accessories, environment, location, fashion, photo)):
        raise ValueError("skin/accessories/environment/location/fashion/photo must be objects")
    for key in ["faceType", "looksLevel", "faceShape", "eyeSize", "eyeTilt", "jawline"]:
        if key not in face:
            raise ValueError(f"face missing required key: {key}")
    face_type = _canonical_face_type(face.get("faceType"))
    if face_type not in FACE_TYPE_ORDER:
        raise ValueError("face.faceType is not supported")
    for key in ["heightCm", "bodyFatVisual", "frame", "muscularity", "shoulderWidth", "legRatio"]:
        if key not in body:
            raise ValueError(f"body missing required key: {key}")
    if float(face["looksLevel"]) > 4.4:
        raise ValueError("looksLevel above 4.4 is intentionally blocked for MVP distribution")
    if str(face.get("looksLevelBand") or looks_level_band(face["looksLevel"])) == "4.4-5.0":
        raise ValueError("looksLevelBand 4.4-5.0 is intentionally blocked for MVP distribution")
    if int(body["heightCm"]) < 145 or int(body["heightCm"]) > 200:
        raise ValueError("heightCm out of realistic operating range")
    for key in ["length", "texture", "color", "bangs"]:
        if key not in hair:
            raise ValueError(f"hair missing required key: {key}")
    for key in ["makeupLevel", "fashionMood", "outfitFit"]:
        if key not in styling:
            raise ValueError(f"styling missing required key: {key}")
    if skin.get("tone") not in SKIN_TONE_VISUAL:
        raise ValueError("skin.tone is not supported")
    if skin.get("texture") not in SKIN_VISUAL:
        raise ValueError("skin.texture is not supported")
    if skin.get("retouching") != "minimal":
        raise ValueError("skin.retouching must be minimal")
    if accessories.get("eyewearGroup") not in {"none", "glasses"}:
        raise ValueError("accessories.eyewearGroup must be none or glasses")
    if accessories.get("eyewearGroup") == "none" and accessories.get("eyewear") != "none":
        raise ValueError("eyewear must be none when eyewearGroup is none")
    if accessories.get("eyewearGroup") == "glasses" and accessories.get("eyewear") == "none":
        raise ValueError("eyewear must be a glasses style when eyewearGroup is glasses")
    if accessories.get("eyewear") not in EYEWEAR_VISUAL:
        raise ValueError("eyewear is not supported")
    if bool(accessories.get("hasEyewear")) != (accessories.get("eyewearGroup") == "glasses"):
        raise ValueError("accessories.hasEyewear must match eyewearGroup")
    if accessories.get("hat") not in {"none", "simple_cap", "beanie"}:
        raise ValueError("accessories.hat is not supported")
    if accessories.get("bag") not in {"canvas_tote", "backpack", "shoulder_bag", "none"}:
        raise ValueError("accessories.bag is not supported")
    if accessories.get("jewelry") not in {"none", "minimal_silver", "simple_watch"}:
        raise ValueError("accessories.jewelry is not supported")
    accessory_text = json.dumps(accessories, ensure_ascii=False)
    if "mask" in accessory_text.lower() or "balaclava" in accessory_text.lower():
        raise ValueError("face-covering accessories are forbidden")
    if environment.get("season") not in SEASON_VISUAL:
        raise ValueError("environment.season is not supported")
    if environment.get("weather") not in WEATHER_VISUAL:
        raise ValueError("environment.weather is not supported")
    if environment.get("timeOfDay") not in TIME_OF_DAY_VISUAL:
        raise ValueError("environment.timeOfDay is not supported")
    if environment.get("temperatureFeel") not in TEMPERATURE_VISUAL:
        raise ValueError("environment.temperatureFeel is not supported")
    if location.get("privacyRisk") == "high" or location.get("logoTextRisk") == "high":
        raise ValueError("location privacy/logo risk must not be high")
    if location.get("locationType") not in LOCATION_CATALOG:
        raise ValueError("location.locationType is not supported")
    for key in ["scene", "privacyRisk", "logoTextRisk", "allowedShots"]:
        if key not in location:
            raise ValueError(f"location missing required key: {key}")
    if not set(location.get("allowedShots", [])) <= set(SHOT_TYPES):
        raise ValueError("location.allowedShots contains unsupported shot types")
    if fashion.get("category") not in SAFE_FASHION_CATALOG[normalized["gender"]]:
        raise ValueError("fashion.category is not supported")
    for key in ["palette", "outerwear", "top", "bottom", "shoes", "bag", "fit", "material", "bottomVisible", "silhouetteReadable", "modest"]:
        if key not in fashion:
            raise ValueError(f"fashion missing required key: {key}")
    if not isinstance(fashion.get("bottomVisible"), bool):
        raise ValueError("fashion.bottomVisible must be boolean")
    if fashion.get("modest") is not True:
        raise ValueError("fashion.modest must be true")
    if fashion.get("silhouetteReadable") is not True:
        raise ValueError("fashion.silhouetteReadable must be true")
    if photo.get("realismProfile") not in PHOTO_REALISM_VISUAL:
        raise ValueError("photo.realismProfile is not supported")
    if photo.get("cameraMode") != "auto":
        raise ValueError("photo.cameraMode must be auto")
    if photo.get("imperfectionLevel") != "mild":
        raise ValueError("photo.imperfectionLevel must be mild")
    for key in ["pose", "gaze", "crop"]:
        if key not in photo:
            raise ValueError(f"photo missing required key: {key}")
    validate_special_case(normalized)
    metadata_hits = scan_prompt_for_banned_terms(
        json.dumps({"accessories": accessories, "location": location, "fashion": fashion, "specialCase": normalized["specialCase"]}, ensure_ascii=False)
    )
    if metadata_hits:
        raise ValueError(f"Spec metadata contains banned positive terms: {', '.join(metadata_hits)}")
    validate_catalog_safety()
    for shot_type in SHOT_TYPES:
        validate_no_banned_positive_terms(build_prompt(normalized, shot_type, _skip_validation=True))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")


def write_asset_csv(path: Path, asset_records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "profileId",
        "assetId",
        "gender",
        "shotType",
        "legacyStoragePath",
        "storagePath",
        "prompt",
        "faceType",
        "looksLevelBand",
        "skinTone",
        "eyewear",
        "eyewearGroup",
        "hasEyewear",
        "season",
        "locationType",
        "fashionCategory",
        "specialCase",
        "bottomVisible",
        "silhouetteReadable",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in asset_records:
            writer.writerow({col: row.get(col, "") for col in columns})


def export_batch(specs: Sequence[Mapping[str, Any]], out_dir: Path) -> Dict[str, str]:
    normalized_specs = [normalize_spec_defaults(spec) for spec in specs]
    asset_records: List[Dict[str, Any]] = []
    for spec in normalized_specs:
        asset_records.extend(build_asset_records(spec))

    specs_jsonl = out_dir / "ai_profile_specs_v3.jsonl"
    assets_jsonl = out_dir / "ai_profile_assets_v3.jsonl"
    assets_csv = out_dir / "ai_profile_assets_v3.csv"
    report_json = out_dir / "ai_profile_distribution_report_v4.json"
    report = {
        "promptDistribution": audit_prompt_distribution(normalized_specs),
        "assetDistribution": audit_asset_distribution(asset_records),
    }
    write_jsonl(specs_jsonl, normalized_specs)
    write_jsonl(assets_jsonl, asset_records)
    write_asset_csv(assets_csv, asset_records)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "specsJsonl": str(specs_jsonl),
        "assetsJsonl": str(assets_jsonl),
        "assetsCsv": str(assets_csv),
        "distributionReportJson": str(report_json),
        "identityCount": str(len(normalized_specs)),
        "assetCount": str(len(asset_records)),
    }


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Spec JSON must be an object")
    return data


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def cmd_sample(args: argparse.Namespace) -> int:
    spec = sample_spec(args.gender, args.numeric_id, seed=args.seed, id_width=args.id_width)
    if args.as_assets:
        rows = build_asset_records(spec)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    spec = load_json(Path(args.spec))
    validate_spec(spec)
    print(build_prompt(spec, args.shot_type))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    specs = generate_specs(
        female_count=args.female_count,
        male_count=args.male_count,
        start_female=args.start_female,
        start_male=args.start_male,
        seed=args.seed,
        id_width=args.id_width,
        exact_distribution=args.exact_distribution,
    )
    result = export_batch(specs, Path(args.out_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_rec_event_context(args: argparse.Namespace) -> int:
    spec = load_json(Path(args.spec))
    asset = build_asset_record(spec, args.shot_type)
    event = {
        "userId": "<user_id>",
        "type": "like | nope",
        "targetId": spec["profileId"],
        "targetType": "ai_profile",
        "createdAt": "<UTC ISO string>",
        "context": make_rec_event_context(asset),
    }
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Seolleyeon AI profile prompt builder v3")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="Print one sampled identity spec or asset records")
    s.add_argument("--gender", required=True, choices=list(GENDERS))
    s.add_argument("--numeric_id", required=True, type=int)
    s.add_argument("--seed", default=None, type=int)
    s.add_argument("--id_width", default=3, type=int)
    s.add_argument("--as_assets", action="store_true")
    s.set_defaults(func=cmd_sample)

    b = sub.add_parser("batch", help="Generate JSONL/CSV prompt batch")
    b.add_argument("--female_count", default=120, type=int)
    b.add_argument("--male_count", default=120, type=int)
    b.add_argument("--start_female", default=1, type=int)
    b.add_argument("--start_male", default=1, type=int)
    b.add_argument("--seed", default=20260504, type=int)
    b.add_argument("--id_width", default=3, type=int)
    b.add_argument("--out_dir", required=True, type=str)
    b.add_argument("--exact_distribution", dest="exact_distribution", action="store_true", default=True)
    b.add_argument("--no_exact_distribution", dest="exact_distribution", action="store_false")
    b.set_defaults(func=cmd_batch)

    pr = sub.add_parser("prompt", help="Build a prompt from one spec JSON file")
    pr.add_argument("--spec", required=True, type=str)
    pr.add_argument("--shot_type", required=True, choices=list(SHOT_TYPES))
    pr.set_defaults(func=cmd_prompt)

    e = sub.add_parser("rec_event_context", help="Print recEvent context example for one spec and shot")
    e.add_argument("--spec", required=True, type=str)
    e.add_argument("--shot_type", required=True, choices=list(SHOT_TYPES))
    e.set_defaults(func=cmd_rec_event_context)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
