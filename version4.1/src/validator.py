# validator.py - Edge Case Test Data Validator (v4.1)
# Validates generated test data CSV for structure and content integrity

import pandas as pd
import re
from typing import Tuple, List, Dict


class ValidationResult:
    """Container for validation results"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, check_name: str, details: str = ""):
        self.passed.append({"check": check_name, "details": details})

    def add_fail(self, check_name: str, details: str):
        self.failed.append({"check": check_name, "details": details})

    def add_warning(self, check_name: str, details: str):
        self.warnings.append({"check": check_name, "details": details})

    @property
    def is_valid(self) -> bool:
        return len(self.failed) == 0

    @property
    def summary(self) -> dict:
        return {
            "valid": self.is_valid,
            "passed": len(self.passed),
            "failed": len(self.failed),
            "warnings": len(self.warnings)
        }


def validate_edge_case_csv(df: pd.DataFrame) -> ValidationResult:
    """
    Main validation function for edge case test data CSV.

    Expected structure:
    - Row 0: Description (element names)
    - Row 1: Action (click/input)
    - Row 2: XPath (locators)
    - Row 3: Perfect_Template (all valid values)
    - Row 4+: Edge case test rows
    """
    result = ValidationResult()

    # === CHECK 1: Minimum rows ===
    if len(df) < 5:
        result.add_fail(
            "Minimum Rows",
            f"Expected at least 5 rows (4 header + 1 test), got {len(df)}"
        )
        return result  # Can't continue validation
    result.add_pass("Minimum Rows", f"{len(df)} rows found")

    # === CHECK 2: Column consistency ===
    col_counts = df.apply(lambda row: row.notna().sum(), axis=1)
    first_row_cols = len(df.columns)

    inconsistent_rows = []
    for idx, count in enumerate(col_counts):
        # Allow for some NaN values but flag major discrepancies
        actual_values = df.iloc[idx].dropna()
        if len(actual_values) < first_row_cols * 0.5:  # Less than 50% columns filled
            inconsistent_rows.append(idx)

    if inconsistent_rows:
        result.add_warning(
            "Column Consistency",
            f"Rows with potential missing data: {inconsistent_rows[:5]}..."
        )
    else:
        result.add_pass("Column Consistency", f"All {len(df)} rows have consistent columns")

    # === CHECK 3: Header row labels ===
    first_col = df.iloc[:, 0].tolist()
    expected_headers = ["Description", "Action", "XPath", "Perfect_Template"]

    header_issues = []
    for i, expected in enumerate(expected_headers):
        actual = str(first_col[i]).strip() if i < len(first_col) else "MISSING"
        if expected.lower() not in actual.lower():
            header_issues.append(f"Row {i}: expected '{expected}', got '{actual}'")

    if header_issues:
        result.add_fail("Header Row Labels", "; ".join(header_issues))
    else:
        result.add_pass("Header Row Labels", "Description, Action, XPath, Perfect_Template found")

    # === CHECK 4: Action row values ===
    action_row = df.iloc[1, 1:].tolist()  # Skip first column (label)
    valid_actions = {'click', 'input', 'change'}
    invalid_actions = []

    for i, action in enumerate(action_row):
        action_str = str(action).strip().lower()
        if action_str and action_str not in valid_actions and not pd.isna(action):
            invalid_actions.append(f"Col {i+1}: '{action}'")

    if invalid_actions:
        result.add_warning(
            "Action Row Values",
            f"Unexpected action values: {invalid_actions[:5]}"
        )
    else:
        result.add_pass("Action Row Values", "All actions are click/input")

    # === CHECK 5: XPath row format ===
    xpath_row = df.iloc[2, 1:].tolist()
    valid_xpaths = 0
    invalid_xpaths = []

    for i, xpath in enumerate(xpath_row):
        xpath_str = str(xpath).strip()
        if pd.isna(xpath) or not xpath_str:
            continue
        if xpath_str.startswith('//') or xpath_str.startswith('/html'):
            valid_xpaths += 1
        else:
            invalid_xpaths.append(f"Col {i+1}: '{xpath_str[:30]}...'")

    if invalid_xpaths and len(invalid_xpaths) > len(xpath_row) * 0.1:
        result.add_warning(
            "XPath Row Format",
            f"Some invalid XPaths: {invalid_xpaths[:3]}"
        )
    else:
        result.add_pass("XPath Row Format", f"{valid_xpaths} valid XPaths found")

    # === CHECK 6: Perfect template row completeness ===
    perfect_row = df.iloc[3, 1:].tolist()
    empty_in_perfect = sum(1 for v in perfect_row if pd.isna(v) or str(v).strip() == '')

    if empty_in_perfect > len(perfect_row) * 0.3:  # More than 30% empty
        result.add_warning(
            "Perfect Template Completeness",
            f"{empty_in_perfect} empty values in Perfect_Template row"
        )
    else:
        result.add_pass("Perfect Template Completeness", "Template row has values")

    # === CHECK 7: Edge case rows exist ===
    edge_case_rows = df.iloc[4:]
    if len(edge_case_rows) == 0:
        result.add_fail("Edge Case Rows", "No edge case test rows found (Row 5+)")
    else:
        result.add_pass("Edge Case Rows", f"{len(edge_case_rows)} edge case rows found")

    # === CHECK 8: Pipe-separated values in edge case rows ===
    rows_with_pipes = 0
    rows_without_pipes = []

    for idx in range(4, len(df)):
        row = df.iloc[idx, 1:].tolist()  # Skip description column
        has_pipe = any('|' in str(v) for v in row if not pd.isna(v))
        if has_pipe:
            rows_with_pipes += 1
        else:
            rows_without_pipes.append(idx)

    if rows_without_pipes:
        result.add_fail(
            "Pipe-Separated Edge Cases",
            f"{len(rows_without_pipes)} rows missing pipe-separated values: {rows_without_pipes[:5]}"
        )
    else:
        result.add_pass(
            "Pipe-Separated Edge Cases",
            f"All {rows_with_pipes} edge case rows have pipe-separated values"
        )

    # === CHECK 9: One edge case field per row ===
    multi_pipe_rows = []

    for idx in range(4, len(df)):
        row = df.iloc[idx, 1:].tolist()
        pipe_count = sum(1 for v in row if not pd.isna(v) and '|' in str(v))
        if pipe_count > 1:
            multi_pipe_rows.append(f"Row {idx}: {pipe_count} fields with pipes")

    if multi_pipe_rows:
        result.add_warning(
            "Single Edge Case Per Row",
            f"Rows with multiple pipe-separated fields: {multi_pipe_rows[:3]}"
        )
    else:
        result.add_pass("Single Edge Case Per Row", "Each row tests exactly one field")

    # === CHECK 10: Edge case value count (should be 4) ===
    incorrect_edge_count = []

    for idx in range(4, len(df)):
        row = df.iloc[idx, 1:].tolist()
        for col_idx, val in enumerate(row):
            if not pd.isna(val) and '|' in str(val):
                parts = str(val).split('|')
                if len(parts) != 4:
                    incorrect_edge_count.append(f"Row {idx}, Col {col_idx+1}: {len(parts)} values")

    if incorrect_edge_count:
        result.add_warning(
            "Edge Case Count (4 expected)",
            f"Fields without exactly 4 edge cases: {incorrect_edge_count[:3]}"
        )
    else:
        result.add_pass("Edge Case Count", "All edge case fields have 4 values")

    # === CHECK 11: Click values preserved ===
    action_row = df.iloc[1, 1:].tolist()
    click_columns = [i for i, a in enumerate(action_row) if str(a).lower() == 'click']

    click_modified = []
    for idx in range(4, len(df)):
        row = df.iloc[idx, 1:].tolist()
        for col_idx in click_columns:
            if col_idx < len(row):
                val = str(row[col_idx]).strip().lower()
                if val != 'click' and not pd.isna(row[col_idx]):
                    click_modified.append(f"Row {idx}, Col {col_idx+1}")

    if click_modified:
        result.add_fail(
            "Click Values Preserved",
            f"Click columns modified in: {click_modified[:5]}"
        )
    else:
        result.add_pass("Click Values Preserved", "All click values remain 'Click'")

    # === CHECK 12: Row descriptions include field names ===
    edge_case_descriptions = df.iloc[4:, 0].tolist()
    missing_field_name = []

    # Get input field names from Description row
    input_columns = [i for i, a in enumerate(action_row) if str(a).lower() in ['input', 'change']]
    field_names = [str(df.iloc[0, i+1]).lower() for i in input_columns if i+1 < len(df.columns)]

    for idx, desc in enumerate(edge_case_descriptions):
        desc_lower = str(desc).lower()
        # Check if description contains any field name
        has_field = any(fn in desc_lower for fn in field_names if fn)
        if not has_field and desc_lower not in ['', 'nan']:
            missing_field_name.append(f"Row {idx+4}: '{desc}'")

    if missing_field_name and len(missing_field_name) > len(edge_case_descriptions) * 0.3:
        result.add_warning(
            "Row Descriptions",
            f"Some rows don't clearly indicate target field: {missing_field_name[:3]}"
        )
    else:
        result.add_pass("Row Descriptions", "Edge case rows have descriptive names")

    return result


def validate_csv_file(filepath: str) -> ValidationResult:
    """Load CSV file and validate"""
    try:
        df = pd.read_csv(filepath, header=None)
        return validate_edge_case_csv(df)
    except Exception as e:
        result = ValidationResult()
        result.add_fail("File Load", f"Could not load CSV: {str(e)}")
        return result


def print_validation_report(result: ValidationResult):
    """Print formatted validation report"""
    print("\n" + "=" * 60)
    print("EDGE CASE TEST DATA VALIDATION REPORT")
    print("=" * 60)

    # Summary
    print(f"\nSummary: {'VALID' if result.is_valid else 'INVALID'}")
    print(f"  Passed:   {len(result.passed)}")
    print(f"  Failed:   {len(result.failed)}")
    print(f"  Warnings: {len(result.warnings)}")

    # Passed checks
    if result.passed:
        print("\n" + "-" * 40)
        print("PASSED CHECKS:")
        for item in result.passed:
            print(f"  [PASS] {item['check']}")
            if item['details']:
                print(f"         {item['details']}")

    # Failed checks
    if result.failed:
        print("\n" + "-" * 40)
        print("FAILED CHECKS:")
        for item in result.failed:
            print(f"  [FAIL] {item['check']}")
            print(f"         {item['details']}")

    # Warnings
    if result.warnings:
        print("\n" + "-" * 40)
        print("WARNINGS:")
        for item in result.warnings:
            print(f"  [WARN] {item['check']}")
            print(f"         {item['details']}")

    print("\n" + "=" * 60)


# CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python validator.py <csv_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    result = validate_csv_file(filepath)
    print_validation_report(result)

    sys.exit(0 if result.is_valid else 1)
