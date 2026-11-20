"""The theme file must stay valid: if it cannot be read, Streamlit silently falls back to its default look."""

import tomllib
from pathlib import Path

CONFIG = Path(__file__).parent.parent / ".streamlit" / "config.toml"


def test_theme_file_can_be_read_and_has_light_and_dark_colours():
    theme = tomllib.loads(CONFIG.read_text())["theme"]
    for mode in ("light", "dark"):
        for key in ("primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor"):
            assert theme[mode][key].startswith("#"), f"{mode}.{key}"
