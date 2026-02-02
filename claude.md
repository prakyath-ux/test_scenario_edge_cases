# Automatic XPath - Project Documentation

## Project Goal
Build an automated QA testing tool that:
1. Captures XPaths and user input values from web forms via browser recording
2. Generates test case data (edge cases) for QA automation testing
3. Outputs in company format for integration with existing QA workflows

---

## PROJECT STATUS: POC DELIVERED - STARTING PHASE 2 (Jan 30, 2026)

### Phase 1 (COMPLETE - POC Delivered Jan 28, 2026)
| Component | Status |
|-----------|--------|
| XPath Recorder (version4_QA) | ✅ COMPLETE |
| Test Scenario Generator (test_case_generation) | ✅ COMPLETE |
| CSV Validator | ✅ COMPLETE |
| Data Visualization (transpose) | ✅ COMPLETE |

### Phase 2 (IN PROGRESS)
| Component | Status |
|-----------|--------|
| Multi-section form handling | PENDING |
| Dropdown/Checkbox combination testing | PENDING |
| CSV auto-splitter | PENDING |
| Browser automation runner | PENDING |

---

# SECTION 1: XPath Recorder

## Location: `/version4_QA/`

## Files:

| File | Purpose |
|------|---------|
| `app_v4.py` | Streamlit UI - URL input, Start/Stop buttons, format selection |
| `recorder.py` | Playwright browser automation - captures XPaths via JavaScript |
| `test.ipynb` | Data visualization - transpose recorded data to company format |
| `a.txt` | Backup/reference of recorder.py code |
| `xpath_data_retrieved/` | Folder with older captured data |
| `xpaths_*.csv` | Captured XPath data files |
| `xpaths_*.json` | Captured XPath data (JSON format) |

## How to Run XPath Recorder:

```bash
cd version4_QA
streamlit run app_v4.py
```

1. Enter URL in the text box
2. Select output format (CSV, JSON, or Python)
3. Click "Start Recording"
4. Chromium browser opens - interact with the form (click fields, type values)
5. Click "Stop Recording" in Streamlit
6. CSV/JSON files saved in current directory

## Output CSV Format:

```csv
Label,XPath,Strategy,Matches,Action,Value
firstName,//*[@id="firstName"],id,1,click,
firstName,//*[@id="firstName"],id,1,change,PRAKYATH
email,//*[@id="email"],id,1,click,
email,//*[@id="email"],id,1,change,PRAK@GMAIL.COM
```

| Column | Description |
|--------|-------------|
| Label | Element identifier (id, name, or text) |
| XPath | The XPath locator for the element |
| Strategy | How XPath was generated (id, name, data-testid, class, text, absolute) |
| Matches | Number of elements matching this XPath (1 = unique) |
| Action | click or change |
| Value | User input value (empty for clicks) |

## XPath Strategy Priority (in recorder.py):

1. `id` - Most reliable
2. `name` - Second best
3. `data-testid` - Good for modern apps
4. `aria-label` - Accessibility attribute
5. `role` - ARIA role
6. `placeholder` - Input placeholder
7. `type` - Input type
8. `href` - For links
9. `class` - CSS class
10. `text` - Element text content
11. `absolute` - Last resort (fragile!)

## Key Technical Concepts:

```python
subprocess.Popen()           # Run recorder.py as background process
signal.signal(SIGTERM, cleanup)  # Handle stop signal from Streamlit
page.wait_for_timeout(500)   # Keep Playwright event loop running
page.expose_function()       # Bridge between JavaScript and Python
```

---

## How to Visualize Data (test.ipynb):

Open `version4_QA/test.ipynb` in Jupyter/VS Code and run cells.

### What it does:
1. Loads recorded CSV
2. Cleans data (replaces NaN with 'Click' for click actions)
3. Replaces 'change' with 'input' for readability
4. Transposes to company format:

**Before (vertical):**
```
Label      | Action | Value
firstName  | click  |
firstName  | change | PRAKYATH
```

