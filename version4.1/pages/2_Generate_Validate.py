# pages/2_Generate_Validate.py - Generate Edge Cases & Validate CSV
# This page handles LLM-powered edge case generation and CSV validation

import streamlit as st
import pandas as pd
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from groq import Groq
from dotenv import load_dotenv
from validator import validate_edge_case_csv, ValidationResult

# Load .env from multiple possible locations
env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
    '.env'
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

# Lazy Groq client
groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        groq_client = Groq(api_key=api_key)
    return groq_client

st.set_page_config(page_title="Generate  and Validate", page_icon="", layout="wide")

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
    .stDownloadButton button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a5a !important;
    }
    .stDownloadButton button:hover {
        background-color: #3a3a4a !important;
        border-color: #6a6a7a !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Upload Element Properties CSV")
st.markdown("*Generate edge cases with LLM and validate CSV structure*")
st.divider()

# Validation display function
def display_validation_checklist(result: ValidationResult):
    """Display validation as unified checklist"""
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

    all_checks = (
        [('pass', i['check'], i['details']) for i in result.passed] +
        [('fail', i['check'], i['details']) for i in result.failed] +
        [('warn', i['check'], i['details']) for i in result.warnings]
    )

    for status, check_name, details in all_checks:
        icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}[status]
        css = {"pass": "check-pass", "fail": "check-fail", "warn": "check-warn"}[status]
        detail_text = details[:57] + "..." if len(details) > 60 else details

        st.markdown(f"""
        <div class="check-row {css}">
            <strong>{icon} {check_name}</strong>
            <span style="color: #888; margin-left: 10px;">{detail_text}</span>
        </div>
        """, unsafe_allow_html=True)

# Sub-tabs for Generate vs Validate
gen_tab, val_tab = st.tabs(["🧪 Generate", "✅ Validate"])

