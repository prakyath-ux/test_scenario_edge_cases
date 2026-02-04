# Automatic XPath - Project Documentation

## Project Goal
Build an automated QA testing tool that:
1. Captures XPaths and user input values from web forms via browser recording
2. Generates edge case test data for QA automation testing
3. Outputs in company format (7 header rows + edge case rows) for integration with automation scripts

---

## PROJECT STATUS: POC DELIVERED - DEMO READY (Feb 4, 2026)

### Current Version: `version4.1/` (Consolidated App)

| Component | Status | Location |
|-----------|--------|----------|
| XPath Recorder | COMPLETE | `version4.1/app.py` + `src/recorder.py` |
| Edge Case Generator | COMPLETE | `version4.1/app.py` (Groq LLM) |
| CSV Validator (12 checks) | COMPLETE | `version4.1/src/validator.py` |
| Live Capture View | COMPLETE | `version4.1/app.py` |
| Automation Page (Placeholder) | COMPLETE | `version4.1/pages/2_Test_Data.py` |

### Legacy Versions (Reference Only)
- `version4_QA/` - Original recorder prototype
- `test_case_generation/` - Standalone LLM generator

---

# SECTION 1: Architecture Overview

## version4.1/ Directory Structure

```
version4.1/
├── app.py                    # Main Streamlit dashboard (orchestrates everything)
├── src/
│   ├── recorder.py           # Playwright browser automation (spawned as subprocess)
│   ├── validator.py          # CSV validation (12 checks, imported by app.py)
│   └── llm_generator.py      # Standalone LLM generator (backup/reference)
├── pages/
│   └── 2_Test_Data.py        # Automation page (Jenkins integration - coming soon)
└── .live_capture.jsonl       # Real-time capture data (created during recording)
```

## How app.py Orchestrates Everything

```
app.py (Main Dashboard)
    │
    ├── subprocess.Popen() ──────► recorder.py (browser automation)
    │       │                           │
    │       │                           └── writes to .live_capture.jsonl
    │       │
    │       └── signal.SIGTERM ──────► stops recorder.py
    │
    ├── import validator ────────► validator.py (12 validation checks)
    │       │
    │       └── validate_edge_case_csv(df)
    │
    └── Groq API ────────────────► LLM edge case generation
            │
            └── model: llama-3.3-70b-versatile
```

---

# SECTION 2: CSV Output Format (v4.1)

## Company Format Structure (7 Header Rows)

```
Row 0: Steps            | 1        | 2        | 3        | ...
Row 1: Group            | Section1 | Section1 | Section2 | ...
Row 2: Elements         | firstName| lastName | email    | ...
Row 3: Property         | text     | text     | email    | ...
Row 4: Action           | click    | input    | input    | ...
Row 5: XPath            | //...    | //...    | //...    | ...
Row 6: Perfect_Template | Click    | JOHN     | test@... | ...
Row 7: Value_firstName  |          | edge|val | test@... | ...  (edge case row)
Row 8: Value_lastName   | Click    |          | test@... | ...  (edge case row)
...
```

| Row | Content | Description |
|-----|---------|-------------|
| 0 | Steps | Sequential step numbers (1, 2, 3...) |
| 1 | Group | Section/group names from recording |
| 2 | Elements | Field names/labels |
| 3 | Property | Element types (text, email, select, etc.) |
| 4 | Action | `click` or `input` |
| 5 | XPath | Element locators |
| 6 | Perfect_Template | All valid values (golden path) |
| 7+ | Value_fieldName | Edge case test rows (pipe-separated values) |

## Edge Case Format

Each edge case row tests ONE field with pipe-separated values:
```
empty | special_chars | numeric | long_input
  |         @#$%^&*    | 12345  | AAAA...(50 chars)
```

