import json
import re

from aiogram.types import InlineKeyboardMarkup
from core.admin_settings import read_setting, write_setting

DEFAULT = {"primary":"#c7ef7c","secondary":"#323f2d","native":"default"}


def theme():
    return {**DEFAULT, **json.loads(read_setting("button_theme","{}"))}


def save_theme(values):
    if not isinstance(values,dict) or set(values)!=set(DEFAULT):
        raise ValueError
    if not all(isinstance(values[k],str) and re.fullmatch(r"#[0-9a-fA-F]{6}",values[k]) for k in ("primary","secondary")):
        raise ValueError
    if values["native"] not in ("default","primary","success","danger"):
        raise ValueError
    write_setting("button_theme",json.dumps(values))


async def style_keyboard(make_request,bot,method):
    markup=getattr(method,"reply_markup",None)
    if isinstance(markup,InlineKeyboardMarkup):
        style=theme()["native"]
        if style!="default":
            rows=[[b if getattr(b,"style",None) else b.model_copy(update={"style":style}) for b in row] for row in markup.inline_keyboard]
            method=method.model_copy(update={"reply_markup":InlineKeyboardMarkup(inline_keyboard=rows)})
    return await make_request(bot,method)
