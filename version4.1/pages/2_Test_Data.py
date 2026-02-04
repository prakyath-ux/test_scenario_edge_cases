# pages/2_Test_Data.py - Test Data Generation & Validation
# Combined Generator + Validator with Schedule and Report placeholders

import streamlit as st
import pandas as pd
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from groq import Groq
from dotenv import load_dotenv
from validator import validate_edge_case_csv, ValidationResult

# Load .env from multiple possible locations
env_paths = [
    os.path.join(os.path.dirname(__file__), '..', 'config', '.env'),
    os.path.join(os.path.dirname(__file__), '..', '.env'),
    os.path.join(os.path.dirname(__file__), 'src', '.env'),
    '.env'
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

# Lazy Groq client
client = None

def get_groq_client():
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        client = Groq(api_key=api_key)
    return client


st.set_page_config(page_title="Test Data Manager", page_icon="📊", layout="wide")

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
    .section-card {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Test Data Manager")
st.markdown("*Generate edge case test data and validate CSV outputs*")
st.divider()


# ============ VALIDATION DISPLAY FUNCTION ============
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

    # Unified checklist
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


# ============ MAIN TABS ============
tab_upload, tab_schedule, tab_report = st.tabs(["📤 New Upload", "📅 Schedule", "📈 Report"])


# ============ TAB 1: NEW UPLOAD (Generator + Validator) ============
with tab_upload:
    st.subheader("Generate & Validate Edge Case Test Data")

    # Sub-tabs for Generate vs Validate
    gen_tab, val_tab = st.tabs(["🧪 Generate", "✅ Validate"])

    # -------- GENERATE SUB-TAB --------
    with gen_tab:
        st.markdown("**Upload recorded flow CSV to generate edge case test data**")
        st.caption("Input: Vertical CSV from recorder (columns: Group, Element, Action, Property, Strategy, XPath, Value)")

        gen_file = st.file_uploader("Upload recorded flow CSV", type=['csv'], key="gen_upload")

        if gen_file:
            df = pd.read_csv(gen_file)

            with st.expander("View Raw Uploaded Data", expanded=False):
                st.dataframe(df, use_container_width=True)

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

            def transpose_to_company_format(df: pd.DataFrame) -> dict:
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

                    row = [f"{field_name} ({group})" if group else field_name]
                    for i, (val, ftype) in enumerate(zip(transposed['values'], transposed['field_types'])):
                        row.append(edge_values if i == idx else val)

                    edge_case_rows.append({
                        'row_data': row, 'description': description,
                        'target_field': field_name, 'target_index': idx, 'group': group
                    })
                return edge_case_rows

            def create_output_dataframe(transposed: dict, edge_case_rows: list) -> pd.DataFrame:
                rows = [
                    ['Group'] + transposed['groups'],
                    ['Description'] + transposed['descriptions'],
                    ['Action'] + transposed['actions'],
                    ['Property'] + transposed['properties'],
                    ['Strategy'] + transposed['strategies'],
                    ['XPath'] + transposed['xpaths'],
                    ['Perfect_Template (Valid Flow)'] + transposed['values']
                ]
                for edge_row in edge_case_rows:
                    rows.append(edge_row['row_data'])
                return pd.DataFrame(rows)

            def create_description_summary(edge_case_rows: list) -> pd.DataFrame:
                return pd.DataFrame([{
                    'Row': f'Row {i + 8}',  # 7 header rows + 1 for 1-indexing
                    'Target Field': er['target_field'],
                    'Group/Section': er['group'],
                    'Test Description': er['description']
                } for i, er in enumerate(edge_case_rows)])

            # ---- Analysis ----
            st.subheader("Field Analysis")
            transposed = transpose_to_company_format(df)
            text_fields = get_text_input_fields(transposed)

            type_counts = {}
            for ft in transposed['field_types']:
                type_counts[ft] = type_counts.get(ft, 0) + 1

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Fields", len(transposed['descriptions']))
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
                groq_client = get_groq_client()
                if not groq_client:
                    st.error("GROQ_API_KEY not found! Set it in your .env file.")
                    st.stop()

                with st.spinner("Generating edge cases with LLM..."):
                    try:
                        prompt = build_llm_prompt(text_fields, transposed)
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=4000
                        )
                        llm_response = response.choices[0].message.content
                        llm_data = parse_llm_response(llm_response, text_fields)
                        edge_case_rows = generate_edge_case_rows(transposed, text_fields, llm_data)
                        output_df = create_output_dataframe(transposed, edge_case_rows)
                        summary_df = create_description_summary(edge_case_rows)

                        # Store in session state for validation
                        st.session_state['generated_df'] = output_df
                        st.session_state['summary_df'] = summary_df

                        st.success(f"Generated {len(edge_case_rows)} edge case test rows!")

                        st.subheader("Test Description Summary")
                        st.dataframe(summary_df, use_container_width=True, height=300)

                        st.subheader("Generated Test Data")

                        # View toggle for generated data
                        gen_view_mode = st.radio(
                            "View Mode:",
                            ["Horizontal (Company Format)", "Vertical (Standard)"],
                            horizontal=True,
                            key="gen_view_mode"
                        )

                        if gen_view_mode == "Horizontal (Company Format)":
                            st.dataframe(output_df, use_container_width=True, height=400, hide_index=True)
                        else:
                            # Convert to vertical format for viewing
                            # Row indices: 0=Group, 1=Description, 2=Action, 3=Property, 4=Strategy, 5=XPath, 6=Values
                            vertical_rows = []
                            if len(output_df) >= 7:
                                groups = output_df.iloc[0, 1:].tolist()
                                descriptions = output_df.iloc[1, 1:].tolist()
                                actions = output_df.iloc[2, 1:].tolist()
                                properties = output_df.iloc[3, 1:].tolist()
                                strategies = output_df.iloc[4, 1:].tolist()
                                xpaths = output_df.iloc[5, 1:].tolist()
                                values = output_df.iloc[6, 1:].tolist()

                                for i in range(len(descriptions)):
                                    vertical_rows.append({
                                        'Group': groups[i],
                                        'Element': descriptions[i],
                                        'Action': actions[i],
                                        'Property': properties[i],
                                        'Strategy': strategies[i],
                                        'XPath': xpaths[i],
                                        'Value': values[i]
                                    })

                            vertical_df = pd.DataFrame(vertical_rows)
                            st.dataframe(vertical_df, use_container_width=True, height=400)

                        # Downloads
                        st.divider()
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.download_button(
                                "📥 Company Format CSV",
                                output_df.to_csv(index=False, header=False),
                                file_name="edge_case_test_data_company.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col2:
                            # Create vertical CSV from the data
                            vertical_export = []
                            if len(output_df) >= 7:
                                groups = output_df.iloc[0, 1:].tolist()
                                descriptions = output_df.iloc[1, 1:].tolist()
                                actions = output_df.iloc[2, 1:].tolist()
                                properties = output_df.iloc[3, 1:].tolist()
                                strategies = output_df.iloc[4, 1:].tolist()
                                xpaths = output_df.iloc[5, 1:].tolist()
                                values = output_df.iloc[6, 1:].tolist()
                                for i in range(len(descriptions)):
                                    vertical_export.append({
                                        'Group': groups[i],
                                        'Element': descriptions[i],
                                        'Action': actions[i],
                                        'Property': properties[i],
                                        'Strategy': strategies[i],
                                        'XPath': xpaths[i],
                                        'Value': values[i]
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

                        # Auto-validate
                        st.divider()
                        st.subheader("Auto-Validation")
                        result = validate_edge_case_csv(output_df)
                        display_validation_checklist(result)

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        else:
            st.markdown("""
            ### How to use:
            1. **Upload** a recorded flow CSV (from the XPath recorder)
            2. **Review** the field analysis
            3. **Generate** edge case test data
            4. **Download** the generated CSV

            ### Output format:
            - Row 1-3: Description, Action, XPath metadata
            - Row 4: Perfect template (valid values)
            - Row 5+: Edge case rows (one per text input field)
            """)

    # -------- VALIDATE SUB-TAB --------
    with val_tab:
        st.markdown("**Upload a generated edge case CSV to validate its structure**")
        st.caption("Input: Horizontal CSV from generator (Company Format with rows: Group, Description, Action, etc.)")

        val_file = st.file_uploader("Upload edge case CSV to validate", type=['csv'], key="val_upload")

        if val_file:
            try:
                df = pd.read_csv(val_file, header=None)

                with st.expander("Preview CSV Data", expanded=False):
                    st.dataframe(df.head(10), use_container_width=True)
                    st.caption(f"{len(df)} rows, {len(df.columns)} columns")

                if st.button("Validate CSV", type="primary", use_container_width=True):
                    with st.spinner("Validating..."):
                        result = validate_edge_case_csv(df)
                    display_validation_checklist(result)

            except Exception as e:
                st.error(f"Error loading CSV: {str(e)}")
        else:
            st.markdown("""
            ### Validation Checks
            - **Structure**: Row count, column consistency, header labels
            - **Content**: Action values, XPath format, template completeness
            - **Format**: Pipe-separated values, single field per row, 4 edge cases
            - **Integrity**: Click values preserved, descriptive row names
            """)


# ============ TAB 2: SCHEDULE (Placeholder) ============
with tab_schedule:
    st.subheader("Schedule Test Runs")
    st.info("🚧 **Coming Soon**\n\nThis section will allow you to schedule automated test data generation and validation runs.")

    st.markdown("""
    ### Planned Features:
    - Schedule recurring test data generation
    - Set up automated validation checks
    - Email notifications for failures
    - Integration with CI/CD pipelines
    """)


# ============ TAB 3: REPORT (Placeholder) ============
with tab_report:
    st.subheader("Test Reports & Analytics")
    st.info("🚧 **Coming Soon**\n\nThis section will provide analytics and reports on generated test data.")

    st.markdown("""
    ### Planned Features:
    - Historical validation results
    - Test coverage metrics
    - Edge case distribution charts
    - Export reports to PDF
    """)


st.divider()
st.markdown("*Test Data Manager v4.1 • Built for QA Automation*")