**After (horizontal - company format):**
```
Description | firstName | firstName | email | email | ...
Action      | click     | input     | click | input | ...
Test Case 1 | Click     | PRAKYATH  | Click | test@ | ...
```

### Code to transpose:

```python
import pandas as pd

# Load data
df = pd.read_csv("xpaths_XXXXXX.csv")

# Clean
df_clean = df[['Label', 'Action', 'Value']].copy()
df_clean['Action'] = df_clean['Action'].replace('change', 'input')
df_clean['Value'] = df_clean.apply(
    lambda row: 'Click' if row['Action'] == 'click' else row['Value'],
    axis=1
)

# Transpose
labels = df_clean['Label'].tolist()
actions = df_clean['Action'].tolist()
values = df_clean['Value'].tolist()

rows = [
    ['Description'] + labels,
    ['Action'] + actions,
    ['Perfect template (all valid)'] + values
]

result = pd.DataFrame(rows)

# Show all columns
pd.set_option('display.max_columns', None)
result
```

---

# SECTION 2: Test Scenario Generator

## Location: `/test_case_generation/`

## Files:

| File | Purpose |
|------|---------|
| `llm_generator.py` | Streamlit app - generates edge case test scenarios using LLM |
| `csv_validator.py` | Streamlit app - validates generated CSV structure |
| `test2.ipynb` | Manual scenario generator (non-LLM approach) |
| `.env` | Contains GROQ_API_KEY |
| `test_scenarios*.csv` | Generated test scenario files |
| `a.txt` | Reference/backup code |

## How to Run LLM Generator:

```bash
cd test_case_generation

# Set API key (or use .env file)
export GROQ_API_KEY="your-groq-api-key"

streamlit run llm_generator.py
```

1. Upload a CSV file (from XPath recorder)
2. Click "Generate Test Scenarios"
3. LLM generates edge cases for each input field
4. Download the generated CSV

## How to Run CSV Validator:

```bash
cd test_case_generation
streamlit run csv_validator.py
```

1. Upload the generated test scenarios CSV
2. Click "Validate CSV"
3. See validation results (pass/fail for each check)

## What LLM Generator Does:

**Input:** Recorded XPath CSV
```csv
Label,XPath,Strategy,Matches,Action,Value
firstName,//*[@id="firstName"],id,1,click,
firstName,//*[@id="firstName"],id,1,change,PRAKYATH
```

**Output:** Test scenarios CSV with edge cases
```csv
Description,firstName,firstName,email,email,...
Perfect template,Click,PRAKYATH,Click,test@email.com,...
firstName - empty,Click,,Click,test@email.com,...
firstName - special,Click,@#$%^&,Click,test@email.com,...
firstName - numeric,Click,12345,Click,test@email.com,...
firstName - long,Click,AAAA...(50 chars),Click,test@email.com,...
email - empty,Click,PRAKYATH,Click,,...
...
```

## Edge Cases Generated:

| Edge Case | Test Value |
|-----------|------------|
| empty | (blank) |
| special | @#$%^& |
| numeric | 12345 |
| long | 50 'A' characters |

## Validation Checks (csv_validator.py):

| Check | What it validates |
|-------|-------------------|
| Column count | Every row has same columns as header |
| Click preservation | "Click" values never modified |
| One change per row | Each test case modifies exactly 1 field |
| Edge cases present | empty, special, numeric, long exist |
| Perfect row complete | No unexpected empty values |

## Key Code in llm_generator.py:

1. **Dynamic column detection** - Counts columns from input CSV
2. **Dynamic input field detection** - Finds fields with 'change' action
3. **Post-processing validation** - Fixes LLM output if column count is wrong

```python
# Post-processing to fix column count
lines = result_text.split('\n')
header_cols = len(lines[0].split(','))

for line in lines[1:]:
    cols = line.split(',')
    if len(cols) < header_cols:
        cols.extend(['Click'] * (header_cols - len(cols)))  # Add missing
    elif len(cols) > header_cols:
        cols = cols[:header_cols]  # Trim extra
```

---

