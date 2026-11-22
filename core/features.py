# NR SHOP - Feature Management

from core.admin_settings import read_setting, write_setting

FEATURES = {

    # Main Categories
    "ai": True,
    "vpn": True,
    "telegram": False,
    "vps": True,

    # User Services
    "orders": True,
    "support": True,

}


for key, default in FEATURES.items():
    FEATURES[key] = read_setting('feature.' + key, str(int(default))) == '1'


def is_feature_enabled(feature: str) -> bool:
    """
    Check whether a feature is enabled.
    """

    return FEATURES.get(feature, False)


def set_feature(feature: str, status: bool):
    """
    Enable or disable a feature.
    """

    if feature not in FEATURES:
        raise ValueError(f"Unknown feature: {feature}")

    write_setting('feature.' + feature, str(int(status)))
    FEATURES[feature] = status