**Click columns**: Empty string `''` (automation checks Action row to know it's a click)

---

# SECTION 3: Running the Application

## Quick Start

```bash
cd version4.1
streamlit run app.py
```

## Workflow

1. **Page 1: XPath Analytics Recorder**
   - Enter URL → Start Recording → Interact with form → Stop Recording
   - Live view shows captured elements in real-time
   - Upload recorded CSV → Generate edge cases with LLM
   - Validate generated CSV (12 checks)
   - Download Company Format CSV

2. **Page 2: Test Automation** (Coming Soon)
   - Upload CSV for automation
   - Schedule Jenkins runs
   - View test reports

---

# SECTION 4: Key Files

## app.py (962 lines) - Main Dashboard

**Key Functions:**
- `transpose_to_company_format()` - Converts vertical to horizontal format
- `start_recording()` - Spawns recorder.py via subprocess
- `stop_recording()` - Sends SIGTERM to recorder process
- `generate_edge_cases()` - Calls Groq LLM API
- `create_output_dataframe()` - Builds final CSV structure

**LLM Configuration (line ~817):**
```python
model="llama-3.3-70b-versatile"  # Groq free tier
```

**Click handling (line ~736):**
```python
elif ftype == 'click':
    row.append('')  # Empty for click actions
```

## src/recorder.py (398 lines) - Browser Automation

**Key Concepts:**
- Playwright browser automation
- JavaScript injection for click/change event capture
- Writes to `.live_capture.jsonl` in real-time
- Signal handling for graceful shutdown

```python
signal.signal(signal.SIGTERM, cleanup_handler)
page.expose_function("recordAction", record_action_callback)
```

## src/validator.py (330 lines) - CSV Validation

**12 Validation Checks:**

| # | Check | Type |
|---|-------|------|
| 1 | Minimum Rows | FAIL if < 8 rows |
| 2 | Column Consistency | WARN if rows have < 50% columns |
| 3 | Header Row Labels | FAIL if missing Steps/Group/Elements/etc |
| 4 | Action Row Values | WARN if not click/input/change |
| 5 | XPath Row Format | WARN if XPaths don't start with // or /html |
| 6 | Perfect Template Completeness | WARN if > 30% empty |
| 7 | Edge Case Rows Exist | FAIL if no rows after row 6 |
| 8 | Pipe-Separated Values | FAIL if edge rows missing pipes |
| 9 | Single Edge Case Per Row | WARN if multiple pipes in one row |
| 10 | Edge Case Count (4 expected) | WARN if not exactly 4 values |
| 11 | Click Values Preserved | FAIL if click columns have values |
| 12 | Row Names (Value_fieldName) | WARN if naming pattern not followed |

**Usage:**
```python
from src.validator import validate_edge_case_csv, ValidationResult

result = validate_edge_case_csv(df)
print(result.is_valid)  # True/False
print(result.summary)   # {"valid": True, "passed": 10, "failed": 0, "warnings": 2}
```

---

# SECTION 5: Integration with Automation Scripts

## Integration Architecture

Your tool produces CSV files that automation scripts consume:

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR TOOL (app.py)                        │
│  Record → Generate Edge Cases → Validate → Export CSV        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     CSV File (Contract)
                     7 header rows + edge cases
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              AUTOMATION SCRIPTS               │
│  Read CSV → Parse XPaths → Execute Tests → Report Results    │
└─────────────────────────────────────────────────────────────┘
```

## Integration Patterns

**Pattern 1: Shared Folder**
```
/qa_automation/
├── test_data/           ← Your CSVs go here
│   └── edge_cases.csv
└── scripts/             ← Automation scripts read from here
    └── runner.py
```

**Pattern 2: Git-based**
```
qa-repo/
├── test_data/           ← You commit CSVs
├── automation/          ← QA dev's scripts
└── .github/workflows/   ← CI/CD pipelines
```

## What Automation Scripts Do With Your CSV

```python
# QA dev's runner.py (simplified)
df = pd.read_csv("edge_cases.csv", header=None)

xpaths = df.iloc[5, 1:].tolist()      # Row 5 = XPaths
actions = df.iloc[4, 1:].tolist()      # Row 4 = Actions

for test_row_idx in range(7, len(df)):  # Edge cases start at row 7
    test_values = df.iloc[test_row_idx, 1:].tolist()

    for i, (xpath, action, value) in enumerate(zip(xpaths, actions, test_values)):
        element = driver.find_element("xpath", xpath)
        if action == 'click':
            element.click()
        else:
            if '|' in str(value):
                # Test each edge case
                for edge_val in value.split('|'):
                    element.send_keys(edge_val.strip())
```

## Responsibility Split

| Your Tool (AI Intern) | Automation Scripts (Senior Dev) |
|----------------------|--------------------------------|
| Generate valid CSV structure | Parse and read CSV |
| Ensure 7 header rows correct | Navigate to target URL |
| Generate edge cases with LLM | Execute browser actions |
| Validate before handoff | Handle assertions/validation |
| Export Company Format | Report to Jenkins/CI |

---

# SECTION 6: Environment Setup

## Dependencies

```
playwright>=1.48.0
streamlit>=1.32.0
pandas
numpy
groq
python-dotenv
```

## Install

```bash
pip install playwright streamlit pandas numpy groq python-dotenv
playwright install chromium
```

## Environment Variables

```bash
export GROQ_API_KEY="your-groq-api-key"
```

Or create `.env` file in `version4.1/`:
```
GROQ_API_KEY=your-groq-api-key
```

---

# SECTION 7: Quick Reference

## Commands

```bash
# Main App (v4.1)
cd version4.1 && streamlit run app.py

# Validate CSV from command line
python version4.1/src/validator.py path/to/file.csv
```

## Key Files

| Purpose | File |
|---------|------|
| Main dashboard | `version4.1/app.py` |
| Browser recorder | `version4.1/src/recorder.py` |
| CSV validator | `version4.1/src/validator.py` |
| Automation page | `version4.1/pages/2_Test_Data.py` |

## LLM Details

- **Provider:** Groq Cloud
- **Model:** llama-3.3-70b-versatile
- **Tier:** Free (sufficient for demo)
- **Spend:** ~$0.03 USD (plenty of headroom)

---

# SECTION 8: Terminology

| Term | Definition |
|------|------------|
| Company Format | Horizontal CSV with 7 header rows + edge case rows |
| Edge Case | Boundary/invalid input (empty, special, numeric, long) |
| Perfect Template | Row 6 - all valid values (golden path) |
| Pipe-separated | Edge case format: `val1 | val2 | val3 | val4` |
| XPath | XML Path - locator to find elements on webpage |
| Vertical Format | Standard row-per-action format (input to generator) |

---

**Last Updated:** February 4, 2026
**Status:** POC DELIVERED - DEMO READY
**Current Version:** version4.1