# -------- GENERATE SUB-TAB --------
with gen_tab:
    st.markdown("**Upload recorded flow CSV to generate edge case test data**")
    st.caption("Input: Vertical CSV from recorder (columns: Step, Group, Element, Property, Action, XPath, Value)")

    gen_file = st.file_uploader("Upload recorded flow CSV", type=['csv'], key="gen_upload")

    if gen_file:
        df_gen = pd.read_csv(gen_file)

        with st.expander("View Raw Uploaded Data", expanded=False):
            st.dataframe(df_gen, use_container_width=True)

        # ---- Field Classification Functions ----
        def classify_field(field_name: str, action: str, value: str) -> str:
            value_str = str(value).strip().lower()
            field_lower = field_name.lower()

            if action.lower() == 'click':
                return 'click'
            if value_str in ['true', 'false']:
                return 'boolean'
            if 'otp' in field_lower:
                return 'otp'
            if any(pattern in str(value) for pattern in ['fakepath', '.png', '.jpg', '.jpeg', '.pdf', '.doc', 'C:\\', '/']):
                if any(ext in str(value).lower() for ext in ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.gif', '.bmp']):
                    return 'file_upload'
            return 'text_input'

        def transpose_for_generation(df: pd.DataFrame) -> dict:
            descriptions, actions, xpaths, values, field_types, groups, strategies, properties = [], [], [], [], [], [], [], []

            for _, row in df.iterrows():
                element = row.get('Element', row.get('Label', ''))
                action = row.get('Action', '')
                value = row.get('Value', '')
                xpath = row.get('XPath', '')
                group = row.get('Group', '')
                strategy = row.get('Strategy', '')
                prop = row.get('Property', '')

                if pd.isna(value): value = ''
                if pd.isna(element): element = ''
                if pd.isna(strategy): strategy = ''
                if pd.isna(prop): prop = ''

                descriptions.append(element)
                actions.append(action.lower())
                xpaths.append(xpath)
                groups.append(group if not pd.isna(group) else '')
                strategies.append(strategy)
                properties.append(prop)
                values.append('Click' if action.lower() == 'click' else str(value))
                field_types.append(classify_field(element, action, value))

            return {
                'descriptions': descriptions, 'actions': actions, 'xpaths': xpaths,
                'values': values, 'field_types': field_types, 'groups': groups,
                'strategies': strategies, 'properties': properties
            }

        def get_text_input_fields(transposed: dict) -> list:
            text_fields = []
            for i, (ft, name, value, group) in enumerate(zip(
                transposed['field_types'], transposed['descriptions'],
                transposed['values'], transposed['groups']
            )):
                if ft == 'text_input':
                    text_fields.append((i, name, value, group))
            return text_fields

        def build_llm_prompt(text_fields: list, transposed: dict) -> str:
            field_summary = [f"  - Field: '{name}' | Group: '{group}' | Valid Value: '{value}'"
                             for idx, name, value, group in text_fields]

            return f"""You are a QA test data expert. Generate edge case test values for form validation testing.

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

## RULES
- Output ONLY the lines in the specified format, nothing else
- The EDGE_CASE_VALUES must be exactly 4 values separated by " | "
- First edge case value should be empty (just a space before the first |)
- Make descriptions clear and specific to the field's purpose
- Do NOT include any markdown, headers, or explanations

## GENERATE OUTPUT FOR ALL {len(text_fields)} FIELDS:
"""

        def parse_llm_response(response_text: str, text_fields: list) -> dict:
            field_data = {}
            for line in response_text.strip().split('\n'):
                line = line.strip()
                if not line or '|||' not in line:
                    continue
                parts = line.split('|||')
                if len(parts) >= 3:
                    field_data[parts[0].strip().lower()] = {
                        'description': parts[1].strip(),
                        'edge_values': parts[2].strip()
                    }
            return field_data

        def generate_edge_case_rows(transposed: dict, text_fields: list, llm_data: dict) -> list:
            edge_case_rows = []
            for idx, field_name, original_value, group in text_fields:
                field_key = field_name.lower()
                if field_key in llm_data:
                    description = llm_data[field_key]['description']
                    edge_values = llm_data[field_key]['edge_values']
                else:
                    description = f"Tests {field_name} validation - empty, special chars, numeric, long input"
                    edge_values = " | @#$%^&*<> | 12345 | " + "A" * 50

                # Row name format: Value_fieldName (for regex matching)
                row_name = f"Value_{field_name}"
                row = [row_name]
                for i, (val, ftype) in enumerate(zip(transposed['values'], transposed['field_types'])):
                    if i == idx:
                        row.append(edge_values)
                    elif ftype == 'click':
                        row.append('')  # Empty for click actions (automation checks Action column)
                    else:
                        row.append(val)

                edge_case_rows.append({
                    'row_data': row, 'description': description,
                    'target_field': field_name, 'target_index': idx, 'group': group
                })
            return edge_case_rows

        def create_output_dataframe(transposed: dict, edge_case_rows: list) -> pd.DataFrame:
            # Generate step numbers (1, 2, 3, ...)
            steps = [str(i + 1) for i in range(len(transposed['descriptions']))]

            rows = [
                ['Steps'] + steps,
                ['Group'] + transposed['groups'],
                ['Elements'] + transposed['descriptions'],
                ['Property'] + transposed['properties'],
                ['Action'] + transposed['actions'],
                ['XPath'] + transposed['xpaths'],
                ['Perfect_Template (Valid Flow)'] + transposed['values']
            ]
            for edge_row in edge_case_rows:
                rows.append(edge_row['row_data'])
            return pd.DataFrame(rows)

        def create_description_summary(edge_case_rows: list) -> pd.DataFrame:
            # 7 header rows: Steps, Group, Elements, Action, Property, XPath, Perfect_Template
            # Edge cases start at Row 8
            return pd.DataFrame([{
                'Row': f'Row {i + 8}',
                'Target Field': er['target_field'],
                'Group/Section': er['group'],
                'Test Description': er['description']
            } for i, er in enumerate(edge_case_rows)])

        # ---- Analysis ----
        st.markdown("##### Field Analysis")
        transposed_gen = transpose_for_generation(df_gen)
        text_fields = get_text_input_fields(transposed_gen)

        type_counts = {}
        for ft in transposed_gen['field_types']:
            type_counts[ft] = type_counts.get(ft, 0) + 1

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Fields", len(transposed_gen['descriptions']))
        col2.metric("Text Inputs", type_counts.get('text_input', 0))
        col3.metric("Clicks", type_counts.get('click', 0))
        col4.metric("Booleans", type_counts.get('boolean', 0))
        col5.metric("Files/OTP", type_counts.get('file_upload', 0) + type_counts.get('otp', 0))

        st.info(f"**{len(text_fields)} text input fields** will get edge case testing")

        with st.expander(f"View {len(text_fields)} Text Input Fields", expanded=False):
            st.dataframe(pd.DataFrame([
                {'Field': name, 'Group': group, 'Valid Value': value}
                for idx, name, value, group in text_fields
            ]), use_container_width=True)

        st.divider()

        # ---- Generate Button ----
        if st.button("Generate Edge Case Test Data", type="primary", use_container_width=True):
            client = get_groq_client()
            if not client:
                st.error("GROQ_API_KEY not found! Set it in your .env file.")
                st.stop()

            with st.spinner("Generating edge cases with LLM..."):
                try:
                    prompt = build_llm_prompt(text_fields, transposed_gen)
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=4000
                    )
                    llm_response = response.choices[0].message.content
                    llm_data = parse_llm_response(llm_response, text_fields)
                    edge_case_rows = generate_edge_case_rows(transposed_gen, text_fields, llm_data)
                    output_df = create_output_dataframe(transposed_gen, edge_case_rows)
                    summary_df = create_description_summary(edge_case_rows)

                    st.session_state['generated_df'] = output_df
                    st.session_state['summary_df'] = summary_df

                    st.success(f"Generated {len(edge_case_rows)} edge case test rows!")

                    st.markdown("##### Test Description Summary")
                    st.dataframe(summary_df, use_container_width=True, height=300)

                    st.markdown("##### Generated Test Data")

                    gen_view_mode = st.radio(
                        "View Mode:",
                        ["Horizontal CSV", "Vertical CSV"],
                        horizontal=True,
                        key="gen_view_mode"
                    )

                    if gen_view_mode == "Horizontal CSV":
                        st.dataframe(output_df, use_container_width=True, height=400, hide_index=True)
                    else:
                        vertical_rows = []
                        if len(output_df) >= 7:
                            # Row indices: 0=Steps, 1=Group, 2=Elements, 3=Property, 4=Action, 5=XPath, 6=Values
                            steps = output_df.iloc[0, 1:].tolist()
                            groups = output_df.iloc[1, 1:].tolist()
                            elements = output_df.iloc[2, 1:].tolist()
                            properties = output_df.iloc[3, 1:].tolist()
                            actions = output_df.iloc[4, 1:].tolist()
                            xpaths = output_df.iloc[5, 1:].tolist()
                            values = output_df.iloc[6, 1:].tolist()

                            for i in range(len(elements)):
                                vertical_rows.append({
                                    'Step': steps[i], 'Group': groups[i], 'Element': elements[i],
                                    'Property': properties[i], 'Action': actions[i],
                                    'XPath': xpaths[i], 'Value': values[i]
                                })

                        vertical_df = pd.DataFrame(vertical_rows)
                        st.dataframe(vertical_df, use_container_width=True, height=400)

                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            "📥 Horizontal CSV",
                            output_df.to_csv(index=False, header=False),
                            file_name="edge_case_test_data_company.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col2:
                        vertical_export = []
                        if len(output_df) >= 7:
                            # Row indices: 0=Steps, 1=Group, 2=Elements, 3=Property, 4=Action, 5=XPath, 6=Values
                            steps = output_df.iloc[0, 1:].tolist()
                            groups = output_df.iloc[1, 1:].tolist()
                            elements = output_df.iloc[2, 1:].tolist()
                            properties = output_df.iloc[3, 1:].tolist()
                            actions = output_df.iloc[4, 1:].tolist()
                            xpaths = output_df.iloc[5, 1:].tolist()
                            values = output_df.iloc[6, 1:].tolist()
                            for i in range(len(elements)):
                                vertical_export.append({
                                    'Step': steps[i], 'Group': groups[i], 'Element': elements[i],
                                    'Property': properties[i], 'Action': actions[i],
                                    'XPath': xpaths[i], 'Value': values[i]
                                })
                        vert_df = pd.DataFrame(vertical_export)
                        st.download_button(
                            "📥 Vertical CSV",
                            vert_df.to_csv(index=False),
                            file_name="edge_case_test_data_vertical.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with col3:
                        st.download_button(
                            "📥 Descriptions CSV",
                            summary_df.to_csv(index=False),
                            file_name="test_descriptions.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                    st.divider()
                    st.markdown("##### Auto-Validation")
                    result = validate_edge_case_csv(output_df)
                    display_validation_checklist(result)

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    else:
        st.markdown("""
        **How to use:**
        1. Upload a recorded flow CSV (from the XPath recorder)
        2. Review the field analysis
        3. Generate edge case test data
        4. Download the generated CSV
        """)

# -------- VALIDATE SUB-TAB --------
with val_tab:
    st.markdown("**Upload a generated edge case CSV to validate its structure**")
    st.caption("Input: Horizontal CSV from generator")

    val_file = st.file_uploader("Upload edge case CSV to validate", type=['csv'], key="val_upload")

    if val_file:
        try:
            df_val = pd.read_csv(val_file, header=None)

            with st.expander("Preview CSV Data", expanded=False):
                st.dataframe(df_val.head(10), use_container_width=True)
                st.caption(f"{len(df_val)} rows, {len(df_val.columns)} columns")

            if st.button("Validate CSV", type="primary", use_container_width=True):
                with st.spinner("Validating..."):
                    result = validate_edge_case_csv(df_val)
                display_validation_checklist(result)

        except Exception as e:
            st.error(f"Error loading CSV: {str(e)}")
    else:
        st.markdown("""
        **Validation Checks:**
        - Structure: Row count, column consistency, header labels
        - Content: Action values, XPath format, template completeness
        - Format: Pipe-separated values, single field per row, 4 edge cases
        """)

st.divider()
st.markdown("*Generate & Validate v4.1 • Powered by Groq LLM*")
