import collections
import html
import json
import random
import re
import uuid
from pathlib import Path
from urllib.parse import quote_plus

import streamlit as st

# ------------------------------------------------------------
# BeautyMix — personal makeup recommendations from your own collection
# Existing products.json and uploads/ files are preserved.
# ------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
UPLOAD_DIR = APP_DIR / "uploads"
LOOK_IMG_DIR = ASSETS_DIR / "looks"          # BeautyMix illustrations (generated)
MY_LOOK_DIR = ASSETS_DIR / "my_looks"        # your own look photos
DATA_FILE = APP_DIR / "products.json"
HISTORY_FILE = APP_DIR / "recommendation_history.json"
UPLOAD_DIR.mkdir(exist_ok=True)
LOOK_IMG_DIR.mkdir(parents=True, exist_ok=True)
MY_LOOK_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["Foundation", "Blush", "Eyeshadow", "Lip"]
CATEGORY_ORDER = {name: i for i, name in enumerate(CATEGORIES)}

# Colour choices: Foundation has NO colour. Blush / Eyeshadow / Lip each get a list.
# "Transparent" is a Lip-only option. Any category can also use a custom colour name.
STANDARD_COLOURS = [
    "Pink", "Light Pink", "Peach", "Red", "Brown", "Nude", "Beige",
    "Purple", "Lavender", "Blue", "Silver", "Green", "Gold", "Orange",
    "Coral", "Rose", "Mauve",
]


def colour_choices_for(category):
    return STANDARD_COLOURS + (["Transparent"] if category == "Lip" else [])


FINISHES = ["Matte", "Natural", "Glowy", "Glossy", "Shimmer", "Glitter"]
OCCASIONS = [
    "University / Everyday", "Casual / Brunch", "Work / Interview",
    "Date / Social Plans", "Party / Night Out", "Special Event / Photoshoot"
]
WEATHERS = ["Hot & Humid", "Mild", "Cold & Dry", "Rainy"]
TIMES = ["10 minutes", "20 minutes", "30 minutes"]
VIBES = [
    "Fresh & Natural", "Soft & Romantic", "Elegant & Polished",
    "Glowy & Radiant", "Bold & Glamorous", "Fun & Experimental", "Surprise Me"
]
LOOKS = [
    "Clean Girl", "Soft Girl", "Soft Glam", "Baddie Glam", "Coquette Makeup",
    "Latte Makeup", "Cloud Skin & Blurred Lips", "Monochromatic Makeup",
    "Icy Glam", "Bold Lip"
]
LOOK_DETAILS = {
    "Clean Girl": ("Fresh, minimal-looking makeup with softly defined features.", "neutral", ["Natural", "Matte", "Glowy"]),
    "Soft Girl": ("Soft pink or peach styling with a gentle, romantic finish.", "cool", ["Natural", "Glowy", "Glossy"]),
    "Soft Glam": ("Balanced definition, blended colour and a polished finish.", "neutral", ["Natural", "Glowy", "Shimmer"]),
    "Baddie Glam": ("More defined eyes or lips with a confident, high-impact finish.", "warm", ["Matte", "Glossy", "Shimmer", "Glitter"]),
    "Coquette Makeup": ("Delicate, romantic styling with soft colour and a glossy touch.", "cool", ["Glowy", "Glossy", "Shimmer"]),
    "Latte Makeup": ("Warm brown, beige and bronze-inspired styling.", "warm", ["Matte", "Natural", "Shimmer"]),
    "Cloud Skin & Blurred Lips": ("Soft-focus, understated colour with a diffused-looking finish.", "neutral", ["Matte", "Natural"]),
    "Monochromatic Makeup": ("Coordinated colour family across cheeks, eyes and lips.", "neutral", ["Natural", "Glowy", "Matte"]),
    "Icy Glam": ("Cool-toned, luminous styling with a frosty shimmer or sparkle.", "cool", ["Glowy", "Shimmer", "Glitter"]),
    "Bold Lip": ("A lip-led look with supporting products kept coordinated.", "neutral", ["Matte", "Glossy", "Glowy"]),
}
# How bold each look is (1 soft .. 3 bold) vs. how bold each occasion calls for
LOOK_INTENSITY = {
    "Clean Girl": 1, "Soft Girl": 1, "Soft Glam": 2, "Baddie Glam": 3, "Coquette Makeup": 2,
    "Latte Makeup": 1, "Cloud Skin & Blurred Lips": 1, "Monochromatic Makeup": 2,
    "Icy Glam": 3, "Bold Lip": 3,
}
OCCASION_INTENSITY = {
    "University / Everyday": 1, "Casual / Brunch": 1, "Work / Interview": 1,
    "Date / Social Plans": 2, "Party / Night Out": 3, "Special Event / Photoshoot": 3,
}
PARTY_OCCASIONS = {"Party / Night Out", "Special Event / Photoshoot"}
GLAM_LOOKS = {"Baddie Glam", "Icy Glam", "Bold Lip", "Soft Glam"}

# How many products per category (a random number inside the range is picked).
# Foundation is always exactly 1. 10 minutes = exactly 1 of each.
# Blush never goes above 2.
TIME_RANGES = {
    "10 minutes": {"Foundation": (1, 1), "Blush": (1, 1), "Eyeshadow": (1, 1), "Lip": (1, 1)},
    "20 minutes": {"Foundation": (1, 1), "Blush": (1, 2), "Eyeshadow": (1, 2), "Lip": (1, 2)},
    "30 minutes": {"Foundation": (1, 1), "Blush": (2, 2), "Eyeshadow": (2, 4), "Lip": (2, 4)},
}

# Colour tone groups (used for coordination AND for the warm/cool finishing tips)
WARM_GROUPS = {"Peach", "Coral", "Orange", "Brown", "Beige", "Gold"}
COOL_GROUPS = {"Pink", "Red", "Purple", "Blue", "Silver", "Green"}

# ------------------------------------------------------------
# Fun, varied recommendation lines (built only from the product's
# category, colour and finish — nothing invented about the product)
# ------------------------------------------------------------
PART = {"Foundation": "skin", "Blush": "cheeks", "Eyeshadow": "lids", "Lip": "lips"}

FINISH_LINES = {
    "Matte": [
        "Matte keeps your {part} velvety and shine-free, with a soft-focus effect.",
        "Think blurred, velvet-soft {part}: that's exactly what matte is about.",
        "No shine here. Matte gives {part} a smooth, filtered-looking finish.",
        "Matte mode on: a calm, flat-finish look for your {part}.",
    ],
    "Natural": [
        "A natural finish lets your {part} look like skin, only better.",
        "Natural means effortless. Your {part} stay true-to-life with zero fuss.",
        "Subtle and skin-like: natural is the 'is she even wearing makeup?' finish.",
        "Keeping it real: a natural finish on your {part} for an easygoing, everyday feel.",
    ],
    "Glowy": [
        "Glowy finish = a lit-from-within feel on your {part}.",
        "Hello, radiance! Glowy gives {part} a fresh, dewy-looking sheen.",
        "Light-catching and luminous: glowy {part} are made for the highlight moments.",
        "A little glow goes a long way. Your {part} get a fresh, radiant lift.",
    ],
    "Glossy": [
        "Glossy brings juicy, reflective shine to your {part}.",
        "Shine on! A glossy finish gives {part} a wet-look, light-catching pop.",
        "Glossy is the finishing wink: a high-shine touch for your {part}.",
        "Sleek and shiny: glossy makes your {part} catch every bit of light.",
    ],
    "Shimmer": [
        "A touch of shimmer gives your {part} a soft, subtle sparkle without going full disco.",
        "Shimmer is gentle light play: subtle shine, no chunky glitter.",
        "Shimmery, not glittery: that soft sheen catches the light when you move.",
        "Just a whisper of sparkle: shimmer keeps your {part} pretty and polished.",
    ],
    "Glitter": [
        "Glitter alert! Visible sparkle that makes your {part} the main event.",
        "This one's for the shine-seekers: glitter is bolder and more visible than shimmer.",
        "Go on, sparkle! Glitter adds statement-making, you-can-see-it sparkle.",
        "Party-ready glitter: bold, visible and impossible to miss on your {part}.",
    ],
}

COLOUR_LINES = {
    "Pink": [
        "{colour} is a sweet, romantic pick that leans cool.",
        "Pink on your {part}? Soft, flirty and very on-theme.",
        "Rosy, pretty and playful: pink is a crowd-pleaser.",
    ],
    "Peach": [
        "{colour} is warm, sunny and just a little juicy. Peachy keen!",
        "A peachy touch on your {part} brings instant sun-kissed energy.",
        "Peach is the soft, warm hug of colours.",
    ],
    "Red": [
        "{colour} is bold and confident, and it won't be ignored.",
        "Red alert: {colour} gives your {part} serious main-character energy.",
        "Classic, daring red: always a statement.",
    ],
    "Brown": [
        "{colour} brings cosy, warm depth. Hello, coffee-shop chic.",
        "Deep and grounded: brown tones add definition with a soft, earthy feel.",
        "Brown tones bring a cosy, bronzed richness.",
    ],
    "Beige": [
        "{colour} keeps things soft, creamy and neutral.",
        "Beige-family shades blend into a calm, understated palette.",
        "Beige is the quiet, creamy neutral that lets the look breathe.",
    ],
    "Purple": [
        "{colour} adds a dreamy, slightly playful twist.",
        "A little purple goes a long way for a fun, cool-toned moment.",
        "Purple tones: a touch of whimsy for your {part}.",
    ],
    "Blue": [
        "{colour} is a fun, unexpected pop that suits an experimental mood.",
        "Cool blue tones bring icy, editorial energy.",
        "Blue is bold, cool and totally out-of-the-box.",
    ],
    "Silver": [
        "{colour} adds a cool, moonlit gleam.",
        "Silver tones are made for frosty, futuristic moments.",
        "Silver brings a polished, futuristic shimmer-of-colour.",
    ],
    "Green": [
        "{colour} is a playful, fresh pop of colour.",
        "A green shade makes the whole look feel more experimental and fun.",
        "Green is fresh, unexpected and full of personality.",
    ],
    "Gold": [
        "{colour} adds a warm, golden touch of luxury.",
        "Golden tones bring that golden-hour glow.",
        "Gold tones glow warm, like a little sunshine in a bottle.",
    ],
    "Orange": [
        "{colour} brings a sunny, warm burst of colour.",
        "Orange tones add juicy, summery energy.",
        "Orange is bright, lively and full of good vibes.",
    ],
    "Coral": [
        "{colour} sits between pink and orange: a lively, warm pop.",
        "Coral on your {part} = instant fresh-and-cheerful.",
        "Coral is cheerful, flattering-looking and full of life.",
    ],
    "Transparent": [
        "Transparent adds sheer, no-colour polish so the rest of your makeup stays the star.",
        "Clear and easy: a transparent shade keeps the look light and uncomplicated.",
        "Sheer and simple: transparent lets your natural look shine through.",
    ],
    "_custom": [
        "Your custom shade, '{colour}', makes this look truly one-of-a-kind.",
        "Love the unique '{colour}': a personal touch only your collection has.",
        "A shade named '{colour}' is proof this collection is yours alone.",
    ],
}

