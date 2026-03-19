from pathlib import Path


def test_widget_css_is_scoped():
    css_path = Path(__file__).resolve().parents[1] / "apps" / "shopify-widget" / "src" / "styles" / "globals.css"
    css = css_path.read_text(encoding="utf-8")

    forbidden_selectors = [":root", "body", "html", "\n* {"]
    for selector in forbidden_selectors:
        assert selector not in css
