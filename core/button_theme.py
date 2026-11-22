import json
import re
from urllib.parse import urlsplit

from aiogram.types import InlineKeyboardMarkup
from core.admin_settings import read_setting, write_setting

LAYOUTS = ("tiles", "list", "compact", "feature")
NATIVE_STYLES = ("default", "primary", "success", "danger")
PALETTE_FIELDS = ("primary", "secondary", "background", "surface")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
BUTTON_KEY = re.compile(r"[A-Za-z0-9_.:/-]{1,120}")
DEFAULT = {
    "primary": "#e9c88e",
    "secondary": "#252335",
    "background": "#101019",
    "surface": "#191927",
    "native": "default",
    "layout": "tiles",
    "chat_layout": "tiles",
    "buttons": {},
}


def theme():
    return {**DEFAULT, **json.loads(read_setting("button_theme","{}"))}


def storefront_theme():
    appearance = theme()
    public_prefixes = ("miniapp:","shop:category:","webapp:","panel:","agency:")
    public_actions = {"shop:home","shop:orders","support:menu"}
    appearance["buttons"] = {
        key: rules for key,rules in appearance["buttons"].items()
        if key in public_actions or key.startswith(public_prefixes)
        if not any(part.isdecimal() for part in key.split(":"))
    }
    return appearance


def save_theme(values):
    if not isinstance(values,dict) or not values.keys() <= DEFAULT.keys():
        raise ValueError("Unknown theme settings")
    merged = {**theme(), **values}
    if not all(isinstance(merged[key],str) and COLOR.fullmatch(merged[key]) for key in PALETTE_FIELDS):
        raise ValueError("Invalid color")
    if merged["native"] not in NATIVE_STYLES or any(merged[key] not in LAYOUTS for key in ("layout","chat_layout")):
        raise ValueError("Invalid layout or Telegram style")
    overrides = merged["buttons"]
    if not isinstance(overrides,dict) or len(overrides)>600:
        raise ValueError("Too many button overrides")
    for key, rules in overrides.items():
        if not BUTTON_KEY.fullmatch(key) or not isinstance(rules,dict) or not rules.keys() <= {"web","native"}:
            raise ValueError("Invalid button rule")
        if "web" in rules and (not isinstance(rules["web"],str) or not COLOR.fullmatch(rules["web"])):
            raise ValueError("Invalid button color")
        if "native" in rules and rules["native"] not in NATIVE_STYLES:
            raise ValueError("Invalid Telegram button style")
    write_setting("button_theme",json.dumps(merged,separators=(",",":")))


def button_key(button):
    if button.callback_data:
        return button.callback_data
    target = button.web_app.url if button.web_app else button.url
    if target:
        parsed=urlsplit(target)
        key=("webapp:"+parsed.path) if button.web_app else ("link:"+parsed.netloc+parsed.path)
        return key if BUTTON_KEY.fullmatch(key) else None
    return None


def layout_keyboard(rows, *, pack_tiles=False):
    layout = theme()["chat_layout"]
    if layout == "tiles" and not pack_tiles:
        return rows
    buttons = [button for row in rows for button in row]
    if layout == "list":
        return [[button] for button in buttons]
    if layout == "feature":
        first = [[button] for button in buttons[:2]]
        rest = buttons[2:]
        return first + [rest[i:i+2] for i in range(0,len(rest),2)]
    width = 2 if layout == "tiles" else 3
    return [buttons[i:i+width] for i in range(0,len(buttons),width)]


async def style_keyboard(make_request,bot,method):
    markup = getattr(method,"reply_markup",None)
    if isinstance(markup,InlineKeyboardMarkup):
        appearance=theme()
        rows=[]
        for row in markup.inline_keyboard:
            styled=[]
            for button in row:
                rules=appearance["buttons"].get(button_key(button),{})
                color=rules.get("native",getattr(button,"style",None) or appearance["native"])
                styled.append(button.model_copy(update={"style":None if color=="default" else color}))
            rows.append(styled)
        method=method.model_copy(update={"reply_markup":InlineKeyboardMarkup(inline_keyboard=rows)})
    return await make_request(bot,method)
