# Automatic XPath - Complete Project Manual

**Version:** 4.1
**Status:** POC Delivered - Demo Ready
**Last Updated:** February 5, 2026
**Team:** QA Automation - Impacto Digital

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [System Architecture](#4-system-architecture)
5. [Data Flow](#5-data-flow)
6. [Component Deep Dive](#6-component-deep-dive)
7. [XPath Strategy Priority](#7-xpath-strategy-priority)
8. [Edge Case Generation](#8-edge-case-generation)
9. [CSV Format Specification](#9-csv-format-specification)
10. [Validation Rules](#10-validation-rules)
11. [Integration Architecture](#11-integration-architecture)
12. [Technology Stack](#12-technology-stack)
13. [Environment Setup & Running](#13-environment-setup--running)
14. [Directory Structure](#14-directory-structure)
15. [Known Limitations & Future Work](#15-known-limitations--future-work)

---

## 1. Executive Summary

Automatic XPath is a QA automation tool that records user interactions on web forms, captures XPath locators for every element, and uses an LLM to generate edge case test data. The output is a standardized Company Format CSV that automation engineers consume to run regression tests. The tool replaces the manual process of inspecting elements, writing XPaths by hand, and thinking up test edge cases, reducing a multi-hour task to minutes.

**Current Status:** Proof of Concept delivered and demo-ready. The recorder, generator, and validator are complete. Jenkins integration for automated test execution is planned but not yet implemented.

---

## 2. Problem Statement

### Why This Tool Exists

QA automation testing for web applications requires two things: knowing WHERE to interact (XPaths) and knowing WHAT to type (test data). Both of these are painful to produce manually.

**Problem 1: XPath Capture is Tedious**
- QA engineers open browser DevTools, right-click elements, copy XPaths one by one
- A single form with 30 fields means 30+ manual inspections
- XPaths copied from DevTools are often absolute paths (fragile, break when page structure changes)
- No standardized format; every engineer captures differently

**Problem 2: Edge Case Generation Requires Expertise**
- QA engineers must think of boundary values for every field: empty strings, special characters, overly long inputs, numeric-only values
- This is repetitive and error-prone (humans forget edge cases)
- Different engineers produce inconsistent test data
- No validation that the generated data follows the expected format

**Problem 3: No Standard Handoff Format**
- The QA recorder tool and the automation scripts need a shared contract
- Without a standard CSV format, integration breaks every time someone changes the structure
- Manual copy-paste between tools introduces errors

**Problem 4: Time Pressure**
- Teams need to test new features quickly
- Manual XPath capture + test data creation can take hours per form
- Edge cases are often skipped due to time constraints

---

## 3. Solution Overview

### What We Built

A 3-page Streamlit web application that automates the entire workflow:

```
RECORD ──► GENERATE ──► VALIDATE ──► EXPORT
  │            │             │           │
  │            │             │           └── Company Format CSV
  │            │             └── 12 structural checks
  │            └── LLM edge case generation (Groq)
  └── Playwright browser automation
```

**Page 1: XPath Analytics Recorder** (`app.py`)
- Enter a URL, click Start Recording
- A Chromium browser opens; interact with the form normally
- Every click and input is captured with its XPath, action, value, and element properties
- Live view shows captured elements in real-time
- Download the recorded data as a Vertical CSV

**Page 2: Generate & Validate** (`pages/2_Generate_Validate.py`)
- Upload the recorded Vertical CSV
- The tool classifies each field (text input, click, boolean, file upload, OTP)
- Only text input fields are sent to the LLM for edge case generation
- The LLM (Groq llama-3.3-70b-versatile) generates 4 edge cases per field: empty, special characters, numeric, and long string
- The output is validated against 12 structural checks
- Download the Company Format CSV (7 header rows + edge case rows)

**Page 3: Launch Test** (`pages/3_Launch_Test.py`)
- Upload the edge case CSV for automation execution
- Jenkins integration (under development)
- Test reports (under development)

### How It Solves Each Problem

| Problem | Solution |
|---------|----------|
| XPath capture is tedious | Automated browser recording with 11-strategy XPath generation |
| Edge cases require expertise | LLM generates 4 edge cases per field automatically |
| No standard handoff format | Company Format CSV with 7 fixed header rows |
| Time pressure | Full workflow completes in minutes instead of hours |

---

## 4. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT APPLICATION                      │
│                                                               │
│  ┌──────────────┐  ┌───────────────────┐  ┌──────────────┐  │
│  │   Page 1:     │  │    Page 2:         │  │  Page 3:     │  │
│  │   Record      │  │    Generate &      │  │  Launch Test │  │
│  │   (app.py)    │  │    Validate        │  │  (Placeholder│  │
│  │               │  │    (2_Gen_Val.py)   │  │              │  │
│  └──────┬───────┘  └────────┬──────────┘  └──────────────┘  │
│         │                    │                                │
│         │ subprocess         │ import                         │
│         ▼                    ▼                                │
│  ┌──────────────┐  ┌───────────────────┐                    │
│  │ recorder.py  │  │   validator.py     │                    │
│  │ (Playwright)  │  │   (12 checks)     │                    │
│  └──────────────┘  └───────────────────┘                    │
│                              │                                │
│                              │ API call                       │
│                              ▼                                │
│                    ┌───────────────────┐                      │
│                    │  Groq Cloud API   │                      │
│                    │  llama-3.3-70b    │                      │
│                    └───────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### How Components Connect

There are two patterns for how `app.py` calls other modules:

**Pattern 1: Subprocess (recorder.py)**
```python
# app.py spawns recorder.py as a separate process
subprocess.Popen(['python', 'src/recorder.py', url, formats, output_dir, capture_file])

# To stop recording, app.py sends SIGTERM
process.terminate()
```

Why subprocess? Because Playwright runs a persistent browser session that blocks execution. Running it in a separate process lets Streamlit stay responsive.

**Pattern 2: Import (validator.py)**
```python
# Page 2 imports validator directly
from validator import validate_edge_case_csv, ValidationResult

result = validate_edge_case_csv(dataframe)
```

Why import? Because validation is a quick, non-blocking operation that returns immediately.

### Inter-Process Communication

```
app.py ◄──── .live_capture.jsonl ────► recorder.py
  │                                        │
  │  reads JSONL every 2 seconds           │  writes JSONL on every
  │  to update Live View                   │  browser interaction
  │                                        │
  └────── SIGTERM signal ──────────────────┘
          (to stop recording)
```

The `.live_capture.jsonl` file is the communication channel between app.py and recorder.py. Each line is a JSON object representing one captured event:

```json
{"type": "xpath", "label": "firstName", "action": "click", "xpath": "//...", "timestamp": "..."}
{"type": "group", "name": "Personal Info", "timestamp": "..."}
{"type": "cleared", "timestamp": "...", "message": "Data cleared"}
```

---

## 5. Data Flow

### End-to-End Pipeline

```
Step 1: RECORD
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  User enters  │ ──► │  Chromium     │ ──► │ .live_capture    │
│  URL in       │     │  browser      │     │ .jsonl           │
│  Streamlit    │     │  opens        │     │ (real-time data) │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                    │
Step 2: DOWNLOAD                                    ▼
┌──────────────────┐     ┌──────────────────────────────┐
│  User downloads   │ ◄── │  Live View shows captured     │
│  Vertical CSV     │     │  elements as they appear      │
└────────┬─────────┘     └──────────────────────────────┘
         │
Step 3: UPLOAD TO GENERATOR
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Upload Vertical  │ ──► │  Field classifier │
│  CSV to Page 2    │     │  sorts fields     │
└──────────────────┘     └────────┬─────────┘
                                  │
Step 4: LLM GENERATION            ▼
┌──────────────────┐     ┌──────────────────┐
│  Groq API call    │ ◄── │  Build prompt     │
│  (llama-3.3-70b)  │     │  for text inputs  │
└────────┬─────────┘     └──────────────────┘
         │
Step 5: BUILD OUTPUT              ▼
┌──────────────────┐     ┌──────────────────┐
│  Company Format   │ ◄── │  Parse LLM        │
│  CSV (7 headers   │     │  response +       │
│  + edge cases)    │     │  build rows        │
└────────┬─────────┘     └──────────────────┘
         │
Step 6: VALIDATE                  ▼
┌──────────────────┐     ┌──────────────────┐
│  12-check         │ ──► │  Pass/Fail/Warn   │
│  validation       │     │  report            │
└────────┬─────────┘     └──────────────────┘
         │
Step 7: HANDOFF                   ▼
┌──────────────────┐     ┌──────────────────┐
│  Download CSV     │ ──► │  Automation       │
│  for QA team      │     │  scripts consume  │
└──────────────────┘     └──────────────────┘
```

### CSV Format Transformation

**Input (Vertical CSV from recorder):**
```
Step | Group        | Element    | Property | Action | XPath  | Value
1    | PersonalInfo | firstName  | text     | click  | //...  |
2    | PersonalInfo | firstName  | text     | input  | //...  | JOHN
3    | PersonalInfo | email      | email    | click  | //...  |
4    | PersonalInfo | email      | email    | input  | //...  | test@email.com
```

**Output (Horizontal Company Format CSV):**
```
Steps            | 1        | 2        | 3             | 4
Group            | Personal | Personal | Personal      | Personal
Elements         | firstName| firstName| email         | email
Property         | text     | text     | email         | email
Action           | click    | input    | click         | input
XPath            | //...    | //...    | //...         | //...
Perfect_Template | Click    | JOHN     | Click         | test@email.com
Value_firstName  |          |  | @#$.. |               | test@email.com
Value_email      |          | JOHN     |               |  | special@..
```

---

## 6. Component Deep Dive

### 6.1 app.py (532 lines) - Main Dashboard

**Purpose:** Orchestrates recording, displays live captured data, and shows session history.

**Key Sections:**

| Section | Lines | What It Does |
|---------|-------|--------------|
| CSS Styling | 89-154 | Dark theme, button styles, metric cards |
| Recording Control | 164-253 | Start/Stop buttons, subprocess management |
| Live View | 256-477 | Real-time display during recording |
| Session History | 481-560 | View/download previous recording sessions |

**Key Functions:**
- `transpose_to_company_format(entries)` - Converts vertical data to horizontal format with 7 header rows
- Start Recording block - Spawns `recorder.py` via `subprocess.Popen()`
- Stop Recording block - Sends `SIGTERM` to recorder process
- Live View - Reads `.live_capture.jsonl` every 2 seconds, processes group markers, displays data

**Session State:**
```python
st.session_state.recording  # True/False - is recording active?
st.session_state.process    # subprocess.Popen object (or None)
st.session_state.last_json  # Path to last saved JSON file
```

**Group Assignment Logic:**
Groups are assigned retroactively. When the user clicks "Assign Page", a group marker is written to the JSONL file. All elements captured BEFORE that marker inherit the group name.

---

### 6.2 recorder.py (397 lines) - Browser Automation

**Purpose:** Captures XPaths and user interactions from a live browser session.

**How It Works:**

1. Playwright launches a Chromium browser and navigates to the target URL
2. A large block of JavaScript is injected into the page
3. The JavaScript adds event listeners for `click` and `change` events on ALL elements
4. When the user interacts with an element, JavaScript extracts:
   - Element tag, type, id, name, classes, text content
   - Input value (for change events)
   - Element properties (inputmode, pattern, maxLength, required)
5. JavaScript calls `window.recordAction()` which bridges to Python via `page.expose_function()`
6. Python receives the data and generates an optimized XPath using 11 strategies
7. Each capture is appended to `.live_capture.jsonl`

**Signal Handling:**
```python
signal.signal(signal.SIGTERM, cleanup)  # From app.py terminate()
signal.signal(signal.SIGINT, cleanup)   # From Ctrl+C
```

When either signal is received, `cleanup()` saves all captured data to JSON/CSV files and closes the browser.

**JavaScript Injection Highlights:**
- Hover highlighting: Red border + semi-transparent red overlay
- Click interception: `event.preventDefault()` + `event.stopPropagation()` to capture without navigating
- Change detection: Captures the new value after user types in a field
- Property extraction: Reads HTML attributes (type, inputmode, pattern, maxLength, required)

---

### 6.3 validator.py (329 lines) - CSV Validation

**Purpose:** Validates that a generated edge case CSV conforms to the Company Format specification.

**ValidationResult Class:**
```python
class ValidationResult:
    passed: list   # Checks that passed
    failed: list   # Blocking issues (CSV is invalid)
    warnings: list # Non-blocking issues (CSV works but has concerns)

    @property
    def is_valid(self) -> bool:
        return len(self.failed) == 0

    @property
    def summary(self) -> dict:
        return {"valid": self.is_valid, "passed": N, "failed": N, "warnings": N}
```

**All 12 checks are detailed in [Section 10](#10-validation-rules).**

**Can be run as CLI tool:**
```bash
python src/validator.py path/to/edge_case.csv
```

---

### 6.4 llm_generator.py (463 lines) - Standalone Generator

**Purpose:** Backup/reference implementation of the LLM edge case generator. The same logic exists in `2_Generate_Validate.py` for the integrated workflow.

**Key difference from Page 2:** This file can run independently as its own Streamlit app (`streamlit run src/llm_generator.py`). It was the original implementation before being integrated into the main app.

---

### 6.5 2_Generate_Validate.py (480 lines) - Generation Page

**Purpose:** Upload recorded CSV, generate edge cases via LLM, validate output, download results.

**Contains two sub-tabs:**
- **Generate Tab:** Upload CSV, analyze fields, call LLM, build output, auto-validate
- **Validate Tab:** Upload any CSV and run the 12-check validation independently

**Key functions are detailed in [Section 8](#8-edge-case-generation).**

---

### 6.6 3_Launch_Test.py (165 lines) - Automation Page

**Purpose:** Placeholder for future Jenkins CI/CD integration.

**Current status:** All interactive elements (Jenkins URL, pipeline selector, schedule button) are disabled. Three sections exist as UI scaffolding:
1. Upload Test Data
2. Schedule Test Run (disabled)
3. Test Reports (placeholder)

---

## 7. XPath Strategy Priority

The recorder generates the most reliable XPath possible for each element. It tries 11 strategies in order, stopping at the first one that produces a unique match (exactly 1 element on the page).

| Priority | Strategy | Example XPath | Reliability |
|----------|----------|---------------|-------------|
| 1 | `id` | `//*[@id="firstName"]` | Highest - IDs should be unique |
| 2 | `name` | `//input[@name="email"]` | High - usually unique per form |
| 3 | `data-testid` | `//*[@data-testid="submit-btn"]` | High - made for testing |
| 4 | `data-testid + text` | `//*[@data-testid="x" and contains(text(),"Submit")]` | High - combined |
| 5 | `aria-label` | `//*[@aria-label="First Name"]` | Medium - accessibility attribute |
| 6 | `role` | `//*[@role="button"]` | Medium - may match multiple |
| 7 | `role + text` | `//*[@role="button" and contains(text(),"Submit")]` | Medium-High |
| 8 | `placeholder` | `//input[@placeholder="Enter name"]` | Medium |
| 9 | `type` | `//input[@type="email"]` | Low - often not unique |
| 10 | `href` | `//a[@href="/login"]` | Medium - for links only |
| 11 | `class` | `//*[contains(@class,"form-input")]` | Low - utility classes skipped |
| 12 | `text` | `//*[contains(text(),"Submit")]` | Low - text may change |
| 13 | `absolute` | `/html/body/div[2]/form/input[3]` | Lowest - breaks on any DOM change |

**Why this order matters:**
- ID-based XPaths almost never break when the page changes
- Absolute XPaths break whenever any element is added/removed/moved
- The recorder validates each strategy by counting matches - if it matches more than 1 element, it tries the next strategy

---

## 8. Edge Case Generation

### Field Classification

Before generating edge cases, every field is classified:

```python
def classify_field(field_name, action, value) -> str:
    # Priority order:
    # 1. Action is click → 'click' (no testing needed)
    # 2. Value is true/false → 'boolean' (no testing needed)
    # 3. Field name contains 'otp' → 'otp' (no testing needed)
    # 4. Value contains file paths → 'file_upload' (no testing needed)
    # 5. Everything else → 'text_input' (GETS EDGE CASES)
```

Only `text_input` fields receive LLM-generated edge cases. The other types are skipped because:
- **click**: No input value to test
- **boolean**: Only true/false (not text-based)
- **otp**: Generated separately, not typed by users
- **file_upload**: File paths, not user-typed text

### LLM Prompt Structure

The prompt sent to Groq follows a strict format:

```
You are a QA test data expert. Generate edge case test values...

## INPUT: Text Input Fields That Need Testing
  - Field: 'firstName' | Group: 'PersonalInfo' | Valid Value: 'JOHN'
  - Field: 'lastName' | Group: 'PersonalInfo' | Valid Value: 'DOE'

## EDGE CASE TYPES (in this exact order)
1. empty: Empty string (leave blank)
2. special: Special characters (@#$%^&*<>)
3. numeric: Numbers only (12345)
4. long: Excessively long string (50+ characters)

## OUTPUT FORMAT
FIELD_NAME|||DESCRIPTION|||EDGE_CASE_VALUES

Example:
firstName|||Tests firstName validation...|||  | @#$%^&*<> | 12345 | AAAA...
```

**Why this format?**
- Triple pipes (`|||`) are used as delimiters because single pipes (`|`) are used within edge case values
- The strict format makes parsing reliable
- Temperature 0.3 ensures consistent output across runs
- Max tokens 4000 is sufficient for ~50 fields

### The 4 Edge Case Types

| Type | Purpose | Example Value |
|------|---------|---------------|
| empty | Tests required field validation | ` ` (blank) |
| special | Tests character sanitization | `@#$%^&*<>` |
| numeric | Tests numeric-only rejection in text fields | `12345` |
| long | Tests max length enforcement | `AAAAAAAAAA...` (50+ chars) |

### How Edge Case Rows Are Built

For each text input field, one row is generated:

```
Row name: Value_fieldName
Target field: pipe-separated edge values ( | @#$%^& | 12345 | AAAA...)
Other text fields: keep their original valid values
Click fields: empty string ''
```

This means each edge case row tests ONE field at a time while keeping all other fields valid. This isolates which field causes a failure.

---

## 9. CSV Format Specification

### Company Format Structure

The output CSV has exactly 7 header rows followed by edge case rows:

```
Row 0: Steps            | 1        | 2        | 3        | ...
Row 1: Group            | Section1 | Section1 | Section2 | ...
Row 2: Elements         | firstName| lastName | email    | ...
Row 3: Property         | text     | text     | email    | ...
Row 4: Action           | click    | input    | input    | ...
Row 5: XPath            | //...    | //...    | //...    | ...
Row 6: Perfect_Template | Click    | JOHN     | test@... | ...
Row 7: Value_firstName  |          | val|val  | test@... | ...  (edge case)
Row 8: Value_email      |          | JOHN     | val|val  | ...  (edge case)
...
```

### Row-by-Row Breakdown

| Row | Label | Content | Purpose |
|-----|-------|---------|---------|
| 0 | Steps | Sequential numbers: 1, 2, 3... | Identifies column position |
| 1 | Group | Section names from recording | Groups related fields |
| 2 | Elements | Field names/labels | Human-readable identifier |
| 3 | Property | HTML input types (text, email, select) | Field type information |
| 4 | Action | `click` or `input` | What the automation script should do |
| 5 | XPath | Element locator paths | How automation finds the element |
| 6 | Perfect_Template | All valid values (golden path) | The "happy path" test data |
| 7+ | Value_fieldName | Edge case values (pipe-separated) | Boundary/invalid test data |

### Edge Case Row Format

Each edge case row contains pipe-separated values for exactly ONE field:

```
Value_firstName |  | JOHN | test@email.com
                  ^-- empty | @#$%^& | 12345 | AAAA... (4 edge cases)
```

**Click column handling:**
- Columns where Action (row 4) = `click` are left as empty strings `''`
- Automation scripts check the Action row to know these are clicks, not inputs
- The empty string means "skip input, just click"

**Row naming convention:**
- Each edge case row starts with `Value_` followed by the field name
- Example: `Value_firstName`, `Value_email`, `Value_phoneNumber`
- This allows automation scripts to identify which field is being tested

---

## 10. Validation Rules

The validator runs 12 checks on any Company Format CSV. Checks are categorized as FAIL (blocks usage) or WARN (flags concerns but CSV is still usable).

| # | Check Name | Type | Condition | Why It Matters |
|---|------------|------|-----------|----------------|
| 1 | Minimum Rows | FAIL | Must have at least 8 rows (7 header + 1 edge case) | Without edge cases, there's nothing to test |
| 2 | Column Consistency | WARN | Each row should have at least 50% of columns filled | Rows with mostly empty cells may indicate parsing errors |
| 3 | Header Row Labels | FAIL | First column values must be: Steps, Group, Elements, Property, Action, XPath, Perfect_Template | Automation scripts rely on these exact row positions |
| 4 | Action Row Values | WARN | Row 4 should only contain: click, input, or change | Unknown actions will confuse automation scripts |
| 5 | XPath Row Format | WARN | Row 5 XPaths must start with `//` or `/html` | Invalid XPaths will fail element lookup |
| 6 | Perfect Template Completeness | WARN | Row 6 should have less than 30% empty values | Too many empty values means the golden path is incomplete |
| 7 | Edge Case Rows Exist | FAIL | Must have at least 1 row after row 6 | No edge cases means no test data was generated |
| 8 | Pipe-Separated Values | FAIL | Every edge case row must contain at least one pipe (`\|`) character | Edge cases must be pipe-separated per the format spec |
| 9 | Single Edge Case Per Row | WARN | Each row should test only 1 field (only 1 cell with pipes) | Testing multiple fields in one row makes failures ambiguous |
| 10 | Edge Case Count | WARN | Each pipe-separated value should have exactly 4 parts | We expect 4 edge case types: empty, special, numeric, long |
| 11 | Click Values Preserved | FAIL | Click columns must be empty or "Click" in edge case rows | Putting test values in click columns will cause automation errors |
| 12 | Row Names | WARN | Edge rows should follow `Value_fieldName` pattern | Consistent naming helps automation scripts identify test targets |

### Validation Output

```python
result = validate_edge_case_csv(df)

# Access results
result.is_valid    # True if no FAIL checks triggered
result.passed      # [{"check": "...", "details": "..."}]
result.failed      # [{"check": "...", "details": "..."}]
result.warnings    # [{"check": "...", "details": "..."}]
result.summary     # {"valid": True, "passed": 10, "failed": 0, "warnings": 2}
```

---

## 11. Integration Architecture

### How This Tool Fits Into the QA Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    THIS TOOL (Your Code)                     │
│  Record XPaths → Generate Edge Cases → Validate → Export CSV │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  CSV File (The Contract)
                  7 header rows + edge case rows
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              AUTOMATION SCRIPTS (Senior Dev's Code)          │
│  Read CSV → Parse XPaths → Execute Browser Tests → Report    │
└─────────────────────────────────────────────────────────────┘
```

The CSV file is the integration point. Your tool produces it; automation scripts consume it. As long as both sides agree on the format (7 header rows, specific labels, pipe-separated edge cases), the systems work together without needing to share code.

### Integration Patterns

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
├── automation/          ← Senior dev's scripts
└── .github/workflows/   ← CI/CD pipelines
```

### What Automation Scripts Do With the CSV

```python
# Senior dev's runner.py (simplified)
import pandas as pd
from selenium import webdriver

df = pd.read_csv("edge_cases.csv", header=None)

# Extract from header rows
xpaths  = df.iloc[5, 1:].tolist()    # Row 5 = XPaths
actions = df.iloc[4, 1:].tolist()    # Row 4 = Actions

# Iterate over edge case rows
for test_row_idx in range(7, len(df)):
    test_values = df.iloc[test_row_idx, 1:].tolist()

    for i, (xpath, action, value) in enumerate(zip(xpaths, actions, test_values)):
        element = driver.find_element("xpath", xpath)

        if action == 'click':
            element.click()
        else:
            if '|' in str(value):
                for edge_val in value.split('|'):
                    element.clear()
                    element.send_keys(edge_val.strip())
                    # Assert/validate form behavior...
            else:
                element.send_keys(str(value))
```

### Responsibility Split

| Your Tool (This Codebase) | Automation Scripts (Senior Dev) |
|---------------------------|--------------------------------|
| Record XPaths from browser | Read and parse the CSV |
| Generate edge case test data | Navigate to the target URL |
| Validate CSV structure | Execute browser actions (click/type) |
| Export Company Format CSV | Handle assertions and validation |
| Ensure 7 header rows are correct | Report results to Jenkins/CI |

---

## 12. Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.13+ | Core language |
| **Streamlit** | >= 1.32.0 | Web UI framework (multi-page app) |
| **Playwright** | >= 1.48.0 | Browser automation (Chromium) |
| **Groq Cloud API** | - | LLM inference provider |
| **llama-3.3-70b-versatile** | - | LLM model for edge case generation |
| **Pandas** | >= 2.0.0 | DataFrame manipulation and CSV handling |
| **python-dotenv** | >= 1.0.0 | Environment variable management |

### Why These Choices

- **Streamlit** over Flask/Django: Fastest way to build data-oriented UIs in Python. Multi-page support out of the box. No frontend code needed.
- **Playwright** over Selenium: Modern API, auto-wait for elements, better performance, native TypeScript/JavaScript bridge.
- **Groq** over OpenAI: Free tier with sufficient limits for demo. Fast inference (70B model responds in seconds). No cost concerns.
- **llama-3.3-70b-versatile**: Strong instruction-following for structured output. Free on Groq. Temperature 0.3 gives consistent results.

---

## 13. Environment Setup & Running

### Prerequisites

- Python 3.10+ (tested on 3.13)
- pip (Python package manager)
- Groq API key (free at https://console.groq.com)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd xpath_streamlit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install streamlit pandas playwright groq python-dotenv
playwright install chromium
```

### API Key Setup

Create the file `version4.1/config/.env`:
```
GROQ_API_KEY=your-groq-api-key-here
```

Or set as environment variable:
```bash
export GROQ_API_KEY="your-groq-api-key-here"
```

### Running the Application

```bash
cd version4.1
streamlit run app.py
```

The app opens at `http://localhost:8501` with three pages in the sidebar:
1. XPath Analytics Recorder
2. Generate & Validate
3. Launch Test

### Quick Test

1. Enter `https://demoqa.com/automation-practice-form` as the URL
2. Click Start Recording
3. Fill out a few fields in the browser
4. Click Stop Recording
5. Download the Vertical CSV
6. Go to Page 2, upload the CSV
7. Click Generate Edge Case Test Data
8. Review the output and download

---

## 14. Directory Structure

```
version4.1/
├── app.py                          (532 lines)  Main dashboard - recording & live view
├── requirements.txt                              Python dependencies
├── README.md                                     Quick start guide
├── PROJECT_MANUAL.md                             This document
├── .gitignore                                    Excludes .env, venv/, __pycache__
│
├── config/
│   └── .env                                      Groq API key (not in git)
│
├── src/
│   ├── __init__.py                               Package initializer
│   ├── recorder.py                 (397 lines)  Playwright browser automation
│   ├── validator.py                (329 lines)  CSV validation (12 checks)
│   ├── llm_generator.py            (463 lines)  Standalone LLM generator (backup)
│   └── csv_validator.py            (199 lines)  Alternative validator (backup)
│
├── pages/
│   ├── 2_Generate_Validate.py      (480 lines)  Page 2 - Generate & Validate
│   └── 3_Launch_Test.py            (165 lines)  Page 3 - Launch Test (placeholder)
│
├── data/
│   ├── captures/                                 Recording output files
│   │   ├── .live_capture.jsonl                   Real-time capture (runtime only)
│   │   ├── .recording_state.json                 Recording status (runtime only)
│   │   └── xpaths_*.csv / .json                  Saved sessions
│   └── samples/                                  Reference test data (13 CSVs)
│       ├── test1-7.csv                           Small test cases
│       └── End_to_end_*.csv                      Full workflow test data
│
└── notebooks/
    └── test_4.1.ipynb                            Jupyter notebook for analysis
```

### Total Codebase Size

| Category | Files | Lines |
|----------|-------|-------|
| Main app | 1 | 532 |
| Pages | 2 | 645 |
| Source modules | 4 | 1,388 |
| **Total Python** | **7** | **2,565** |

---

## 15. Known Limitations & Future Work

### Current Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Checkboxes use absolute XPaths | Fragile, break on DOM changes | Manual XPath correction after recording |
| Some elements captured as "div" or "svg" | Not descriptive labels | Review and rename in CSV |
| Multi-section forms recorded in one session | Large CSVs with many columns | Use "Assign Page" to group, or record sections separately |
| LLM occasionally produces malformed output | Missing edge cases for some fields | Fallback values are used (empty, @#$%^&, 12345, AAA...) |
| No automated test execution | Manual handoff to automation team | Page 3 placeholder for Jenkins |

### Planned Future Work

| Feature | Priority | Status |
|---------|----------|--------|
| Jenkins CI/CD integration | High | Page 3 placeholder built |
| Browser automation runner | High | Planned |
| Dropdown/checkbox combination testing | Medium | Planned |
| CSV auto-splitter for multi-section forms | Medium | Planned |
| Better checkbox XPath strategies | Medium | Planned |
| Test result reporting | Medium | Planned |
| Coordinate capture (x,y fallback) | Low | Researched |
| Label direction detection | Low | Researched |

---

## Appendix: Quick Reference

### Commands
```bash
# Run the app
cd version4.1 && streamlit run app.py

# Validate a CSV from command line
python version4.1/src/validator.py path/to/file.csv

# Run standalone generator (backup)
cd version4.1 && streamlit run src/llm_generator.py
```

### LLM Configuration
- **Provider:** Groq Cloud
- **Model:** llama-3.3-70b-versatile
- **Temperature:** 0.3
- **Max Tokens:** 4000
- **Tier:** Free
- **Spend:** ~$0.03 USD total

### Key Terms
| Term | Definition |
|------|------------|
| Company Format | Horizontal CSV with 7 header rows + edge case rows |
| Edge Case | Boundary/invalid input (empty, special, numeric, long) |
| Perfect Template | Row 6 - all valid values (golden path) |
| Pipe-separated | Edge case format: `val1 \| val2 \| val3 \| val4` |
| XPath | XML Path - locator to find elements on a webpage |
| Vertical Format | Standard row-per-action format (input to generator) |
| JSONL | JSON Lines - one JSON object per line (inter-process communication) |

---

*Built by QA Automation Team - Impacto Digital*
*Version 4.1 - February 2026*