# SECTION 3: Complete Workflow

## End-to-End Process:

```
1. RECORD
   └── Run: streamlit run version4_QA/app_v4.py
   └── Enter URL, record form interactions
   └── Output: xpaths_XXXXXX.csv

2. GENERATE TEST SCENARIOS
   └── Run: streamlit run test_case_generation/llm_generator.py
   └── Upload recorded CSV
   └── Output: test_scenarios.csv (edge cases)

3. VALIDATE
   └── Run: streamlit run test_case_generation/csv_validator.py
   └── Upload generated CSV
   └── Confirm all checks pass

4. VISUALIZE (Optional)
   └── Open: version4_QA/test.ipynb
   └── Load CSV, run transpose code
   └── View in company format
```

---

# SECTION 4: Testing Notes

## Tested Scenarios:

| Test | Input Columns | Result |
|------|---------------|--------|
| Test 1 | 13 columns | PASS |
| Test 2 | 19 columns | PASS |
| Test 3 | 14 columns | PASS |
| Multi-section (Section 1-4) | 111 rows | PASS |

## Known Limitations:

1. **Checkboxes use absolute XPaths** - Fragile, may break if page structure changes
2. **Some elements captured as "div" or "svg"** - Not descriptive labels
3. **Multi-section forms** - All sections recorded in one CSV (can be split manually)

---

# SECTION 5: Future Enhancements (Post-Freeze)

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| Coordinate capture | Capture x,y position as fallback | Low |
| Label direction detection | Detect if label is left/above input | Low |
| CSV splitter | Auto-split multi-section recordings | Medium |
| Combination testing | Test different dropdown/checkbox combinations | Medium |
| Browser automation runner | Run test scenarios against live form | High |
| Better checkbox XPaths | Improve XPath strategy for checkboxes | Medium |

## Coordinate Notes (for future reference):

```javascript
// Get element coordinates
element.getBoundingClientRect()
// Returns: { x, y, width, height, top, left, right, bottom }
```

**Why coordinates are fragile:**
- Change with screen size
- Change with browser resize
- Change with zoom level
- Change with dynamic content

---

# SECTION 6: Dependencies

```
playwright>=1.48.0
streamlit>=1.32.0
pandas
numpy
groq
python-dotenv
```

## Install:

```bash
pip install playwright streamlit pandas numpy groq python-dotenv
playwright install chromium
```

---

# SECTION 7: Environment Setup

## Required Environment Variables:

```bash
# For LLM Generator
export GROQ_API_KEY="your-groq-api-key"
```

Or create `.env` file in `test_case_generation/`:
```
GROQ_API_KEY=your-groq-api-key
```

---

# SECTION 8: Quick Reference

## Commands:

```bash
# XPath Recorder
cd version4_QA && streamlit run app_v4.py

# Test Scenario Generator
cd test_case_generation && streamlit run llm_generator.py

# CSV Validator
cd test_case_generation && streamlit run csv_validator.py
```

## Important Files to Check:

| Purpose | File |
|---------|------|
| Record XPaths | `version4_QA/app_v4.py` |
| Browser automation | `version4_QA/recorder.py` |
| Visualize data | `version4_QA/test.ipynb` |
| Generate test scenarios | `test_case_generation/llm_generator.py` |
| Validate CSV | `test_case_generation/csv_validator.py` |
| Manual scenario logic | `test_case_generation/test2.ipynb` |

---

# SECTION 9: Terminology

| Term | Definition |
|------|------------|
| Test Case | 1 value change for 1 element (e.g., "firstName - empty") |
| Test Scenario | Multiple value changes for 1 element (all firstName edge cases) |
| Test Suite | All tests for all elements in one section/page |
| Edge Case | Boundary/invalid input (empty, special chars, too long, etc.) |
| XPath | XML Path - locator to find elements on webpage |
| Strategy | Method used to generate XPath (id, name, class, etc.) |

---

**Last Updated:** January 30, 2026
**Status:** POC DELIVERED - PHASE 2 IN PROGRESS
