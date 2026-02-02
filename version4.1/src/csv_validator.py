# csv_validator.py - Streamlit UI for Edge Case Test Data Validation
# Validates generated CSV structure and content integrity (v4.1 format)

import streamlit as st
import pandas as pd
from validator import validate_edge_case_csv, ValidationResult

st.set_page_config(page_title="CSV Validator", page_icon="✅", layout="wide")

# CSS Styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stMarkdown, h1, h2, h3, p { color: #ffffff !important; }
    [data-testid="metric-container"] {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
    }
    .check-row {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 6px;
        font-family: monospace;
    }
    .check-pass {
        background-color: #1a3d1a;
        border-left: 4px solid #28a745;
    }
    .check-fail {
        background-color: #3d1a1a;
        border-left: 4px solid #dc3545;
    }
    .check-warn {
        background-color: #3d3a1a;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

st.title("✅ Edge Case CSV Validator")
st.markdown("*Validate generated test data structure and content integrity*")
st.divider()


def display_validation_results(result: ValidationResult):
    """Display validation results as unified checklist"""

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if result.is_valid:
            st.success("**VALID**")
        else:
            st.error("**INVALID**")

    col2.metric("Passed", len(result.passed))
    col3.metric("Failed", len(result.failed))
    col4.metric("Warnings", len(result.warnings))

    st.divider()

    # Build unified checklist from all results
    st.subheader("Validation Checklist")

    # Combine all results with their status
    all_checks = []
    for item in result.passed:
        all_checks.append(('pass', item['check'], item['details']))
    for item in result.failed:
        all_checks.append(('fail', item['check'], item['details']))
    for item in result.warnings:
        all_checks.append(('warn', item['check'], item['details']))

    # Sort by check name for consistent ordering
    check_order = [
        "Minimum Rows",
        "Column Consistency",
        "Header Row Labels",
        "Action Row Values",
        "XPath Row Format",
        "Perfect Template Completeness",
        "Edge Case Rows",
        "Pipe-Separated Edge Cases",
        "Single Edge Case Per Row",
        "Edge Case Count",
        "Click Values Preserved",
        "Row Descriptions"
    ]

    # Create ordered list
    ordered_checks = []
    for check_name in check_order:
        for status, name, details in all_checks:
            if check_name.lower() in name.lower() or name.lower() in check_name.lower():
                ordered_checks.append((status, name, details))
                break

    # Add any checks not in the predefined order
    for status, name, details in all_checks:
        if not any(name == oc[1] for oc in ordered_checks):
            ordered_checks.append((status, name, details))

    # Display unified checklist
    for status, check_name, details in ordered_checks:
        if status == 'pass':
            icon = "✅"
            css_class = "check-pass"
        elif status == 'fail':
            icon = "❌"
            css_class = "check-fail"
        else:
            icon = "⚠️"
            css_class = "check-warn"

        # Format details (truncate if too long)
        detail_text = details if len(details) < 60 else details[:57] + "..."

        st.markdown(f"""
        <div class="check-row {css_class}">
            <strong>{icon} {check_name}</strong>
            <span style="color: #888; margin-left: 10px;">{detail_text}</span>
        </div>
        """, unsafe_allow_html=True)

    # Show detailed failures/warnings in expander if any
    if result.failed or result.warnings:
        st.divider()
        with st.expander("View Full Details", expanded=False):
            if result.failed:
                st.markdown("**Failed Checks:**")
                for item in result.failed:
                    st.error(f"**{item['check']}**\n\n{item['details']}")

            if result.warnings:
                st.markdown("**Warnings:**")
                for item in result.warnings:
                    st.warning(f"**{item['check']}**\n\n{item['details']}")


# File upload
uploaded_file = st.file_uploader("Upload generated edge case CSV", type=['csv'])

if uploaded_file:
    # Load CSV
    try:
        df = pd.read_csv(uploaded_file, header=None)

        # Show preview
        with st.expander("Preview CSV Data", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"Showing first 10 of {len(df)} rows, {len(df.columns)} columns")

        st.divider()

        # Validate button
        if st.button("Validate CSV", type="primary", use_container_width=True):
            with st.spinner("Validating..."):
                result = validate_edge_case_csv(df)

            display_validation_results(result)

    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")

else:
    # Instructions
    st.markdown("""
    ### How It Works

    Upload a generated edge case CSV and click **Validate** to check:

    | Category | Checks |
    |----------|--------|
    | **Structure** | Row count, column consistency, header labels |
    | **Content** | Action values, XPath format, template completeness |
    | **Format** | Pipe-separated values, single field per row, 4 edge cases |
    | **Integrity** | Click values preserved, descriptive row names |

    ---

    ### Expected CSV Format (v4.1)

    ```
    Row 1: Description | firstName    | email        | ...
    Row 2: Action      | input        | input        | ...
    Row 3: XPath       | //*[@id="..."]| //*[@id="..."]| ...
    Row 4: Perfect     | John         | a@b.com      | ...
    Row 5: firstName   | |@#$|123|AAA...| a@b.com    | ...
    Row 6: email       | John         | |@#$|123|AAA@x.com | ...
    ```

    Each edge case row tests **ONE field** with 4 pipe-separated values:
    `empty | special | numeric | long`
    """)

st.divider()
st.markdown("*Edge Case Test Data Validator v4.1*")
