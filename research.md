# XPath Extraction Tool - Research & Documentation

## Project Overview

A tool that opens a browser, allows users to click on elements, and captures XPaths + input values in the background. Built for QA teams to visually identify and record web elements for test automation.

---

## Project Structure

```
autoomatic_xpath/
├── version3.py          # Main recorder - captures XPaths + values
├── app.py               # Streamlit dashboard - displays results
├── requirements.txt     # Dependencies (playwright, streamlit, pandas)
├── research.md          # This documentation
├── xpaths_*.json        # Captured session data
├── xpaths_*.py          # Python export format
├── xpaths_*.csv         # CSV export format
└── venv/                # Python virtual environment
```

---

## How It Works

### Step 1: Run the Recorder (version3.py)

```bash
python version3.py
```

1. Enter URL when prompted
2. Choose output format (1-4)
3. Browser opens with the URL
4. **Hover** over elements → red highlight shows what you're targeting
5. **Click** element → XPath captured
6. **Type/Select** value → value captured on field blur
7. Press **Enter** in terminal when done
8. Files saved with timestamp

### Step 2: View Results (app.py)

```bash
streamlit run app.py
```

1. Select a captured session from dropdown
2. Choose view:
   - **Full Data** - All columns including XPath
   - **Simple View** - Element, Action, Strategy, Value (no XPath)
   - **Developer View** - Element, XPath, Action
   - **QA View** - Element, Action, Value
3. Download as CSV or JSON

---

## Technical Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (Playwright Chromium)                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Injected JavaScript (XPATH_JS)                      │   │
│  │  - mouseover listener → highlight element            │   │
│  │  - click listener → getXPath() → reportXPath()       │   │
│  │  - change listener → getXPath() + value → reportXPath│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ window.reportXPath(label, xpath, strategy, matches, action, value)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Python (version3.py)                                       │
│  - page.expose_function("reportXPath", handle_xpath)        │
│  - handle_xpath() stores in captured_xpaths dict            │
│  - On exit: save to .json, .py, .csv files                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Streamlit Dashboard (app.py)                               │
│  - Loads .json files                                        │
│  - Displays in pandas DataFrame                             │
│  - Multiple view options                                    │
│  - Download functionality                                   │
└─────────────────────────────────────────────────────────────┘
```

### XPath Generation Strategy (Priority Order)

| Priority | Strategy | Example | When Used |
|----------|----------|---------|-----------|
| 1 | id | `//*[@id="firstName"]` | Element has unique ID |
| 2 | name | `//input[@name="email"]` | Form fields with name attr |
| 3 | data-testid | `//*[@data-testid="submit-btn"]` | QA-friendly attribute |
| 4 | data-testid + text | `//*[@data-testid="btn" and contains(., "Save")]` | When data-testid not unique |
| 5 | aria-label | `//*[@aria-label="Close"]` | Accessibility attribute |
| 6 | role | `//*[@role="button"]` | Semantic role |
| 7 | role + text | `//*[@role="button" and contains(., "Submit")]` | When role not unique |
| 8 | placeholder | `//input[@placeholder="Enter name"]` | Input placeholder |
| 9 | type | `//input[@type="email"]` | Input type |
| 10 | type + name | `//input[@type="text" and @name="user"]` | Combined attributes |
| 11 | href | `//a[@href="/about"]` | Links |
| 12 | class | `//div[contains(@class, "modal")]` | CSS class (less stable) |
| 13 | text | `//button[contains(., "Submit")]` | Element text content |
| 14 | absolute | `/html/body/div[1]/form/input[3]` | Fallback when nothing unique |

### Uniqueness Validation

Every XPath is validated using `countMatches()`:
```javascript
function countMatches(xpath) {
    const result = document.evaluate(xpath, document, null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    return result.snapshotLength;
}
```
- If count = 1 → XPath is unique ✓
- If count > 1 → Try next strategy or combine attributes

---

## Key Code Sections

### version3.py

| Section | Lines | Purpose |
|---------|-------|---------|
| Imports | 1-22 | Dependencies |
| captured_xpaths | 24 | Global dict storing all captures |
| XPATH_JS | 26-207 | JavaScript injected into browser |
| countMatches() | 34-41 | Validates XPath uniqueness |
| getAbsoluteXPath() | 43-62 | Builds fallback absolute path |
| getXPath() | 64-160 | Main XPath generation logic |
| highlightElement() | 162-180 | Red outline on hover |
| Event listeners | 182-205 | click + change capture |
| handle_xpath() | 211-236 | Python receives data from JS |
| save_python/json/csv() | 240-275 | Export functions |
| main() | 278-334 | Entry point |