LOOK_LINES = {
    "Clean Girl": ["Clean Girl approved: effortless, fresh and polished.", "Nails the 'I woke up like this (but better)' Clean Girl brief.", "A fresh, put-together pick for your Clean Girl moment."],
    "Soft Girl": ["Soft Girl energy: sweet, gentle and a little dreamy.", "Pretty in pastel: exactly what Soft Girl is about.", "Gentle, rosy and sweet: a Soft Girl match."],
    "Soft Glam": ["Soft Glam ready: polished with a touch of drama.", "Fits the 'dressed up, not overdone' Soft Glam finish.", "Adds the polish that Soft Glam is known for."],
    "Baddie Glam": ["Baddie Glam mode: confident and a little extra.", "Turns the volume up for a high-impact Baddie Glam moment.", "Brings the confident, sculpted energy of Baddie Glam."],
    "Coquette Makeup": ["Coquette dreams: dainty, romantic and bow-worthy.", "Very Coquette: delicate with a flirty finish.", "A delicate, ribbon-and-roses kind of Coquette pick."],
    "Latte Makeup": ["Latte Makeup vibes: cosy, warm and café-ready.", "Stir in some creamy neutrals. Very Latte Makeup.", "Warm, cosy and ready for your Latte Makeup look."],
    "Cloud Skin & Blurred Lips": ["Cloud Skin & Blurred Lips: soft-focus, diffused and dreamy.", "Blur it out! It fits the cloud-soft, understated mood.", "Soft, hazy and smudge-friendly: a Cloud Skin match."],
    "Monochromatic Makeup": ["Monochrome magic: one colour story across the face.", "Ties right into the all-one-family Monochromatic idea.", "Helps keep the whole face in one colour story."],
    "Icy Glam": ["Icy Glam ready: frosty, luminous and a bit futuristic.", "Chill factor unlocked: perfect for Icy Glam sparkle.", "A frosty, sparkly pick that suits Icy Glam."],
    "Bold Lip": ["Bold Lip focus: this one is all about making a statement.", "Lip-led looks love this: the lip takes centre stage.", "Supports a statement lip without stealing its spotlight."],
}

WEATHER_LINES = {
    "Hot & Humid": {
        "top": ["Hot and humid? Matte foundation is the move for a fresh-looking base.", "Humidity, meet matte: the weather says this is the one."],
        "alt": ["Not the top pick for humid days, but a solid backup.", "A balanced runner-up for hot and humid weather."],
    },
    "Cold & Dry": {
        "top": ["Cold and dry? A glowy base brings back that lit-from-within look.", "Winter-skin rescue: glowy foundation for cold, dry days."],
        "alt": ["Not the top pick for cold, dry days, but a solid backup.", "A balanced runner-up for cold and dry weather."],
    },
    "Mild": {
        "top": ["Mild weather means natural-foundation weather. Easy breezy.", "Not too hot, not too cold: natural foundation fits perfectly."],
        "alt": ["Not the top pick for mild days, but it can still work.", "A flexible runner-up for mild weather."],
    },
    "Rainy": {
        "top": ["Rainy day? Matte is one great option for a steady base.", "Grey skies, steady base: matte is a good rainy-day choice."],
        "alt": ["Natural is a balanced option for rainy days.", "Easygoing and natural for a rainy-day base."],
    },
}

PAIR_LINES = {
    "same": [
        "Both this and your {other} sit in the {group} family, a tidy colour story.",
        "Shares the {group} family with your {other}, so the two feel like a set.",
        "Teams up with your {other} through a shared {group} tone.",
    ],
    "tone": [
        "Both this and your {other} lean {tone}, so nothing clashes.",
        "A {tone}-toned duo with your {other}.",
        "Plays nicely with your {other}: same {tone} mood.",
    ],
    "contrast": [
        "Pairs this {finish} finish with the {ofinish} finish of your {other} for a nice mix of textures.",
        "{finish} here, {ofinish} on your {other}: contrast that keeps the look interesting.",
        "Texture play: {finish} next to your {other}'s {ofinish}.",
    ],
    "harmony": [
        "Shares the {finish} finish of your {other}, so the textures feel connected.",
        "Same {finish} finish as your {other} keeps the whole look consistent.",
        "Both {finish}: this and your {other} read as one cohesive finish.",
    ],
    "foundation": [
        "Echoes the {finish} finish of your foundation, so base and colour feel connected.",
        "Same {finish} finish as your foundation for a seamless look.",
    ],
}
OCCASION_LINES = {
    "easy": ["Easy and wearable for {occasion}.", "A practical pick for {occasion}."],
    "party": ["Adds the extra shine that {occasion} calls for.", "Made for {occasion}: a little more sparkle and shine."],
}
PALETTE_MULTI_LINES = [
    "A multi-shade pick: {colour} lets you blend from light to deep.",
    "Several shades in one ({colour}), so you can build the look step by step.",
]
GENERIC_LINES = [
    "Straight from your own collection and ready to work with this look.",
    "A great reason to wear what you already own.",
]

# Colour story of each look (group -> bonus). Bold Lip is set per category.
LOOK_PALETTE = {
    "Clean Girl": {"Pink": 2.5, "Peach": 2.5, "Beige": 2.5, "Transparent": 2.5, "Brown": 1},
    "Soft Girl": {"Pink": 4, "Peach": 3, "Coral": 2, "Purple": 1, "Transparent": 1.5},
    "Soft Glam": {"Brown": 2.5, "Beige": 2.5, "Peach": 2.5, "Pink": 2, "Gold": 2.5},
    "Baddie Glam": {"Brown": 3.5, "Beige": 2, "Gold": 2.5, "Red": 2, "Orange": 1},
    "Coquette Makeup": {"Pink": 4, "Purple": 2, "Beige": 1, "Peach": 1, "Transparent": 2},
    "Latte Makeup": {"Brown": 4.5, "Beige": 4.5, "Peach": 1, "Gold": 2},
    "Cloud Skin & Blurred Lips": {"Pink": 2.5, "Peach": 2.5, "Beige": 2.5, "Brown": 1},
    "Monochromatic Makeup": {},  # handled by repeating one colour family
    "Icy Glam": {"Silver": 4.5, "Blue": 3.5, "Purple": 3, "Pink": 2.5, "Transparent": 2},
    "Bold Lip": {
        "Lip": {"Red": 6},
        "Blush": {"Beige": 4, "Peach": 3.5, "Pink": 1},
        "Eyeshadow": {"Beige": 4, "Brown": 3, "Peach": 3},
    },
}
# Bold Lip: the lip is the star (red), everything else stays nude. Required groups are used
# whenever you own a matching product.
LOOK_REQUIRED = {"Bold Lip": {"Lip": {"Red"}, "Blush": {"Beige", "Peach"}, "Eyeshadow": {"Beige", "Brown", "Peach"}}}
LOOK_REQUIRED_EVERY = {"Bold Lip": {"Blush", "Eyeshadow"}}  # applies to every pick, not just the first
LOOK_REQUIRED_NOTES = {"Bold Lip": {"Lip"}}  # explain only when the red lip is missing

LOOK_PALETTE_LINES = {
    "Clean Girl": ["{colour} is gentle enough for a fresh Clean Girl palette.", "A soft shade like {colour} keeps Clean Girl effortless."],
    "Soft Girl": ["{colour} gives Soft Girl that sweet, pastel flush.", "Soft and rosy: {colour} is right on-brand for Soft Girl."],
    "Soft Glam": ["{colour} adds the warm, flattering depth Soft Glam loves.", "A {colour} shade slots right into a Soft Glam palette."],
    "Baddie Glam": ["{colour} brings the warm, sculpted depth of Baddie Glam.", "{colour} is a confident pick for a Baddie Glam face."],
    "Coquette Makeup": ["{colour} fits Coquette's soft, romantic palette.", "Dainty and pretty: {colour} suits Coquette."],
    "Latte Makeup": ["{colour} sits right inside the Latte palette of browns, beiges and nudes.", "{colour} keeps this look cosy and coffee-toned."],
    "Cloud Skin & Blurred Lips": ["{colour} blurs softly into a Cloud Skin palette.", "A soft {colour} is ideal for diffused, cloud-like colour."],
    "Monochromatic Makeup": ["{colour} is part of the {group} family you can repeat on cheeks, eyes and lips.", "Repeat {group} across the face and {colour} ties it together."],
    "Icy Glam": ["{colour} brings Icy Glam's cool, frosty palette.", "Cool and icy: {colour} is exactly the Icy Glam mood."],
    "Bold Lip": ["{colour} is the statement red that Bold Lip is built around.", "Red is the star of Bold Lip, and {colour} delivers."],
}
BOLD_SUPPORT_LINES = ["{colour} stays soft so the lip can be the star.", "A quiet {colour} keeps the focus on your red lip."]

LOOK_CATEGORY_NOTES = {
    "Clean Girl": {"Blush": "Blend with your fingertips for a skin-like flush."},
    "Soft Girl": {"Blush": "Place blush high on the cheeks for a sweet, flushed effect."},
    "Soft Glam": {"Eyeshadow": "Blend a soft halo of colour and keep the edges diffused."},
    "Baddie Glam": {"Eyeshadow": "Define the outer corner for a sculpted effect."},
    "Coquette Makeup": {"Lip": "Keep the lip colour soft and dainty."},
    "Latte Makeup": {
        "Eyeshadow": "Stay in browns, beiges and nudes, and blend the edges softly.",
        "Lip": "A brown or nude lip completes the latte palette.",
    },
    "Cloud Skin & Blurred Lips": {"Lip": "Dab the colour on, then blur the edges with a fingertip."},
    "Monochromatic Makeup": {},
    "Icy Glam": {
        "Eyeshadow": "Icy tip: be generous with glitter and shimmer on the lids.",
        "Blush": "Layer highlighter over your blush for that frosty glow.",
    },
    "Bold Lip": {
        "Lip": "Bold Lip rule: the red lip is the star, so keep everything else softer.",
        "Eyeshadow": "Keep the eyes soft so the lip stays the star.",
    },
}

