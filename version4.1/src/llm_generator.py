# llm_generator.py - Edge Case Test Data Generator (v4.1)
# Generates synthetic test data with 4 edge cases per text input field
# Output: Transposed company format with pipe-separated edge case values

import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
import os
import re

# Load .env from multiple possible locations
env_paths = [
    os.path.join(os.path.dirname(__file__), '..', 'config', '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
    os.path.join(os.path.dirname(__file__), '.env'),
    '.env'
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

# Configure Groq (lazy initialization)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None

def get_groq_client():
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        client = Groq(api_key=api_key)
    return client

st.set_page_config(page_title="Edge Case Generator", page_icon="🧪", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.title("🧪 Edge Case Test Data Generator")
st.markdown("*Upload a recorded flow CSV → Generate edge case test scenarios*")
st.divider()


def classify_field(field_name: str, action: str, value: str) -> str:
    """
    Classify a field into categories:
    - click: Button/dropdown clicks
    - boolean: true/false checkboxes
    - otp: OTP input fields
    - file_upload: File path inputs
    - text_input: Text fields (need edge case testing)
    """
    value_str = str(value).strip().lower()
    field_lower = field_name.lower()

    # Click actions
    if action.lower() == 'click':
        return 'click'

    # Boolean fields
    if value_str in ['true', 'false']:
        return 'boolean'

    # OTP fields
    if 'otp' in field_lower:
        return 'otp'

    # File uploads (check for file path patterns)
    if any(pattern in str(value) for pattern in ['fakepath', '.png', '.jpg', '.jpeg', '.pdf', '.doc', 'C:\\', '/']):
        if any(ext in str(value).lower() for ext in ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.gif', '.bmp']):
            return 'file_upload'

    # Default: text input (needs edge case testing)
    return 'text_input'


def transpose_to_company_format(df: pd.DataFrame) -> dict:
    """
    Transpose recorded CSV to company format.
    Returns dict with: descriptions, actions, xpaths, values, field_types
    """
    descriptions = []
    actions = []
    xpaths = []
    values = []
    field_types = []
    groups = []

    for _, row in df.iterrows():
        element = row.get('Element', row.get('Label', ''))
        action = row.get('Action', '')
        value = row.get('Value', '')
        xpath = row.get('XPath', '')
        group = row.get('Group', '')

        # Handle NaN values
        if pd.isna(value):
            value = ''
        if pd.isna(element):
            element = ''

        descriptions.append(element)
        actions.append(action.lower())
        xpaths.append(xpath)
        groups.append(group)

        # For click actions, value is "Click"
        if action.lower() == 'click':
            values.append('Click')
        else:
            values.append(str(value))

        # Classify field type
        field_type = classify_field(element, action, value)
        field_types.append(field_type)

    return {
        'descriptions': descriptions,
        'actions': actions,
        'xpaths': xpaths,
        'values': values,
        'field_types': field_types,
        'groups': groups
    }


def get_text_input_fields(transposed: dict) -> list:
    """
    Get list of text input fields that need edge case testing.
    Returns list of (index, field_name, original_value, group) tuples.
    """
    text_fields = []
    for i, (field_type, name, value, group) in enumerate(zip(
        transposed['field_types'],
        transposed['descriptions'],
        transposed['values'],
        transposed['groups']
    )):
        if field_type == 'text_input':
            text_fields.append((i, name, value, group))
    return text_fields


def build_llm_prompt(text_fields: list, transposed: dict) -> str:
    """
    Build advanced prompt for LLM to generate edge case descriptions and values.
    """
    # Build field summary for LLM
    field_summary = []
    for idx, name, value, group in text_fields:
        field_summary.append(f"  - Field: '{name}' | Group: '{group}' | Valid Value: '{value}'")

    prompt = f"""You are a QA test data expert. Generate edge case test values for form validation testing.

## INPUT: Text Input Fields That Need Testing
{chr(10).join(field_summary)}

## YOUR TASK
For EACH field above, provide:
1. A clear DESCRIPTION explaining what this test case validates
2. Four EDGE CASE VALUES separated by " | " (pipe with spaces)

## EDGE CASE TYPES (in this exact order)
1. **empty**: Empty string (leave blank)
2. **special**: Special characters that might break validation (e.g., @#$%^&*<>)
3. **numeric**: Numbers only (e.g., 12345)
4. **long**: Excessively long string (50+ characters of repeated text)

## OUTPUT FORMAT (strictly follow this)
For each field, output exactly one line in this format:
FIELD_NAME|||DESCRIPTION|||EDGE_CASE_VALUES

Example:
firstName|||Tests firstName validation - empty value should trigger required field error, special chars should be rejected, numeric-only should fail name validation, excessive length should be truncated or rejected||| | @#$%^&*<> | 12345 | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
email|||Tests email validation - empty should trigger required error, special chars without @ should fail format, numeric-only invalid email, excessively long email should fail||| | @#$%^&*<> | 12345 | AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA@test.com

## RULES
- Output ONLY the lines in the specified format, nothing else
- The EDGE_CASE_VALUES must be exactly 4 values separated by " | "
- First edge case value should be empty (just a space before the first |)
- Make descriptions clear and specific to the field's purpose
- Consider the field name and group context when writing descriptions
- Do NOT include any markdown, headers, or explanations

## GENERATE OUTPUT FOR ALL {len(text_fields)} FIELDS:
"""
    return prompt


def parse_llm_response(response_text: str, text_fields: list) -> dict:
    """
    Parse LLM response into field -> (description, edge_values) mapping.
    """
    field_data = {}
    lines = response_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or '|||' not in line:
            continue

        parts = line.split('|||')
        if len(parts) >= 3:
            field_name = parts[0].strip()
            description = parts[1].strip()
            edge_values = parts[2].strip()
            field_data[field_name.lower()] = {
                'description': description,
                'edge_values': edge_values
            }

    return field_data


def generate_edge_case_rows(transposed: dict, text_fields: list, llm_data: dict) -> list:
    """
    Generate edge case test rows.
    Each row targets ONE text input field with 4 pipe-separated edge case values.
    """
    edge_case_rows = []

    for idx, field_name, original_value, group in text_fields:
        # Get LLM-generated data or use defaults
        field_key = field_name.lower()
        if field_key in llm_data:
            description = llm_data[field_key]['description']
            edge_values = llm_data[field_key]['edge_values']
        else:
            # Fallback defaults
            description = f"Tests {field_name} validation - empty, special chars, numeric, long input"
            edge_values = " | @#$%^&*<> | 12345 | " + "A" * 50

        # Build the row - copy all valid values, replace target with edge cases
        row = []
        row.append(f"{field_name} ({group})" if group else field_name)  # Description with group context

        for i, (val, ftype) in enumerate(zip(transposed['values'], transposed['field_types'])):
            if i == idx:
                # This is the target field - insert edge case values
                row.append(edge_values)
            else:
                # Keep original value
                row.append(val)

        edge_case_rows.append({
            'row_data': row,
            'description': description,
            'target_field': field_name,
            'target_index': idx,
            'group': group
        })

    return edge_case_rows


def create_output_dataframe(transposed: dict, edge_case_rows: list) -> pd.DataFrame:
    """
    Create the final output DataFrame in company format.
    """
    # Build header row (column indices)
    num_cols = len(transposed['descriptions'])

    # Build rows
    rows = []

    # Row 0: Description (element names)
    rows.append(['Description'] + transposed['descriptions'])

    # Row 1: Action
    rows.append(['Action'] + transposed['actions'])

    # Row 2: XPath
    rows.append(['XPath'] + transposed['xpaths'])

    # Row 3: Perfect template (all valid values)
    rows.append(['Perfect_Template (Valid Flow)'] + transposed['values'])

    # Edge case rows
    for edge_row in edge_case_rows:
        rows.append(edge_row['row_data'])

    # Create DataFrame
    df = pd.DataFrame(rows)

    return df


def create_description_summary(edge_case_rows: list) -> pd.DataFrame:
    """
    Create a summary table explaining each edge case row.
    """
    summary_data = []
    for i, edge_row in enumerate(edge_case_rows):
        summary_data.append({
            'Row': f'Row {i + 5}',  # Starts at row 5 (after Description, Action, XPath, Perfect)
            'Target Field': edge_row['target_field'],
            'Group/Section': edge_row['group'],
            'Test Description': edge_row['description']
        })

    return pd.DataFrame(summary_data)


# ============ STREAMLIT UI ============

# File upload
uploaded_file = st.file_uploader("Upload recorded flow CSV", type=['csv'])

if uploaded_file:
    # Load and display raw data
    df = pd.read_csv(uploaded_file)

    with st.expander("📄 View Raw Uploaded Data", expanded=False):
        st.dataframe(df, use_container_width=True)

    # Show field classification summary
    st.subheader("📊 Field Analysis")

    transposed = transpose_to_company_format(df)
    text_fields = get_text_input_fields(transposed)

    # Count by type
    type_counts = {}
    for ft in transposed['field_types']:
        type_counts[ft] = type_counts.get(ft, 0) + 1

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Fields", len(transposed['descriptions']))
    col2.metric("Text Inputs", type_counts.get('text_input', 0))
    col3.metric("Clicks", type_counts.get('click', 0))
    col4.metric("Booleans", type_counts.get('boolean', 0))
    col5.metric("Files/OTP", type_counts.get('file_upload', 0) + type_counts.get('otp', 0))

    st.info(f"**{len(text_fields)} text input fields** will get edge case testing → **{len(text_fields)} test rows** generated")

    # Show text fields that will be tested
    with st.expander(f"🔍 View {len(text_fields)} Text Input Fields to Test", expanded=False):
        text_field_df = pd.DataFrame([
            {'Field': name, 'Group': group, 'Valid Value': value}
            for idx, name, value, group in text_fields
        ])
        st.dataframe(text_field_df, use_container_width=True)

    st.divider()

    # Generate button
    if st.button("🚀 Generate Edge Case Test Data", type="primary", use_container_width=True):
        # Check for API key first
        groq_client = get_groq_client()
        if not groq_client:
            st.error("❌ GROQ_API_KEY not found! Please set it in your .env file or environment.")
            st.code("# Create .env file in version4.1/config/ folder:\nGROQ_API_KEY=your_api_key_here")
            st.stop()

        with st.spinner("Generating edge cases with LLM..."):
            # Build and send prompt to LLM
            prompt = build_llm_prompt(text_fields, transposed)

            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Lower temperature for consistent output
                    max_tokens=4000
                )

                llm_response = response.choices[0].message.content

                # Parse LLM response
                llm_data = parse_llm_response(llm_response, text_fields)

                # Generate edge case rows
                edge_case_rows = generate_edge_case_rows(transposed, text_fields, llm_data)

                # Create output DataFrame
                output_df = create_output_dataframe(transposed, edge_case_rows)

                # Create description summary
                summary_df = create_description_summary(edge_case_rows)

                st.success(f"✅ Generated {len(edge_case_rows)} edge case test rows!")

                # Display results
                st.subheader("📋 Test Description Summary")
                st.markdown("*Use this to understand what each test row validates:*")
                st.dataframe(summary_df, use_container_width=True, height=300)

                st.subheader("📊 Generated Test Data (Transposed Format)")
                st.markdown("*Row 4 = Perfect template, Rows 5+ = Edge case tests:*")
                st.dataframe(output_df, use_container_width=True, height=400)

                # Download buttons
                st.divider()
                st.subheader("💾 Download")

                col1, col2 = st.columns(2)

                with col1:
                    # Main test data CSV
                    csv_data = output_df.to_csv(index=False, header=False)
                    st.download_button(
                        "📥 Download Test Data (CSV)",
                        csv_data,
                        file_name="edge_case_test_data.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with col2:
                    # Description summary CSV
                    summary_csv = summary_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Test Descriptions (CSV)",
                        summary_csv,
                        file_name="test_descriptions.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                # Show LLM response for debugging
                with st.expander("🔧 Debug: LLM Response", expanded=False):
                    st.code(llm_response)

            except Exception as e:
                st.error(f"Error generating test data: {str(e)}")
                st.info("Make sure GROQ_API_KEY is set in your .env file")

else:
    # Instructions when no file uploaded
    st.markdown("""
    ### How to use:
    1. **Upload** a recorded flow CSV (from the XPath recorder)
    2. **Review** the field analysis - text inputs will get edge case testing
    3. **Generate** edge case test data with one click
    4. **Download** the transposed test data CSV

    ### Output format:
    - **Row 1**: Field descriptions (element names)
    - **Row 2**: Actions (click/input)
    - **Row 3**: XPaths (for automation)
    - **Row 4**: Perfect template (all valid values)
    - **Row 5+**: Edge case rows (one per text input field)

    ### Edge case values (pipe-separated in target cell):
    - `empty` | `special chars` | `numeric only` | `long string`
    """)

st.divider()
st.markdown("*Built for QA Automation • Edge Case Generator v4.1*")
