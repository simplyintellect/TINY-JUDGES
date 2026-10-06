import os
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CASES_DIR = Path("cases")
HTML_DIR = CASES_DIR / "html"

CASES_DATA = [
    {
        "id": "case_01",
        "type": "clear",
        "description": "Mobile UI with a fixed 600px width banner causing horizontal page overflow scroll on a 390px mobile screen.",
        "must_find": [
            ["overflow", "horizontal", "scroll", "width", "cut off", "clipping", "exceeds", "600px", "too wide"]
        ],
        "false_claims": ["broken image", "typo", "low contrast"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; font-family: sans-serif; background: #f8fafc; }
    .header { background: #0f172a; color: white; padding: 15px; text-align: center; }
    .container { padding: 15px; }
    .overflow-card { width: 600px; background: #2563eb; color: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .content { margin-top: 15px; color: #334155; font-size: 14px; }
  </style>
</head>
<body>
  <div class="header"><h3>Dashboard</h3></div>
  <div class="container">
    <div class="overflow-card">
      <h2>Featured Mobile Banner (Fixed 600px Width)</h2>
      <p>This box is 600px wide, forcing the 390px viewport to scroll horizontally.</p>
    </div>
    <div class="content"><p>Standard responsive text paragraph underneath.</p></div>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_02",
        "type": "clear",
        "description": "Form page where an absolute positioned submit button directly overlaps and obscures body text.",
        "must_find": [
            ["overlap", "overlapping", "obscures", "covers", "collides", "on top of", "unreadable", "blocked"]
        ],
        "false_claims": ["missing image", "spelling error", "dark mode violation"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #ffffff; }
    .card { position: relative; height: 300px; border: 1px solid #e2e8f0; padding: 20px; border-radius: 10px; }
    .text-content { position: absolute; top: 30px; left: 20px; right: 20px; font-size: 16px; color: #0f172a; line-height: 1.5; }
    .btn-overlap { position: absolute; top: 40px; left: 20px; width: 280px; height: 50px; background: #dc2626; color: white; font-weight: bold; border: none; border-radius: 6px; }
  </style>
</head>
<body>
  <h2>User Feedback</h2>
  <div class="card">
    <div class="text-content">
      Please review terms carefully before submitting. All information submitted here will be permanently logged into your audit account history.
    </div>
    <button class="btn-overlap">SUBMIT FEEDBACK</button>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_03",
        "type": "clear",
        "description": "Primary action button rendered with white text on a white background, making button text invisible.",
        "must_find": [
            ["invisible", "contrast", "white text", "white background", "unreadable", "hidden text", "same color", "cannot see"]
        ],
        "false_claims": ["horizontal overflow", "wrong layout", "broken flexbox"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #f1f5f9; }
    .checkout-box { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
    .btn-invisible { background-color: #ffffff; color: #ffffff; border: 2px solid #cbd5e1; font-size: 16px; font-weight: bold; padding: 14px 28px; border-radius: 8px; width: 100%; cursor: pointer; }
  </style>
</head>
<body>
  <div class="checkout-box">
    <h3>Order Summary</h3>
    <p>Total Amount: $49.99</p>
    <button class="btn-invisible">CONFIRM PURCHASE</button>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_04",
        "type": "clear",
        "description": "Modal dialog whose bottom content and action buttons are truncated off the bottom of the screen.",
        "must_find": [
            ["clipped", "cut off", "truncated", "overflow", "bottom", "hidden", "outside viewport", "cannot reach"]
        ],
        "false_claims": ["misaligned icon", "font family error", "bad gradient"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; background: rgba(0,0,0,0.6); font-family: sans-serif; height: 844px; overflow: hidden; }
    .modal-container { position: fixed; top: 60px; left: 15px; right: 15px; height: 950px; background: white; border-radius: 16px; padding: 24px; box-sizing: border-box; }
    .modal-title { font-size: 20px; color: #0f172a; margin-bottom: 15px; }
    .modal-body { font-size: 15px; color: #475569; line-height: 1.6; }
    .actions { position: absolute; bottom: 20px; left: 20px; right: 20px; display: flex; gap: 10px; }
    .btn { flex: 1; padding: 12px; background: #0284c7; color: white; border: none; border-radius: 8px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="modal-container">
    <div class="modal-title">Terms & Conditions Agreement</div>
    <div class="modal-body">
      <p>Section 1: User consent policy guidelines for application data processing.</p>
      <p>Section 2: Security protocol details and data retention schedules.</p>
      <p>Section 3: Third party integrations and data exchange compliance rules.</p>
      <p>Section 4: User account management rights and revocation procedures.</p>
      <p>Section 5: Final liability limit clauses and arbitration jurisdiction.</p>
    </div>
    <div class="actions">
      <button class="btn">DECLINE</button>
      <button class="btn">ACCEPT TERMS</button>
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_05",
        "type": "subtle",
        "description": "Search input box where the search magnifying glass icon is misaligned 6px higher than text input baseline.",
        "must_find": [
            ["misaligned", "icon", "vertical", "offset", "alignment", "uneven", "top", "not centered"]
        ],
        "false_claims": ["white text", "horizontal scrollbar", "missing header"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #ffffff; }
    .search-container { display: flex; align-items: flex-start; border: 2px solid #94a3b8; border-radius: 8px; padding: 12px; }
    .search-icon { font-size: 20px; position: relative; top: -8px; margin-right: 10px; }
    .search-input { border: none; outline: none; font-size: 16px; width: 100%; color: #1e293b; font-family: inherit; }
  </style>
</head>
<body>
  <h3>Search Products</h3>
  <div class="search-container">
    <span class="search-icon">🔍</span>
    <input type="text" class="search-input" value="Wireless Headphones" readonly>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_06",
        "type": "subtle",
        "description": "Article paragraph with cramped line-height (0.80) causing text lines to touch and slightly overlap.",
        "must_find": [
            ["line-height", "line height", "cramped", "touching", "squished", "spacing", "line spacing", "overlap"]
        ],
        "false_claims": ["broken image", "contrast ratio under 1.5", "missing cta"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #f8fafc; }
    .article-card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; }
    .title { font-size: 20px; margin-bottom: 10px; color: #0f172a; }
    .body-text { font-size: 17px; line-height: 0.80; color: #334155; }
  </style>
</head>
<body>
  <div class="article-card">
    <div class="title">Product Updates 2026</div>
    <div class="body-text">
      Our team is excited to release new features for mobile performance optimization. All client assets have been re-indexed to improve rendering speed, reduce layout shifts, and enhance visual audit metrics across mobile screens.
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_07",
        "type": "subtle",
        "description": "Footer disclaimer text using faint light grey text (#e2e8f0) on white background violating contrast standards.",
        "must_find": [
            ["contrast", "faint", "pale", "light gray", "light grey", "unreadable", "accessibility", "low contrast"]
        ],
        "false_claims": ["horizontal overflow", "button overlap", "missing navigation"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #ffffff; }
    .card { border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; }
    .disclaimer { font-size: 13px; color: #e2e8f0; background: #ffffff; margin-top: 15px; }
  </style>
</head>
<body>
  <div class="card">
    <h3>Account Registration</h3>
    <p style="color: #1e293b;">Click submit to complete your account setup process.</p>
    <div class="disclaimer">
      * Notice: By clicking submit, you accept all electronic communications and mandatory updates.
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_08",
        "type": "no_bug",
        "description": "Clean, properly styled mobile login form with no visual defects or layout bugs.",
        "must_find": [],
        "false_claims": ["overlap", "cut off", "unreadable", "misaligned", "contrast issue", "broken layout"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 24px; font-family: sans-serif; background: #f8fafc; }
    .form-card { background: white; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    h2 { margin-top: 0; color: #0f172a; }
    label { display: block; margin-top: 15px; margin-bottom: 6px; font-size: 14px; color: #475569; font-weight: 600; }
    input { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
    button { width: 100%; margin-top: 24px; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
  </style>
</head>
<body>
  <div class="form-card">
    <h2>Sign In</h2>
    <label>Email Address</label>
    <input type="email" value="alex@example.com" readonly>
    <label>Password</label>
    <input type="password" value="••••••••••••" readonly>
    <button>Log In</button>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_09",
        "type": "no_bug",
        "description": "Clean e-commerce product card with high resolution image placeholder, title, rating, price, and CTA.",
        "must_find": [],
        "false_claims": ["truncated", "overlapping text", "low contrast", "horizontal scroll", "clipped"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #f1f5f9; }
    .product-card { background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }
    .img-box { height: 160px; background: #3b82f6; display: flex; align-items: center; justify-content: center; color: white; font-size: 32px; font-weight: bold; }
    .info { padding: 16px; }
    .title { font-size: 18px; font-weight: bold; color: #0f172a; margin: 0 0 6px 0; }
    .price { font-size: 20px; font-weight: 800; color: #16a34a; margin-bottom: 12px; }
    .btn { width: 100%; padding: 12px; background: #0f172a; color: white; border: none; border-radius: 8px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="product-card">
    <div class="img-box">🎧 HEADPHONES</div>
    <div class="info">
      <div class="title">Pro Wireless Headset</div>
      <div class="price">$129.99</div>
      <button class="btn">Add to Cart</button>
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "case_10",
        "type": "vague",
        "description": "Settings page with a dark theme toggle situated near a floating action badge, creating ambiguous visual hierarchy.",
        "must_find": [
            ["ambiguous", "hierarchy", "spacing", "alignment", "toggle", "gap", "confusing", "floating"]
        ],
        "false_claims": ["white on white text", "page crash", "horizontal overflow scrollbar"],
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=390, initial-scale=1.0">
  <style>
    body { margin: 0; padding: 20px; font-family: sans-serif; background: #0f172a; color: white; }
    .setting-item { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 16px; border-radius: 10px; margin-bottom: 15px; position: relative; }
    .label { font-size: 16px; }
    .floating-badge { position: absolute; right: 80px; top: 12px; background: #f59e0b; color: black; font-size: 10px; padding: 3px 6px; border-radius: 4px; font-weight: bold; }
    .toggle { width: 44px; height: 24px; background: #10b981; border-radius: 12px; position: relative; }
    .toggle-knob { width: 20px; height: 20px; background: white; border-radius: 10px; position: absolute; top: 2px; right: 2px; }
  </style>
</head>
<body>
  <h3>Preferences</h3>
  <div class="setting-item">
    <span class="label">Dark Mode</span>
    <span class="floating-badge">BETA</span>
    <div class="toggle"><div class="toggle-knob"></div></div>
  </div>
</body>
</html>"""
    }
]

def generate_test_cases():
    CASES_DIR.mkdir(exist_ok=True)
    HTML_DIR.mkdir(exist_ok=True)

    print("Generating HTML files and Ground Truth JSON specs...")
    for cdata in CASES_DATA:
        cid = cdata["id"]
        html_file = HTML_DIR / f"{cid}.html"
        json_file = CASES_DIR / f"{cid}.json"

        # Write HTML
        html_file.write_text(cdata["html"], encoding="utf-8")

        # Write metadata JSON
        spec = {
            "id": cid,
            "description": cdata["description"],
            "type": cdata["type"],
            "must_find": cdata["must_find"],
            "false_claims": cdata["false_claims"],
            "image_path": str((CASES_DIR / f"{cid}.png").resolve())
        }
        json_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        print(f"Created {html_file} and {json_file}")

    print("\nCapturing 390px Playwright Screenshots...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            
            for cdata in CASES_DATA:
                cid = cdata["id"]
                html_file = (HTML_DIR / f"{cid}.html").resolve()
                png_file = (CASES_DIR / f"{cid}.png").resolve()

                page.goto(html_file.as_uri())
                page.wait_for_load_state("networkidle")
                page.screenshot(path=str(png_file), full_page=False)
                print(f"Captured screenshot: {png_file}")

            browser.close()
        print("\nAll 10 test cases generated successfully!")
    except Exception as e:
        print(f"\nCRITICAL PLAYWRIGHT FAILURE: {type(e).__name__}: {e}", file=sys.stderr)
        print("Please check Playwright installation.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_test_cases()