### app.py

| Section | Lines | Purpose |
|---------|-------|---------|
| Config + CSS | 1-45 | Dark theme styling |
| File loader | 54-65 | Load JSON sessions |
| Summary stats | 68-77 | Metrics display |
| View options | 82-114 | 4 different table views |
| Download | 120-130 | CSV/JSON export |

---

## Data Schema

### JSON Output Structure

```json
{
  "url": "https://example.com/form",
  "captured_at": "2026-01-22T10:30:00.000000",
  "total_elements": 12,
  "xpaths": [
    {
      "label": "firstName",
      "xpath": "//*[@id=\"firstName\"]",
      "strategy": "id",
      "matches": 1,
      "action": "click",
      "values": ""
    },
    {
      "label": "firstName",
      "xpath": "//*[@id=\"firstName\"]",
      "strategy": "id",
      "matches": 1,
      "action": "change",
      "values": "JOHN"
    }
  ]
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| label | string | Human-readable name (id/name/placeholder/text) |
| xpath | string | Generated XPath selector |
| strategy | string | Which method found the XPath |
| matches | int | How many elements match (should be 1) |
| action | string | "click" or "change" |
| values | string | Value entered (empty for clicks) |

---

## Event Capture Logic

### Click Event
- Fires when user clicks any element
- Captures: element label + XPath
- Value: empty string `""`

### Change Event
- Fires when user leaves a field (blur) after changing value
- Captures: element label + XPath + entered value
- For checkboxes: captures `true`/`false`
- For text inputs: captures the text
- For dropdowns: captures selected option text

### Duplicate Handling
- Key: `xpath|action` (e.g., `//*[@id="name"]|click`)
- Same element clicked twice → updates existing entry
- Same element: click + change = 2 separate entries

---

## Commands Reference

### Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Run
```bash
# Capture XPaths
python version3.py

# View dashboard
streamlit run app.py

# Stop Streamlit
Ctrl + C
```

### Git
```bash
git add .
git commit -m "message"
git push origin main
git pull origin main
```

---

## Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| Framework | Playwright | Better CDP support, modern API |
| XPath style | Relative with fallback | Stable but handles edge cases |
| Wildcard `*` vs tag | `*` | Flexibility, works if tag changes |
| Case sensitivity | Sensitive | Matches exact DOM values |
| Output format | Multiple (py/json/csv) | Different use cases |
| Dashboard | Streamlit | Quick to build, looks professional |

---

## Future Enhancements (V4+)

### For Test Case Generation
- [ ] Detect element types (text, dropdown, checkbox, radio)
- [ ] Capture ALL dropdown options (not just selected)
- [ ] Track action sequence/order
- [ ] Detect state dependencies (field A appears after selecting B)
- [ ] Generate permutation combinations
- [ ] SQLite storage for relational data

### UI/UX
- [ ] Run recorder from Streamlit
- [ ] Live capture preview
- [ ] Edit/delete captured entries
- [ ] Session comparison

### Edge Cases
- [ ] Handle iframes
- [ ] Handle shadow DOM
- [ ] Better error messages on close

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `greenlet` build error | Use Python 3.12 or earlier, or `playwright>=1.48.0` |
| Dashboard shows no data | Run version3.py first, choose format 2 or 4 (JSON) |
| XPath shows multiple matches | Element lacks unique attributes, falls back to absolute |
| Browser closes immediately | Check for Python errors in terminal |
| Streamlit won't start | Check if port 8501 is free, or use `--server.port XXXX` |

---

## Original Research (Preserved)

### Problem Statement
Build a tool that:
1. Opens a browser window with a given URL
2. Allows user to click on any element
3. Captures and saves the XPath of clicked elements in the background

### Why This Approach

| Problem with Manual XPath Finding | How This Tool Solves It |
|----------------------------------|-------------------------|
| QA gets XPath list, doesn't know what's what | QA clicks element → sees it highlighted → XPath saved with context |
| Different websites need different scripts | One tool works for any URL |
| Dynamic fields hard to capture | User triggers the fields themselves, then clicks to capture |
| Nested/conditional logic breaks automation | Human decides what to click, tool just records |

### Target Website
**URL**: https://qa-tq-awp.impactodigifin.xyz/newapplication
**Type**: TECU Credit Union - New Member Onboarding Form
**Stack**: Next.js (React)

---

*Last updated: 2026-01-22*