# Finishing-touch tips: ONE set is shown, depending on the palette's tone
TIPS = {
    "warm": {
        "intro": "Your palette leans warm: think golden hour.",
        "bronzer": "A warm golden-bronze or caramel-bronze shade.",
        "highlighter": "Champagne-gold or peachy-gold glow.",
        "brows": "Warm brown to echo the warm tones.",
        "lenses": "Honey brown, warm hazel or olive-brown.",
    },
    "cool": {
        "intro": "Your palette leans cool: think frosty-pink moonlight.",
        "bronzer": "A soft neutral or taupe-toned bronzer, applied lightly.",
        "highlighter": "Pearl, icy-pink or silvery-champagne glow.",
        "brows": "Ash brown or soft taupe to suit the cool tones.",
        "lenses": "Grey, blue-grey, cool hazel or muted taupe.",
    },
}

LIGHTNESS = {
    "Transparent": 0, "Beige": 1, "Silver": 1.5, "Gold": 2, "Peach": 2, "Pink": 2.5,
    "Coral": 3, "Orange": 3.2, "Purple": 3.5, "Blue": 3.5, "Green": 3.5, "Red": 4.5, "Brown": 5,
}
LIGHT_WORDS = {"light", "pale", "baby", "soft", "sheer", "pastel", "milky"}
DARK_WORDS = {"dark", "deep", "burgundy", "wine", "chocolate", "espresso", "plum"}

# Layering order inside one category: matte first, then natural, then shiny / sparkly
# finishes last. Products with the same finish go from light to deep.
FINISH_ORDER = {"Matte": 0, "Natural": 1, "Glowy": 2, "Glossy": 3, "Shimmer": 4, "Glitter": 5}
SHINY_FINISHES = {"Glowy", "Glossy", "Shimmer", "Glitter"}
SPARKLE_FINISHES = {"Shimmer", "Glitter"}
MAX_SHINY_LIPS = 2  # never more than two shiny lip products at once

# Heavy, time-consuming looks: only for 20 / 30 minutes and these occasions
HEAVY_LOOKS = {"Baddie Glam", "Icy Glam"}
HEAVY_OCCASIONS = {"Date / Social Plans", "Party / Night Out", "Special Event / Photoshoot"}
# A look line like "one colour story across the face" makes no sense on a foundation
NO_FOUNDATION_LOOK_LINE = {"Monochromatic Makeup", "Bold Lip"}


