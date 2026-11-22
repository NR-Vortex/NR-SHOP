from dataclasses import dataclass


@dataclass
class RequiredChannel:

    chat_id: str
    title: str
    invite_url: str
    enabled: bool = True


CHECK_CALLBACK = "force_join:check"

def required_channels():
    from os import getenv
    from core.admin_settings import read_setting
    if read_setting("join_enabled", "1") == "0":
        return []
    configured = read_setting("ads:channels", getenv("REQUIRED_CHANNELS", ""))
    return [RequiredChannel(handle, handle, "https://t.me/" + handle[1:]) for handle in configured.split()]
