"""Colour helpers shared by the extractor, the builder and the gates. Standard library only."""
import math
import re

NAMED = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "transparent": None,
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "gold": (255, 215, 0),
    "orange": (255, 165, 0),
    "crimson": (220, 20, 60),
    "navy": (0, 0, 128),
    "teal": (0, 128, 128),
    "ivory": (255, 255, 240),
    "whitesmoke": (245, 245, 245),
}


def _clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def _hsl_to_rgb(hue: float, sat: float, light: float) -> tuple[int, int, int]:
    hue = (hue % 360) / 360
    if sat == 0:
        grey = _clamp(light * 255)
        return grey, grey, grey

    def channel(shift: float) -> float:
        t = (hue + shift) % 1
        q = light * (1 + sat) if light < 0.5 else light + sat - light * sat
        p = 2 * light - q
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return _clamp(channel(1 / 3) * 255), _clamp(channel(0) * 255), _clamp(channel(-1 / 3) * 255)


def _linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * (value ** (1 / 2.4)) - 0.055


def _oklab_to_rgb(light: float, a: float, b: float) -> tuple[int, int, int]:
    l_ = (light + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (light - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (light - 0.0894841775 * a - 1.2914855480 * b) ** 3
    red = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    green = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    blue = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return (
        _clamp(_linear_to_srgb(red) * 255),
        _clamp(_linear_to_srgb(green) * 255),
        _clamp(_linear_to_srgb(blue) * 255),
    )


def _number(token: str, scale: float = 1.0) -> float:
    token = token.strip()
    if token.endswith("%"):
        return float(token[:-1]) / 100 * scale
    token = re.sub(r"(deg|turn|rad)$", "", token)
    return float(token)


def parse_color(text: str):
    """Return (r, g, b, alpha) for a CSS colour, or None when it is not a plain colour."""
    if not text:
        return None
    value = text.strip().lower().rstrip(";").replace("!important", "").strip()
    if value in NAMED:
        rgb = NAMED[value]
        return None if rgb is None else (*rgb, 1.0)

    hex_match = re.fullmatch(r"#([0-9a-f]{3,8})", value)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(char * 2 for char in digits)
        if len(digits) not in (6, 8):
            return None
        red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return red, green, blue, alpha

    func_match = re.fullmatch(r"(rgba?|hsla?|oklch|oklab)\(([^()]*)\)", value)
    if not func_match:
        return None
    name, body = func_match.groups()
    alpha = 1.0
    if "/" in body:
        body, alpha_text = body.split("/", 1)
        try:
            alpha = _number(alpha_text)
        except ValueError:
            return None
    parts = [part for part in re.split(r"[\s,]+", body.strip()) if part]
    try:
        if len(parts) == 4:
            alpha = _number(parts[3])
            parts = parts[:3]
        if len(parts) != 3:
            return None
        if name.startswith("rgb"):
            red, green, blue = (_clamp(_number(part, 255)) for part in parts)
            return red, green, blue, alpha
        if name.startswith("hsl"):
            red, green, blue = _hsl_to_rgb(_number(parts[0]), _number(parts[1]), _number(parts[2]))
            return red, green, blue, alpha
        if name == "oklch":
            light = _number(parts[0])
            chroma = _number(parts[1], 0.4)
            hue = math.radians(_number(parts[2]))
            red, green, blue = _oklab_to_rgb(light, chroma * math.cos(hue), chroma * math.sin(hue))
            return red, green, blue, alpha
        red, green, blue = _oklab_to_rgb(_number(parts[0]), _number(parts[1], 0.4), _number(parts[2], 0.4))
        return red, green, blue, alpha
    except ValueError:
        return None


def to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def over(color, background) -> tuple[int, int, int]:
    """Composite a colour with alpha over an opaque background."""
    alpha = color[3] if len(color) > 3 else 1.0
    return tuple(_clamp(color[i] * alpha + background[i] * (1 - alpha)) for i in range(3))


def luminance(rgb) -> float:
    def channel(value: int) -> float:
        value = value / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def contrast(first, second) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def hue_sat(rgb) -> tuple[float, float, float]:
    """Hue in degrees, saturation and lightness (HSL), each sat/light in 0..1."""
    red, green, blue = (value / 255 for value in rgb[:3])
    high, low = max(red, green, blue), min(red, green, blue)
    light = (high + low) / 2
    if high == low:
        return 0.0, 0.0, light
    spread = high - low
    sat = spread / (2 - high - low) if light > 0.5 else spread / (high + low)
    if high == red:
        hue = ((green - blue) / spread) % 6
    elif high == green:
        hue = (blue - red) / spread + 2
    else:
        hue = (red - green) / spread + 4
    return hue * 60, sat, light


def hue_name(rgb) -> str:
    hue, sat, light = hue_sat(rgb)
    if sat < 0.12:
        if light > 0.85:
            return "white"
        if light < 0.2:
            return "black"
        return "grey"
    bands = [
        (15, "red"),
        (40, "orange"),
        (65, "yellow"),
        (95, "lime"),
        (160, "green"),
        (195, "teal"),
        (255, "blue"),
        (290, "violet"),
        (335, "pink"),
        (361, "red"),
    ]
    for limit, name in bands:
        if hue < limit:
            return name
    return "red"