# ------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------
def load_json(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (OSError, json.JSONDecodeError):
        st.warning(f"Could not read {path.name}. The app will use a temporary empty view; your file has not been deleted.")
        return default


def load_products():
    data = load_json(DATA_FILE, [])
    return data if isinstance(data, list) else []


def save_products(products):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


def save_image(uploaded_file):
    if uploaded_file is None:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    (UPLOAD_DIR / filename).write_bytes(uploaded_file.getvalue())
    return str(Path("uploads") / filename)


def product_image_path(product):
    rel = product.get("image", "")
    if not rel:
        return None
    path = (APP_DIR / rel).resolve()
    try:
        path.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def delete_product_image(product, all_products):
    """Delete the saved photo, unless another product still uses the same file."""
    rel = product.get("image", "")
    if not rel or any(p.get("image") == rel and p.get("id") != product.get("id") for p in all_products):
        return
    path = product_image_path(product)
    if path:
        try:
            path.unlink()
        except OSError:
            pass


def colour_group(original):
    """Classify from the last recognised base-colour word; preserve original separately."""
    raw = str(original or "").strip()
    if not raw:
        return "Unclassified"
    low = raw.casefold()
    if "transparent" in low or "clear" == low:
        return "Transparent"
    # Search all base words and use the last occurrence in the user's original label.
    aliases = {
        "pink": "Pink", "rose": "Pink", "blush": "Pink",
        "peach": "Peach", "coral": "Coral", "orange": "Orange",
        "red": "Red", "burgundy": "Red", "berry": "Purple",
        "purple": "Purple", "lavender": "Purple", "lilac": "Purple", "mauve": "Purple",
        "brown": "Brown", "chocolate": "Brown", "tan": "Brown",
        "beige": "Beige", "nude": "Beige", "ivory": "Beige",
        "blue": "Blue", "silver": "Silver", "grey": "Silver", "gray": "Silver",
        "green": "Green", "gold": "Gold", "yellow": "Gold", "bronze": "Brown",
        "white": "White", "black": "Black",
    }
    hits = []
    for word, group in aliases.items():
        for match in re.finditer(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", low):
            hits.append((match.start(), group))
    if hits:
        return max(hits, key=lambda item: item[0])[1]
    return raw  # uncertain: use the user's original name rather than guessing


def tone_of_group(group):
    if group in WARM_GROUPS:
        return "warm"
    if group in COOL_GROUPS:
        return "cool"
    return None


# An eyeshadow palette can hold several colours, saved as "Pink, Brown, Beige".
def split_colours(colour):
    return [c.strip() for c in str(colour or "").split(",") if c.strip()]


def product_groups(product):
    """Colour groups of a product (empty for Foundation). Palettes can have several."""
    if product.get("category") == "Foundation":
        return []
    groups = []
    for c in split_colours(product.get("colour", "")):
        g = colour_group(c)
        if g != "Unclassified" and g not in groups:
            groups.append(g)
    return groups


def group_label(product):
    return " / ".join(product_groups(product)) or "—"


def product_tone(product):
    warm = cool = 0
    first = None
    for g in product_groups(product):
        t = tone_of_group(g)
        warm += t == "warm"
        cool += t == "cool"
        first = first or t
    if warm > cool:
        return "warm"
    if cool > warm:
        return "cool"
    return first


def shade_lightness(name):
    v = LIGHTNESS.get(colour_group(name), 3.0)
    words = set(re.findall(r"[a-z]+", name.lower()))
    if words & LIGHT_WORDS:
        v -= 1.2
    if words & DARK_WORDS:
        v += 1.2
    return v


def shade_names(product):
    """The colours of a product (one, or the shades of a palette) from light to deep."""
    return sorted(split_colours(product.get("colour", "")), key=shade_lightness)


def lightness(product):
    """Rough light-to-deep rank."""
    names = split_colours(product.get("colour", ""))
    if not names:
        return 3.0
    return sum(shade_lightness(n) for n in names) / len(names)


def layer_key(product):
    """Application order inside a category: finish first (matte -> shiny), then light -> deep."""
    return (FINISH_ORDER.get(product.get("finish"), 1), lightness(product))


def normalise_legacy_product(product):
    """Read older saved records without discarding their original colour values."""
    p = dict(product)
    if not p.get("id"):
        # Stable id (same record -> same id every time it is loaded)
        p["id"] = uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(product, sort_keys=True, default=str)).hex
    p.setdefault("name", "Unnamed product")
    p.setdefault("category", "Lip")
    p.setdefault("colour", "")
    p.setdefault("finish", "Natural")
    p.setdefault("image", "")
    # Keep colour exactly as entered; classification is derived only when matching.
    return p


# History: remembers recent products AND looks so results don't repeat too much.
# Old files (a list of id-lists) are still readable.
def save_recommendation_history(ids, look=""):
    history = load_json(HISTORY_FILE, [])
    if not isinstance(history, list):
        history = []
    history.append({"products": ids, "look": look})
    history = history[-12:]
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _history_entries():
    history = load_json(HISTORY_FILE, [])
    return history if isinstance(history, list) else []


def recent_product_ids():
    ids = set()
    for entry in _history_entries()[-3:]:
        items = entry if isinstance(entry, list) else entry.get("products", []) if isinstance(entry, dict) else []
        ids.update(i for i in items if isinstance(i, str))
    return ids


def recent_looks():
    return [e.get("look") for e in _history_entries()[-2:] if isinstance(e, dict) and e.get("look")]


# ------------------------------------------------------------
# Look selection (the app chooses the look — the user does not)
# ------------------------------------------------------------
def vibe_look_map(vibe):
    mapping = {
        "Fresh & Natural": ["Clean Girl", "Cloud Skin & Blurred Lips", "Latte Makeup"],
        "Soft & Romantic": ["Soft Girl", "Coquette Makeup", "Monochromatic Makeup"],
        "Elegant & Polished": ["Soft Glam", "Latte Makeup", "Monochromatic Makeup", "Clean Girl"],
        "Glowy & Radiant": ["Soft Girl", "Soft Glam", "Icy Glam", "Clean Girl"],
        "Bold & Glamorous": ["Baddie Glam", "Bold Lip", "Icy Glam"],
        "Fun & Experimental": ["Monochromatic Makeup", "Icy Glam", "Baddie Glam", "Coquette Makeup"],
    }
    return mapping.get(vibe, LOOKS)


def look_fit(products, look):
    """0..1: how well the user's own products suit a look (finishes + colour tone)."""
    _, direction, preferred = LOOK_DETAILS[look]
    owned = [p for p in products if p.get("category") != "Foundation"]
    if not owned:
        return 0.0
    points = 0.0
    for p in owned:
        if p.get("finish") in preferred:
            points += 1
        tone = product_tone(p)
        if direction == "neutral" or tone == direction:
            points += 1
        elif tone is None:
            points += 0.5
    return points / (2 * len(owned))


def allowed_looks(pool, occasion, minutes):
    heavy_ok = minutes != "10 minutes" and occasion in HEAVY_OCCASIONS
    ok = [name for name in pool if name not in HEAVY_LOOKS or heavy_ok]
    return ok or ["Soft Glam"]


def choose_look(products, vibe, occasion, minutes="20 minutes"):
    surprise = vibe == "Surprise Me"
    pool = allowed_looks(list(LOOKS) if surprise else vibe_look_map(vibe), occasion, minutes)
    recent = recent_looks()
    target = OCCASION_INTENSITY.get(occasion, 2)
    has_red_lip = any(p.get("category") == "Lip" and "Red" in product_groups(p) for p in products)
    weights = []
    for name in pool:
        w = 0.5 + look_fit(products, name)
        if not surprise:
            w *= 1 / (1 + abs(LOOK_INTENSITY[name] - target))
        if name in recent:
            w *= 0.35  # avoid showing the same look again and again
        if name == "Bold Lip" and not has_red_lip:
            w *= 0.3  # Bold Lip works best with a red lip
        weights.append(w)
    return random.choices(pool, weights=weights, k=1)[0]


# ------------------------------------------------------------
# Scoring and recommending
# ------------------------------------------------------------
def finish_score(product, look, weather, category, occasion):
    finish = str(product.get("finish", "Natural"))
    score = 0.0
    info = {"look_match": False, "weather": None, "occasion": None}
    preferred = LOOK_DETAILS[look][2]
    if finish in preferred:
        score += 3
        info["look_match"] = True
    else:
        score += 0.5
    # Visible glitter is saved for bold looks / party occasions
    if finish == "Glitter" and "Glitter" not in preferred and occasion not in PARTY_OCCASIONS:
        score -= 1.5

    # Weather mainly guides Foundation. Blush is intentionally weather-neutral.
    if category == "Foundation":
        top = {"Hot & Humid": "Matte", "Cold & Dry": "Glowy", "Mild": "Natural"}.get(weather)
        if weather == "Rainy":
            if finish in {"Matte", "Natural"}:
                score += 2
                info["weather"] = "top" if finish == "Matte" else "alt"
        elif finish == top:
            score += 5
            info["weather"] = "top"
        elif finish == "Natural" and weather in {"Hot & Humid", "Cold & Dry"}:
            score += 2
            info["weather"] = "alt"
        elif weather == "Mild" and finish in {"Glowy", "Matte"}:
            score += 2
            info["weather"] = "alt"

    if occasion in {"University / Everyday", "Casual / Brunch", "Work / Interview"} and finish in {"Natural", "Matte", "Glossy"}:
        score += 1
        info["occasion"] = "easy"
    elif occasion in PARTY_OCCASIONS and finish in {"Shimmer", "Glitter", "Glossy"}:
        score += 1.5
        info["occasion"] = "party"
    return score, info


def palette_bonus(product, look, category):
    """Bonus when the product's colour group belongs to the look's colour story."""
    if category == "Foundation":
        return 0.0, False
    table = LOOK_PALETTE.get(look, {})
    if table and isinstance(next(iter(table.values())), dict):
        table = table.get(category, {})
    values = [table[g] for g in product_groups(product) if g in table]
    if not values:
        return 0.0, False
    return max(values) + min(0.5 * (len(values) - 1), 1.0), max(values) >= 2


def mono_groups_of(products):
    """Colour groups that can be repeated across at least two of Blush / Eyeshadow / Lip."""
    seen = {}
    for p in products:
        for g in product_groups(p):
            seen.setdefault(g, set()).add(p.get("category"))
    return {g for g, cats in seen.items() if len(cats) >= 2 and g != "Transparent"}


def colour_cohesion(product, chosen, look):
    """Bonus for colours that coordinate with what is already chosen."""
    if product.get("category") == "Foundation":
        return 0.0
    groups = set(product_groups(product))
    if not groups:
        return 0.0
    best = 0.0
    for other in chosen:
        if other.get("category") == "Foundation":
            continue
        bonus = 0.0
        if groups & set(product_groups(other)):
            bonus = 3.0 if look == "Monochromatic Makeup" else 1.5
        elif product_tone(product) and product_tone(product) == product_tone(other):
            bonus = 0.8
        best = max(best, bonus)
    direction = LOOK_DETAILS[look][1]
    if direction == "neutral":
        best += 0.5
    elif product_tone(product) == direction:
        best += 1.2
    return best


def finish_cohesion(product, chosen):
    """Keep sparkle to one place: avoid several glitter products in one look."""
    if product.get("finish") == "Glitter" and any(o.get("finish") == "Glitter" for o in chosen):
        return -2.0
    return 0.0


def recommend(products, look, weather, occasion, minutes):
    products = [normalise_legacy_product(p) for p in products]
    recent = recent_product_ids()
    ranges = TIME_RANGES[minutes]
    mono = mono_groups_of(products) if look == "Monochromatic Makeup" else set()
    selected, infos, missing, notes = [], {}, [], {}
    # Fixed order: Foundation -> Blush -> Eyeshadow -> Lip. Missing categories are skipped.
    for category in CATEGORIES:
        available = [p for p in products if p.get("category") == category]
        if not available:
            missing.append(category)
            continue
        lo, hi = ranges[category]
        count = min(random.randint(lo, hi), len(available))  # a palette is ONE product
        required = LOOK_REQUIRED.get(look, {}).get(category)
        required_every = category in LOOK_REQUIRED_EVERY.get(look, set())
        for i in range(count):
            chosen_ids = {p["id"] for p in selected}
            candidates = [p for p in available if p["id"] not in chosen_ids]  # no duplicates
            if category == "Lip":  # at most two shiny lip products
                shiny = sum(1 for p in selected if p["category"] == "Lip" and p.get("finish") in SHINY_FINISHES)
                if shiny >= MAX_SHINY_LIPS:
                    candidates = [p for p in candidates if p.get("finish") not in SHINY_FINISHES]
            if not candidates:
                break
            if required and (i == 0 or required_every):
                must = [p for p in candidates if set(product_groups(p)) & required]
                if must:
                    candidates = must
                elif i == 0 and category in LOOK_REQUIRED_NOTES.get(look, set()):
                    notes[category] = (
                        f"{look} works best with a {'/'.join(sorted(required)).lower()} {category.lower()}, "
                        f"but there is none in your collection, so BeautyMix picked the next best option."
                    )
            scored = []
            for p in candidates:
                score, info = finish_score(p, look, weather, category, occasion)
                pal, matched = palette_bonus(p, look, category)
                info["palette"] = matched
                score += pal
                if mono and set(product_groups(p)) & mono:
                    score += 2.0
                    info["palette"] = True
                    info["mono_group"] = sorted(set(product_groups(p)) & mono)[0]
                score += colour_cohesion(p, selected, look) + finish_cohesion(p, selected)
                # Best score first. Among equal scores: products not shown recently first,
                # then a random pick.
                scored.append((round(score, 2), p["id"] in recent, random.random(), p, info))
            scored.sort(key=lambda t: (-t[0], t[1], t[2]))
            best = scored[0]
            selected.append(best[3])
            infos[best[3]["id"]] = best[4]
    # Inside each category: matte first, shiny finishes last; same finish = light to deep
    selected.sort(key=lambda p: (CATEGORY_ORDER.get(p.get("category"), 99), layer_key(p)))
    return selected, infos, missing, notes


def pick_line(pool, used, fmt):
    fresh = [t for t in pool if t not in used] or pool
    template = random.choice(fresh)
    used.add(template)
    return template.format(**fmt)


def interaction_line(p, selected, partner_use, used, fmt):
    """Connect this product to a DIFFERENT product each time (spread across the whole look)."""
    group_set, tone, finish = set(product_groups(p)), product_tone(p), p.get("finish")
    options = []
    for o in selected:
        if o["id"] == p["id"]:
            continue
        kind, shared = None, ""
        if o.get("category") == "Foundation":
            if o.get("finish") == finish:
                kind = "foundation"
        else:
            both = group_set & set(product_groups(o))
            if both:
                kind, shared = "same", sorted(both)[0]
            elif tone and tone == product_tone(o):
                kind = "tone"
            elif finish != o.get("finish") and "Matte" in {finish, o.get("finish")}:
                kind = "contrast"
            elif finish == o.get("finish"):
                kind = "harmony"
        if kind:
            options.append((o, kind, shared))
    if not options:
        return None
    options.sort(key=lambda t: (partner_use[t[0]["id"]], random.random()))
    other, kind, shared = options[0]
    partner_use[other["id"]] += 1
    fmt = dict(fmt, other=other.get("name", "other product"), ofinish=other.get("finish", "").lower(),
               finish=finish, group=shared, tone=tone or "")
    return pick_line(PAIR_LINES[kind], used, fmt)


def build_reasons(selected, infos, look, weather, occasion):
    """Fun, varied reasons mixing finish, colour, look palette, weather, occasion and other products."""
    used = set()
    partner_use = collections.Counter()
    reasons = {}
    for p in selected:
        info = infos.get(p["id"], {})
        cat = p.get("category", "")
        finish = p.get("finish", "Natural")
        colour = str(p.get("colour", "")).strip()
        groups = product_groups(p)
        fmt = {
            "part": PART.get(cat, "look"), "colour": colour or "this shade", "look": look,
            "group": info.get("mono_group") or (groups[0] if groups else ""), "occasion": occasion.lower(),
            "n": len(split_colours(colour)),
        }
        lines = [pick_line(FINISH_LINES.get(finish, FINISH_LINES["Natural"]), used, fmt)]
        if cat == "Foundation":
            if info.get("weather"):
                lines.append(pick_line(WEATHER_LINES[weather][info["weather"]], used, fmt))
            if info.get("look_match") and look not in NO_FOUNDATION_LOOK_LINE:
                lines.append(pick_line(LOOK_LINES[look], used, fmt))
            elif info.get("occasion"):
                lines.append(pick_line(OCCASION_LINES[info["occasion"]], used, fmt))
        else:
            if info.get("palette"):
                if look == "Bold Lip" and cat != "Lip":
                    pool = BOLD_SUPPORT_LINES
                else:
                    pool = LOOK_PALETTE_LINES[look]
                lines.append(pick_line(pool, used, fmt))
            elif len(split_colours(colour)) > 1:
                lines.append(pick_line(PALETTE_MULTI_LINES, used, fmt))
            elif colour:
                lines.append(pick_line(COLOUR_LINES.get(groups[0] if groups else "", COLOUR_LINES["_custom"]), used, fmt))
            link = interaction_line(p, selected, partner_use, used, fmt)
            if link:
                lines.append(link)
            if info.get("look_match") and not info.get("palette"):
                lines.append(pick_line(LOOK_LINES[look], used, fmt))
            elif info.get("occasion") and random.random() < 0.5:
                lines.append(pick_line(OCCASION_LINES[info["occasion"]], used, fmt))
        if len(lines) < 2:
            lines.append(pick_line(GENERIC_LINES, used, fmt))
        reasons[p["id"]] = lines
    return reasons


def _names(items):
    return [i.get("name", "product") for i in items]


def join_names(names):
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def layer_note(items):
    names = _names(items)
    finishes = [i.get("finish", "Natural") for i in items]
    if len(set(finishes)) == 1:
        return f"Layer from light to deep: start with {names[0]}, then add {join_names(names[1:])}."
    steps = ", then ".join(f"{n} ({f.lower()})" for n, f in zip(names, finishes))
    text = f"Layer in this order: {steps}. Matte goes first and shiny finishes go last."
    if len(set(finishes)) < len(finishes):
        text += " Where finishes match, go from light to deep."
    return text


def palette_plan(product, look, category, minutes):
    """Which shades of a multi-colour palette to use for this look (named, not just 'use the palette')."""
    shades = shade_names(product)
    if len(shades) < 2:
        return None
    table = LOOK_PALETTE.get(look, {})
    if table and isinstance(next(iter(table.values())), dict):
        table = table.get(category, {})
    ranked = sorted(((table.get(colour_group(sh), 0), sh) for sh in shades), key=lambda t: -t[0])
    fits = [sh for score, sh in ranked if score >= 2][:2]
    name = product.get("name", "the palette")
    sparkle = product.get("finish") in SPARKLE_FINISHES

    def how(light, deep):
        if sparkle:
            return f"press {light} on the centre of the lid or the inner corner, and keep {deep} toward the outer corner"
        return f"use {light} as the base and {deep} to add depth at the outer corner"

    if len(fits) >= 2:
        light, deep = sorted(fits, key=shade_lightness)
        text = f"For {look}, reach for the {light} and {deep} shades in {name}: {how(light, deep)}."
    elif len(fits) == 1:
        star = fits[0]
        partner = shades[-1] if star == shades[0] else shades[0]
        light, deep = sorted([star, partner], key=shade_lightness)
        text = f"For {look}, the {star} shade in {name} is the one to reach for. Pair it with {partner}: {how(light, deep)}."
    else:
        text = f"From {name}, {how(shades[0], shades[-1])}."
    if minutes == "10 minutes":
        text += " Short on time? Two shades are all you need."
    return text


def category_notes(category, items, look, minutes="20 minutes"):
    """Notes for one category frame: layering order, placement, palette shades, look tips."""
    notes = []
    names = _names(items)
    if len(items) >= 2:
        notes.append(layer_note(items))
    if category == "Eyeshadow":
        singles = [i for i in items if len(shade_names(i)) <= 1]
        palettes = [i for i in items if len(shade_names(i)) > 1]
        base = sorted([i for i in singles if i.get("finish") not in SPARKLE_FINISHES], key=lightness)
        shimmers = [i for i in singles if i.get("finish") == "Shimmer"]
        glitters = [i for i in singles if i.get("finish") == "Glitter"]
        if len(base) == 1:
            notes.append(f"Sweep {base[0].get('name')} across the lid and blend the edges.")
        elif len(base) >= 2:
            notes.append(f"Wash {base[0].get('name')} across the lid, then use {base[-1].get('name')} to add depth at the outer corner."
                         + (f" Blend {join_names(_names(base[1:-1]))} in between." if len(base) > 2 else ""))
        if shimmers:
            notes.append(f"Press {join_names(_names(shimmers))} onto the centre of the lid, the inner corner or under the eye for a soft glow.")
        if glitters:
            notes.append(f"Dab {join_names(_names(glitters))} on the centre of the lid, the inner corner or under the eye, and keep it off the crease so the sparkle stays visible.")
        for pal in palettes[:2]:
            plan = palette_plan(pal, look, category, minutes)
            if plan:
                notes.append(plan)
    elif category == "Blush" and len(items) >= 2:
        notes.append(f"Pat {names[0]} on first, then add {join_names(names[1:])} on the apples of the cheeks for gentle depth.")
    elif category == "Lip" and len(items) >= 2:
        notes.append(f"Apply {names[0]} first, then add {join_names(names[1:])} on top, focusing on the centre of the lips.")
        if items[-1].get("finish") in SHINY_FINISHES:
            notes.append(f"Finish with {names[-1]} on top for shine.")
    if len(items) >= 2:
        finishes = [i.get("finish") for i in items]
        if len(set(finishes)) > 1:
            notes.append(f"Together they mix {join_names([f.lower() for f in dict.fromkeys(finishes)])} finishes for layered texture.")
        else:
            notes.append(f"They share a {finishes[0].lower()} finish, so the layers blend into one consistent texture.")
    extra = LOOK_CATEGORY_NOTES.get(look, {}).get(category)
    if extra:
        notes.append(extra)
    return notes


MONO_EYE_FINISH = {
    "Matte": "A matte finish keeps the lids soft and blended.",
    "Natural": "A natural finish keeps the lids skin-like.",
    "Glowy": "A glowy finish gives the lids a soft sheen.",
    "Glossy": "A glossy finish gives the lids a soft sheen.",
    "Shimmer": "Shimmer adds a subtle sparkle to the lids.",
    "Glitter": "Glitter adds visible sparkle: dab it on the centre of the lid or under the eye.",
}


def mono_eye_reasons(blushes, shadows):
    """Monochromatic Makeup: the recommended blush is also used on the eyes."""
    out = {}
    for b in blushes:
        lines = [
            f"Your blush works on the eyes too: sweep {b.get('name')} over the lids so cheeks and eyes share one colour story.",
            MONO_EYE_FINISH.get(b.get("finish"), MONO_EYE_FINISH["Natural"]),
        ]
        match = next((s for s in shadows if set(product_groups(s)) & set(product_groups(b))), None)
        if match:
            lines.append(f"Same colour family as your {match.get('name')}, so the eye look feels layered, not mismatched.")
        out[b["id"]] = lines
    return out


def palette_tone(selected, look):
    """Warm or cool (never both), from the colours of the recommended products."""
    warm = cool = 0
    first_tone = {}
    for p in selected:
        if p.get("category") == "Foundation":
            continue
        tone = product_tone(p)
        warm += tone == "warm"
        cool += tone == "cool"
        if tone and p.get("category") not in first_tone:
            first_tone[p.get("category")] = tone
    if warm > cool:
        return "warm"
    if cool > warm:
        return "cool"
    # Tie or no coloured products: look's own direction, then lip > blush > eyeshadow, then warm
    direction = LOOK_DETAILS[look][1]
    if direction in TIPS:
        return direction
    for cat in ("Lip", "Blush", "Eyeshadow"):
        if cat in first_tone:
            return first_tone[cat]
    return "warm"


LOOK_FLAVOUR = {
    "Clean Girl": {
        "bronzer": "One light sweep, like a sun-kissed shortcut.",
        "highlighter": "A tiny tap on the cheekbones keeps that lit-from-within glow.",
        "brows": "Brush them up and keep them soft and fluffy.",
        "lenses": "Your eyes should look like yours, just brighter.",
        "lashes": "Curl, then one quick coat. Done!",
    },
    "Soft Girl": {
        "bronzer": "Skip heavy contour and just warm the edges of your face.",
        "highlighter": "A soft, pearly dab adds a dewy, sweet finish.",
        "brows": "Soft, slightly feathered brows keep the look gentle.",
        "lenses": "Soft shades keep the whole look dreamy.",
        "lashes": "Curled lashes keep that doll-like softness.",
    },
    "Soft Glam": {
        "bronzer": "Warm the temples and under the cheekbones for gentle definition.",
        "highlighter": "Add glow to the cheekbones and the inner corners of the eyes.",
        "brows": "Defined but soft, like a polished frame for the eyes.",
        "lenses": "A subtle colour lift pairs nicely with a blended eye.",
        "lashes": "Wispy lashes add the glam touch without feeling heavy.",
    },
    "Baddie Glam": {
        "bronzer": "Sculpt with confidence: cheekbones, jawline and temples.",
        "highlighter": "Go bold on the high points: cheekbones, nose bridge and cupid's bow.",
        "brows": "Sharp, groomed and defined to match the energy.",
        "lenses": "A deeper or bolder lens colour adds to the high-impact look.",
        "lashes": "Dramatic lashes are practically part of this look.",
    },
    "Coquette Makeup": {
        "bronzer": "Keep any bronzer super light so the look stays dainty.",
        "highlighter": "A soft, pearly-pink glow on the cheekbones is perfect.",
        "brows": "Soft, brushed-up brows keep it delicate.",
        "lenses": "Light, soft lens colours keep the romantic feel.",
        "lashes": "Curled, fluttery lashes are the ideal Coquette finish.",
    },
    "Latte Makeup": {
        "bronzer": "Warm the face lightly, like a latte.",
        "highlighter": "Choose a golden glow, like sunlight on a coffee-shop window.",
        "brows": "Brown brows tie the whole latte palette together.",
        "lenses": "Brown and honey tones complement the coffee palette.",
        "lashes": "A brown mascara would keep it soft and cosy.",
    },
    "Cloud Skin & Blurred Lips": {
        "bronzer": "Use almost nothing, or skip it for that soft-focus look.",
        "highlighter": "Tap it on with your fingertips so the glow stays diffused.",
        "brows": "Soft, natural brows blend into the cloud-like finish.",
        "lenses": "Natural tones keep everything soft-focus.",
        "lashes": "Keep it dreamy rather than defined.",
    },
    "Monochromatic Makeup": {
        "bronzer": "Choose a shade in the same colour family as your look.",
        "highlighter": "Pick a glow in the same tone as your palette so it all ties together.",
        "brows": "Match them to the overall colour story.",
        "lenses": "Pick a lens that echoes your eyeshadow.",
        "lashes": "Keep lashes simple so the colour story stays the star.",
    },
    "Icy Glam": {
        "bronzer": "Keep it subtle: this look is all about the glow.",
        "highlighter": "Make it count: layer a visible, frosty highlight right on the cheekbones.",
        "brows": "Crisp, defined brows keep the look icy and sharp.",
        "lenses": "Grey or blue-grey lenses amplify the frosty effect.",
        "lashes": "Extra-long or sparkly lashes fit the icy mood.",
    },
    "Bold Lip": {
        "bronzer": "Keep it light so your red lip stays the star.",
        "highlighter": "Keep the glow soft: the lip should do the talking.",
        "brows": "Neat, defined brows frame a bold lip.",
        "lenses": "Natural colours keep the focus on your lips.",
        "lashes": "One clean coat is enough. Let the lip lead.",
    },
}


def lash_tip(look, minutes, occasion):
    dramatic = (
        LOOK_INTENSITY[look] >= 3
        or (LOOK_INTENSITY[look] == 2 and minutes != "10 minutes")
        or occasion in PARTY_OCCASIONS
    )
    if dramatic:
        base = "Add lashes or layer on the mascara for extra definition."
        extra = ""
    else:
        base = "Curl your lashes with a lash curler, then add a light coat of mascara."
        extra = " Feeling extra? Lashes are a lovely add-on."  # simple look: lashes are a bonus
    return f"{base} {LOOK_FLAVOUR[look]['lashes']}{extra}"


def build_finishing_tips(selected, look, tone, minutes, occasion):
    """Five short tips: tied to the look, and (for two of them) to the recommended products."""
    base, flav = TIPS[tone], LOOK_FLAVOUR[look]
    light_look = LOOK_INTENSITY[look] == 1

    def lead(text):  # soft looks: bronzer, highlighter and lenses should look natural
        return f"Keep it natural: {text[0].lower()}{text[1:]}" if light_look else text

    first = lambda cat: next((p for p in selected if p.get("category") == cat), None)
    blush = first("Blush")
    shadows = [p for p in selected if p.get("category") == "Eyeshadow"]
    shadow = shadows[0] if shadows else None
    sparkle = next((p for p in shadows if p.get("finish") in SPARKLE_FINISHES), None)

    bronzer = f"{lead(base['bronzer'])} {flav['bronzer']}"
    highlighter = f"{lead(base['highlighter'])} {flav['highlighter']}"
    if sparkle and not light_look:
        highlighter += f" It echoes the sparkle of your {sparkle.get('name')}."
    elif blush:
        highlighter += f" Tap it just above your {blush.get('name')}."
    brows = f"{base['brows']} {flav['brows']}"
    lenses = f"{lead(base['lenses'])} {flav['lenses']}"
    if shadow:
        lenses += f" Lovely with the {shadow.get('colour') or 'shades'} of your {shadow.get('name')}."
    return [
        ("Bronzer", bronzer), ("Highlighter", highlighter), ("Brows", brows),
        ("Contact lenses", lenses), ("Lashes", lash_tip(look, minutes, occasion)),
    ]


def find_look_image(look):
    slug = re.sub(r"[^a-z0-9]+", "_", look.lower()).strip("_")
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = LOOK_IMG_DIR / f"{slug}{ext}"
        if candidate.is_file():
            return candidate
    return None


def is_valid_image(path):
    try:
        from PIL import Image
    except ImportError:
        return path.stat().st_size > 0
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def find_my_look_images(look, limit=6):
    """Your own photos in order: <slug>.jpg = #1, <slug>_2.png = #2, <slug>_3.webp = #3 ..."""
    slug = re.sub(r"[^a-z0-9]+", "_", look.lower()).strip("_")
    found = {}
    for path in sorted(MY_LOOK_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        stem = path.stem.lower()
        if stem == slug:
            number = 1
        else:
            m = re.fullmatch(re.escape(slug) + r"_(\d+)", stem)
            if not m:
                continue
            number = int(m.group(1))
        if number not in found and is_valid_image(path):
            found[number] = path
    return [found[n] for n in sorted(found)][:limit]


LOGO_SVG_FALLBACK = (
    "<svg width='58' height='58' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'>"
    "<circle cx='50' cy='50' r='48' fill='#f8e6ea' stroke='#e8c7d0' stroke-width='1.6'/>"
    "<rect x='35' y='57' width='30' height='26' rx='3' fill='#744552'/>"
    "<rect x='33' y='48' width='34' height='10.5' rx='2.2' fill='#c99a7c'/>"
    "<path d='M38 48.5V33l2-4.5 11-12 5.5-2 4.5 2.5 1 5v26.5z' fill='#dd6f8e'/></svg>"
)


def show_logo_and_hero():
    logo = ASSETS_DIR / "beautymix_logo.png"
    left, right = st.columns([1, 9], vertical_alignment="center")
    with left:
        if logo.is_file():
            st.image(str(logo), width=62)  # 1024px source, shown small = crisp
        else:
            st.markdown(LOGO_SVG_FALLBACK, unsafe_allow_html=True)  # vector, always sharp
    with right:
        st.markdown("<div class='bm-wordmark'>BeautyMix</div><div class='bm-tagline'>YOUR BEAUTY, YOUR WAY</div>", unsafe_allow_html=True)
    st.markdown("<div class='bm-divider'></div>", unsafe_allow_html=True)


st.set_page_config(page_title="BeautyMix | Your Beauty, Your Way", page_icon="💄", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap');
:root{--cream:#fbf7f1;--cream2:#fffdfa;--pink:#f2dfe3;--pink2:#e8c7d0;--rose:#b56f83;--deep:#744552;--brown:#4c3633;--muted:#877477;--line:#eadbdc;}
.stApp{background:var(--cream);color:var(--brown);font-family:'DM Sans',sans-serif;}
[data-testid="stHeader"]{background:rgba(251,247,241,.9);}
.block-container{max-width:1200px;padding-top:3.6rem;padding-bottom:3rem;}
h1,h2,h3{color:var(--brown)!important;letter-spacing:-.025em;}
h1,h2{font-family:'Playfair Display',Georgia,serif!important;font-weight:500!important;}
h1{font-size:clamp(2rem,4vw,3rem)!important;}h2{font-size:clamp(1.55rem,3vw,2.2rem)!important;}
p,label,[data-testid="stCaptionContainer"]{color:var(--muted);}
.bm-wordmark{font-family:'Playfair Display',Georgia,serif;font-size:2.45rem;color:var(--deep);line-height:1.1;}
.bm-tagline{font-size:.72rem;letter-spacing:.24em;font-weight:700;color:var(--rose);margin-top:.45rem;}
.bm-divider{height:1px;background:linear-gradient(90deg,transparent,var(--pink2),transparent);margin:1rem 0 1.6rem;}
.bm-panel{background:linear-gradient(125deg,var(--cream2),#f7e7ea);border:1px solid var(--line);border-radius:22px;padding:1.4rem 1.6rem;margin:.4rem 0 1.4rem;box-shadow:0 8px 25px #71454b0b;}
.bm-eyebrow{font-size:.7rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--rose);margin-bottom:.4rem;}
.bm-panel-title{font-family:'Playfair Display',Georgia,serif;font-size:1.7rem;color:var(--brown);}
[data-testid="stSidebar"]{background:#f4e7e8;border-right:1px solid var(--line);}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:.35rem .15rem;}
div[data-testid="stForm"],div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:18px!important;}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--cream2);box-shadow:0 5px 18px #71454b09;padding:.35rem;}
[data-testid="stFileUploader"] section{background:#fff9f8;border-color:#e2c2cc;border-radius:14px;}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] [data-baseweb="select"]>div,[data-testid="stTextArea"] textarea{border-radius:12px;border-color:#e3cfd2;background:#fffdfa;}
div.stButton>button,div[data-testid="stFormSubmitButton"]>button{border-radius:999px;min-height:2.65rem;padding:.35rem 1.1rem;font-weight:600;border-color:#d9b6bf;}
div.stButton>button[kind="primary"],div[data-testid="stFormSubmitButton"]>button[kind="primary"]{background:var(--rose);background:#a96579;border:1px solid #a96579;color:white;}
div.stButton>button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"]>button[kind="primary"]:hover{background:#824c5d;color:white;}
hr{border-color:var(--line);}
.bm-chip{display:inline-block;padding:.22rem .8rem;margin:.15rem .3rem .15rem 0;border-radius:999px;background:#fff;border:1px solid var(--pink2);color:var(--deep);font-size:.8rem;font-weight:600;}
.bm-badge{display:inline-block;padding:.16rem .7rem;border-radius:999px;background:var(--pink);color:var(--deep);font-size:.68rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;}
.bm-tips{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.9rem;margin:.6rem 0 1rem;}
.bm-tip{background:linear-gradient(135deg,var(--cream2),#f9ecee);border:1px solid var(--line);border-radius:18px;padding:1rem 1.1rem;color:var(--brown);font-size:.93rem;line-height:1.45;box-shadow:0 5px 16px #71454b09;}
.bm-tip-t{font-family:'Playfair Display',Georgia,serif;font-size:1.1rem;color:var(--rose);margin-bottom:.3rem;}
.bm-placeholder{min-height:190px;background:linear-gradient(135deg,#f7e5e8,#fffaf3);border:1px solid var(--line);border-radius:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:1.2rem;color:var(--deep);}
.bm-count{font-size:.8rem;color:var(--muted);margin-left:.4rem;}
div[role="dialog"]{background:var(--cream)!important;border-radius:22px!important;}
div[role="dialog"] h2{font-family:'Playfair Display',Georgia,serif!important;font-size:1.6rem!important;color:var(--brown)!important;}
.bm-photo-empty{background:#f8e9ec;border-radius:14px;height:170px;display:flex;align-items:center;justify-content:center;font-size:2rem;}
/* readable button labels: the global <p> colour used to make them grey */
[data-testid="stBaseButton-secondary"] p,[data-testid="stBaseButton-secondaryFormSubmit"] p,button[kind="secondary"] p,button[kind="secondaryFormSubmit"] p{color:var(--deep)!important;}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p,button[kind="primary"] p,button[kind="primaryFormSubmit"] p{color:#fff!important;}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{background:#a96579!important;border:1px solid #a96579!important;}
[data-testid="stBaseButton-primary"]:hover,[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:#824c5d!important;border-color:#824c5d!important;}
[class*="st-key-bm_del_"] button p{color:#a8434f!important;}
div[data-testid="stDialog"] div[role="dialog"]{border-radius:22px;background:var(--cream2);max-width:500px;}
div[data-testid="stDialog"] div[role="dialog"] [data-testid="stVerticalBlock"]{gap:.6rem;}
/* Layer & blend / Look tip box: sits inside the category frame with space below */
[class*="st-key-bm_note_"]{background:#f9ecee;border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem .5rem;margin:.9rem 0 1rem;}
[class*="st-key-bm_note_"] p,[class*="st-key-bm_note_"] li{color:var(--brown);font-size:.92rem;}
/* mood board pinned top-right (manual: arrows switch photos) */
/* finishing-touch cards: cool = pale purple/pink, warm = beige */
.bm-tips.cool .bm-tip{background:linear-gradient(135deg,#f6effb,#fbe9f2);border-color:#e4d4ee;}
.bm-tips.cool .bm-tip-t{color:#8b6aa8;}
.bm-tips.warm .bm-tip{background:linear-gradient(135deg,#fbf4e8,#f3e4cf);border-color:#e9d6b8;}
.bm-tips.warm .bm-tip-t{color:#9a7248;}
.bm-badge.soft{background:#fff;border:1px solid var(--pink2);}
/* the ⋯ button: only the dots, pinned to the top-right corner of each product card */
[class*="st-key-bm_card_"]{position:relative;}
[class*="st-key-bm_menu_"]{position:absolute;top:.05rem;right:.2rem;width:auto!important;z-index:5;}
[class*="st-key-bm_menu_"] button,[class*="st-key-bm_menu_"] button:hover,[class*="st-key-bm_menu_"] button:focus{background:transparent!important;border:none!important;box-shadow:none!important;min-height:0!important;height:auto!important;padding:0 .25rem!important;}
[class*="st-key-bm_menu_"] button p{color:var(--deep)!important;font-size:1.35rem;font-weight:700;line-height:1;margin:0;}
.bm-card-top{height:1.1rem;margin-bottom:-.4rem;}
/* mood board pinned top-right: arrows and dots sit ON the photo */
.st-key-bm_float{position:fixed;top:4.4rem;right:1.2rem;width:190px;z-index:900;background:var(--cream2);padding:8px 8px 10px;border-radius:18px;border:1px solid var(--line);box-shadow:0 10px 30px #71454b26;gap:.35rem;}
.st-key-bm_float_stage{position:relative;gap:0!important;}
.st-key-bm_float [data-testid="stElementContainer"]{margin:0!important;}
.st-key-bm_float::after{display:block;text-align:center;font-size:.56rem;letter-spacing:.1em;text-transform:uppercase;color:var(--rose);font-weight:700;line-height:1.4;padding:0 2px;}
.st-key-bm_float img{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:12px;display:block;}
.st-key-bm_float_prev,.st-key-bm_float_next{position:absolute;top:50%;transform:translateY(-50%);width:auto!important;z-index:4;}
.st-key-bm_float_prev{left:2px;}
.st-key-bm_float_next{right:2px;}
.st-key-bm_float_prev button,.st-key-bm_float_next button,.st-key-bm_float_prev button:hover,.st-key-bm_float_next button:hover,.st-key-bm_float_prev button:focus,.st-key-bm_float_next button:focus{background:transparent!important;border:none!important;box-shadow:none!important;min-height:0!important;height:auto!important;padding:0 .3rem!important;}
.st-key-bm_float_prev button p,.st-key-bm_float_next button p{color:rgba(255,255,255,.6)!important;font-size:2.2rem;font-weight:300;line-height:1;margin:0;text-shadow:0 1px 4px rgba(0,0,0,.3);}
.bm-float-dots{position:absolute;left:0;right:0;bottom:9px;display:flex;justify-content:center;gap:6px;}
.bm-dot{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.55);box-shadow:0 0 3px rgba(0,0,0,.4);}
.bm-dot.on{background:#fff;}
@media(max-width:900px){.st-key-bm_float{width:120px;top:3.6rem;right:.5rem;padding:5px;}.st-key-bm_float::after{display:none;}}
@media(max-width:700px){.block-container{padding-top:2.6rem}.bm-wordmark{font-size:2rem}}
</style>
""", unsafe_allow_html=True)

show_logo_and_hero()


# ------------------------------------------------------------
# Shared widgets: colour input, product records, edit / delete dialogs
# ------------------------------------------------------------
def colour_inputs(category, key, existing=""):
    """Colour widgets for a category. Returns the colour text ('' for Foundation).

    Foundation: no colour input at all.  Eyeshadow: one OR several colours (palettes).
    Blush / Lip: choose a colour or type a custom one.
    """
    if category == "Foundation":
        return ""
    key = f"{key}_{category}"
    options = colour_choices_for(category)
    lookup = {c.lower(): c for c in options}
    existing_list = split_colours(existing)
    if category == "Eyeshadow":
        defaults = [lookup[c.lower()] for c in existing_list if c.lower() in lookup]
        extra = ", ".join(c for c in existing_list if c.lower() not in lookup)
        picked = st.multiselect("Colour(s)", options, default=defaults, key=f"{key}_multi",
                                help="Pick one colour or several (great for palettes).")
        custom = st.text_input("Custom colour name(s)", value=extra, key=f"{key}_custom",
                               placeholder="e.g. Peach Beige, Mauve Brown (separate with commas)")
        names = list(picked) + split_colours(custom)
        unique = {}
        for c in names:
            unique.setdefault(" ".join(c.split()).lower(), " ".join(c.split()))
        return ", ".join(unique.values())
    is_custom = bool(existing_list) and (len(existing_list) > 1 or existing_list[0].lower() not in lookup)
    mode = st.radio("Colour", ["Choose a colour", "Enter a custom colour"], index=1 if is_custom else 0,
                    horizontal=True, key=f"{key}_mode")
    if mode == "Choose a colour":
        index = options.index(lookup[existing_list[0].lower()]) if existing_list and existing_list[0].lower() in lookup else 0
        return st.selectbox("Colour family / name", options, index=index, key=f"{key}_select")
    return " ".join(st.text_input("Custom colour name", value=existing if is_custom else "", key=f"{key}_text",
                                  placeholder="e.g. Peach Beige, Pink Brown, Blue Silver").split())


def make_record(name, category, colour, finish, image, product_id=None):
    """Build the saved record. The colour text is kept exactly as entered; Foundation has none."""
    names = [] if category == "Foundation" else [" ".join(c.split()) for c in split_colours(colour)]
    groups = []
    for n in names:
        g = colour_group(n)
        if g not in groups:
            groups.append(g)
    return {
        "id": product_id or uuid.uuid4().hex, "name": name.strip(), "category": category,
        "colour": ", ".join(names), "colour_group": " / ".join(groups),
        "finish": finish, "image": image,
    }


def _step_banner(delta, n):
    st.session_state["bm_banner_idx"] = (st.session_state.get("bm_banner_idx", 0) + delta) % n


def mood_board(images, look):
    """Your own photos of the look, pinned top-right. Click the arrows on the photo to switch."""
    n = len(images)
    idx = st.session_state.get("bm_banner_idx", 0) % n
    caption = f"{look} · mood board".replace("\\", "").replace('"', "")
    st.markdown(
        "<style>@media(min-width:1100px) and (max-width:1500px){.block-container{padding-right:250px!important}}"
        f'.st-key-bm_float::after{{content:"{caption}";}}</style>',
        unsafe_allow_html=True,
    )
    with st.container(key="bm_float"):
        with st.container(key="bm_float_stage"):
            st.image(str(images[idx]), width="stretch")
            if n > 1:
                st.button("‹", key="bm_float_prev", on_click=_step_banner, args=(-1, n))
                st.button("›", key="bm_float_next", on_click=_step_banner, args=(1, n))
                dots = "".join(f"<span class='bm-dot{' on' if i == idx else ''}'></span>" for i in range(n))
                st.markdown(f"<div class='bm-float-dots'>{dots}</div>", unsafe_allow_html=True)


def render_product_row(p, reasons):
    pic, details = st.columns([1, 4])
    with pic:
        path = product_image_path(p)
        if path:
            st.image(str(path), width="stretch")
        else:
            st.markdown("<div style='background:#f8e9ec;border-radius:14px;padding:2rem;text-align:center;font-size:2rem'>💄</div>", unsafe_allow_html=True)
    with details:
        st.markdown(f"### {p.get('name', 'Unnamed product')}")
        colour = p.get("colour", "")
        if p.get("category") != "Foundation" and colour:
            st.write(f"**Colour:** {colour} · **Colour group:** {group_label(p)}")
        st.write(f"**Finish:** {p.get('finish', 'Natural')}")
        for reason in reasons:
            st.markdown(f"- {reason}")


@st.dialog("Edit product", width="small")
def edit_dialog(product_id):
    """One window for everything: edit the product, or delete it (with a confirmation)."""
    current = [normalise_legacy_product(p) for p in load_products()]
    p = next((q for q in current if q["id"] == product_id), None)
    if p is None:
        st.warning("This product no longer exists.")
        return
    key = f"bm_edit_{product_id}"
    confirm_key = f"{key}_confirm"

    pic_col, form_col = st.columns([1, 3])
    with pic_col:
        path = product_image_path(p)
        if path:
            st.image(str(path), width="stretch")
        else:
            st.markdown("<div style='background:#f8e9ec;border-radius:14px;padding:1.6rem;text-align:center;font-size:2rem'>💄</div>", unsafe_allow_html=True)
    with form_col:
        name = st.text_input("Product name", value=p["name"], key=f"{key}_name")
        cat_col, fin_col = st.columns(2)
        with cat_col:
            category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(p["category"]) if p["category"] in CATEGORIES else 0, key=f"{key}_cat")
        with fin_col:
            finish = st.selectbox("Finish", FINISHES, index=FINISHES.index(p["finish"]) if p["finish"] in FINISHES else 0, key=f"{key}_finish")
    colour = colour_inputs(category, key, p.get("colour", "") if category == p["category"] else "")
    with st.expander("Replace photo"):
        new_photo = st.file_uploader("New photo", type=["png", "jpg", "jpeg", "webp"], key=f"{key}_photo", label_visibility="collapsed")

    if st.session_state.get(confirm_key):
        st.warning(f"Delete {p['name']}? This also removes its saved photo.")
        yes_col, keep_col = st.columns(2)
        with yes_col:
            yes = st.button("Yes, delete", type="primary", key=f"{key}_yes")
        with keep_col:
            st.button("Keep it", key=f"{key}_keep", on_click=lambda: st.session_state.update({confirm_key: False}))
        if yes:
            delete_product_image(p, current)
            save_products([q for q in current if q["id"] != product_id])
            st.session_state[confirm_key] = False
            st.session_state["bm_notice"] = f"{p['name']} was deleted."
            st.rerun()
        return

    save_col, cancel_col, delete_col = st.columns(3)
    with save_col:
        save_clicked = st.button("Save changes", type="primary", key=f"{key}_save")
    with cancel_col:
        cancel_clicked = st.button("Cancel", key=f"{key}_cancel")
    with delete_col:
        st.button("Delete", key=f"bm_del_{product_id}", on_click=lambda: st.session_state.update({confirm_key: True}))
    if cancel_clicked:
        st.rerun()
    if save_clicked:
        if not name.strip():
            st.error("Please enter a product name.")
        elif category != "Foundation" and not colour.strip():
            st.error("Please select or enter a colour.")
        else:
            image = save_image(new_photo) if new_photo is not None else p.get("image", "")
            record = make_record(name, category, colour, finish, image, product_id)
            if new_photo is not None:
                delete_product_image(p, current)
            save_products([record if q["id"] == product_id else q for q in current])
            st.session_state["bm_notice"] = f"{record['name']} was updated."
            st.rerun()


with st.sidebar:
    st.markdown("### Your beauty edit")
    page = st.radio("Navigate", ["My Collection", "Add a Product", "Create a Look"], label_visibility="collapsed")

products = [normalise_legacy_product(p) for p in load_products()]

if st.session_state.get("bm_notice"):
    st.success(st.session_state.pop("bm_notice"))

if page == "Add a Product":
    st.markdown("<div class='bm-panel'><div class='bm-eyebrow'>YOUR COLLECTION</div><div class='bm-panel-title'>Add a little beauty</div><p>Save your own products here and use them in future recommendations.</p></div>", unsafe_allow_html=True)

    # NOT an st.form: the colour field must appear/disappear as soon as the category
    # changes. The counter in the widget keys clears the fields after saving.
    n = st.session_state.setdefault("bm_form_n", 0)
    with st.container(border=True):
        name = st.text_input("Product name", placeholder="e.g. Rose Lip Gloss", key=f"bm_name_{n}")
        category = st.selectbox("Category", CATEGORIES, key=f"bm_cat_{n}")
        colour = colour_inputs(category, f"bm_add_{n}")  # Foundation: nothing is shown
        finish = st.selectbox("Finish", FINISHES, help="Shimmer is a subtle reflective sheen; glitter is more visible sparkle.", key=f"bm_finish_{n}")
        uploaded_file = st.file_uploader("Upload the actual product photo", type=["png", "jpg", "jpeg", "webp"], help="The photo is saved in this project's uploads folder.", key=f"bm_photo_{n}")
        submitted = st.button("Add to my collection", type="primary", key=f"bm_add_btn_{n}")
    if submitted:
        if not name.strip():
            st.error("Please enter a product name.")
        elif category != "Foundation" and not str(colour).strip():
            st.error("Please select or enter a colour.")
        else:
            new_product = make_record(name, category, colour, finish, save_image(uploaded_file))
            products.append(new_product)
            save_products(products)
            st.session_state["bm_notice"] = f"{new_product['name']} was saved. You can add more products whenever you like."
            st.session_state["bm_form_n"] = n + 1
            st.rerun()

elif page == "My Collection":
    st.markdown("<div class='bm-panel'><div class='bm-eyebrow'>YOUR BEAUTY, YOUR WAY</div><div class='bm-panel-title'>My collection</div><p>Your saved products stay in your project folder between app sessions.</p></div>", unsafe_allow_html=True)

    # A dialog requested from a product's ⋯ menu opens here
    action = st.session_state.pop("bm_action", None)
    if action:
        edit_dialog(action[1])

    st.write(f"You have **{len(products)}** saved product(s).")
    if not products:
        st.info("Your collection is empty. Choose ‘Add a Product’ to register your first item.")
    else:
        filter_category = st.selectbox("Filter by category", ["All"] + CATEGORIES)
        visible = [p for p in products if filter_category == "All" or p.get("category") == filter_category]
        cols = st.columns(4)
        for i, p in enumerate(visible):
            with cols[i % 4]:
                with st.container(border=True, key=f"bm_card_{p['id']}"):
                    st.markdown("<div class='bm-card-top'></div>", unsafe_allow_html=True)
                    image_path = product_image_path(p)
                    if image_path:
                        st.image(str(image_path), width="stretch")
                    else:
                        st.markdown("<div style='background:#f8e9ec;border-radius:14px;padding:2.2rem;text-align:center;font-size:2rem'>💄</div>", unsafe_allow_html=True)
                    st.markdown(f"**{p.get('name', 'Unnamed product')}**")
                    if st.button("⋮", key=f"bm_menu_{p['id']}", help="Edit or delete this product"):
                        st.session_state["bm_action"] = ("edit", p["id"])
                        st.rerun()
                    st.caption(p.get("category", ""))
                    if p.get("category") != "Foundation" and p.get("colour"):
                        st.write(f"Colour: {p.get('colour')} · Group: {group_label(p)}")
                    st.write(f"Finish: {p.get('finish', 'Natural')}")

else:  # Create a Look
    st.markdown("<div class='bm-panel'><div class='bm-eyebrow'>A LOOK MADE FROM WHAT YOU OWN</div><div class='bm-panel-title'>Create your look</div><p>Choose your vibe and plans. BeautyMix picks the look and matches products from your saved collection.</p></div>", unsafe_allow_html=True)
    with st.form("look_form"):
        c1, c2 = st.columns(2)
        with c1:
            vibe = st.selectbox("What makeup vibe are you feeling?", VIBES, help="Text-only choices keep the input simple.")
            occasion = st.selectbox("Occasion", OCCASIONS)
        with c2:
            weather = st.selectbox("Weather", WEATHERS)
            minutes = st.selectbox("Time available", TIMES)
            st.caption("BeautyMix chooses the look for you. Surprise Me picks from all ten looks.")
        submitted = st.form_submit_button("Create my BeautyMix look", type="primary")
    if submitted:
        if not products:
            st.warning("Your collection is empty. Add your own products first, then create a look.")
        else:
            chosen_look = choose_look(products, vibe, occasion, minutes)
            selected, infos, missing, warnings = recommend(products, chosen_look, weather, occasion, minutes)
            ids = [p["id"] for p in selected]
            tone = palette_tone(selected, chosen_look)
            cat_notes = {c: category_notes(c, [p for p in selected if p["category"] == c], chosen_look, minutes)
                         for c in CATEGORIES if any(p["category"] == c for p in selected)}
            # Monochromatic Makeup: the recommended blush is ALSO shown in the eyeshadow section
            mono_eye, mono_reasons = [], {}
            if chosen_look == "Monochromatic Makeup":
                blushes = [p for p in selected if p["category"] == "Blush"]
                if blushes:
                    mono_eye = [b["id"] for b in blushes]
                    mono_reasons = mono_eye_reasons(blushes, [p for p in selected if p["category"] == "Eyeshadow"])
                    cat_notes.setdefault("Eyeshadow", []).append(
                        f"Monochromatic bonus: sweep {join_names(_names(blushes))} over your lids too, so cheeks and eyes match.")
            # The whole result is stored once, so it stays stable while you scroll or click.
            st.session_state["bm_last_result"] = {
                "look": chosen_look, "vibe": vibe, "occasion": occasion,
                "weather": weather, "minutes": minutes, "ids": ids, "missing": missing,
                "warnings": warnings, "cat_notes": cat_notes, "tone": tone,
                "reasons": build_reasons(selected, infos, chosen_look, weather, occasion),
                "mono_eye": mono_eye, "mono_eye_reasons": mono_reasons,
                "tips": build_finishing_tips(selected, chosen_look, tone, minutes, occasion),
            }
            st.session_state["bm_banner_idx"] = 0
            save_recommendation_history(ids, chosen_look)

    result = st.session_state.get("bm_last_result")
    if result:
        chosen_look = result["look"]
        look_desc, _direction, preferred_finishes = LOOK_DETAILS[chosen_look]
        st.divider()

        # Your own photos of the look: pinned top-right while you browse (arrows switch photos)
        my_images = find_my_look_images(chosen_look)
        if my_images:
            mood_board(my_images, chosen_look)

        # Hero: BeautyMix illustration + look details
        img_col, txt_col = st.columns([1, 2], vertical_alignment="center")
        with img_col:
            look_image = find_look_image(chosen_look)
            if look_image:
                st.image(str(look_image), caption="BeautyMix illustration", width="stretch")
            else:
                st.markdown("<div class='bm-placeholder'><div style='font-size:2.2rem'>✿</div><b>Look inspiration</b><br><small>Add an image to assets/looks.</small></div>", unsafe_allow_html=True)
        with txt_col:
            st.markdown(f"<div class='bm-eyebrow'>YOUR PERSONAL MAKEUP EDIT</div><h2>{chosen_look}</h2><p>{look_desc}</p>", unsafe_allow_html=True)
            chips = [result["vibe"], result["occasion"], result["weather"], result["minutes"]]
            st.markdown("".join(f"<span class='bm-chip'>{html.escape(c)}</span>" for c in chips), unsafe_allow_html=True)
            st.markdown("**Signature finishes:** " + " · ".join(preferred_finishes))
            pinterest_url = "https://www.pinterest.com/search/pins/?q=" + quote_plus(chosen_look + " makeup look")
            st.link_button("Find more inspiration on Pinterest", pinterest_url)
            if not my_images:
                st.caption("Tip: add your own photos to assets/my_looks to pin a mood board here.")

        by_id = {p["id"]: p for p in products}
        selected = [by_id[i] for i in result["ids"] if i in by_id]
        st.markdown("## Your products")
        if not selected:
            st.info("No products could be recommended yet. Add products to your collection.")
        # One frame per category, in a fixed order. Missing categories are skipped with a note.
        for category in CATEGORIES:
            items = [x for x in selected if x.get("category") == category]
            # Monochromatic Makeup: the recommended blush is also used as eye makeup
            eye_blush = [by_id[i] for i in result.get("mono_eye", []) if i in by_id] if category == "Eyeshadow" else []
            if category in result["missing"] and not eye_blush:
                st.info(f"No suitable {category} in your collection yet, so this step is skipped. Add one to complete the look!")
                continue
            if not items and not eye_blush:
                continue
            with st.container(border=True):
                total = len(items) + len(eye_blush)
                count_text = "1 product" if total == 1 else f"{total} products"
                st.markdown(f"<span class='bm-badge'>{category}</span> <span class='bm-count'>{count_text}</span>", unsafe_allow_html=True)
                if result.get("warnings", {}).get(category):
                    st.info(result["warnings"][category])
                for idx, p in enumerate(items):
                    if idx:
                        st.divider()
                    render_product_row(p, result["reasons"].get(p["id"], []))
                if eye_blush:
                    if items:
                        st.divider()
                    st.markdown("<span class='bm-badge soft'>Your blush, used on the eyes</span>", unsafe_allow_html=True)
                    for idx, p in enumerate(eye_blush):
                        if idx:
                            st.divider()
                        render_product_row(p, result.get("mono_eye_reasons", {}).get(p["id"], []))
                notes = result.get("cat_notes", {}).get(category, [])
                if notes:
                    with st.container(key=f"bm_note_{category}"):
                        st.markdown("**Layer & blend**" if len(items) > 1 else "**Look tip**")
                        st.markdown("\n".join(f"- {t}" for t in notes))

        # ---- Your Finishing Touches: warm OR cool, never both ----
        tone = result.get("tone", "warm")
        tiles = result.get("tips") or build_finishing_tips(selected, chosen_look, tone, result["minutes"], result["occasion"])
        st.markdown("## Your Finishing Touches")
        st.caption(TIPS[tone]["intro"])
        st.markdown(
            f"<div class='bm-tips {tone}'>" + "".join(f"<div class='bm-tip'><div class='bm-tip-t'>{t}</div><div>{html.escape(d)}</div></div>" for t, d in tiles) + "</div>",
            unsafe_allow_html=True,
        )
        st.caption("Warm and cool suggestions come from your product colours and are styling inspiration only; they do not determine your actual skin undertone.")
