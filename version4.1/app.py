# app.py - Streamlit Dashboard with Recording Control + Live View (Stacked)
import streamlit as st
import subprocess
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import os

st.set_page_config(page_title="XPath Analytics Recorder", page_icon="🎯", layout="wide")


def transpose_to_company_format(entries):
    """
    Transpose vertical data to horizontal company format.

    Input (vertical):
        Each entry: {label, action, property, xpath, values, strategy, group}

    Output (horizontal):
        Row 1: Group       | (blank for assignment) | ...
        Row 2: Description | Element1 | Element2 | ...
        Row 3: Action      | click    | input    | ...
        Row 4: Property    | text     | text     | ...
        Row 5: Strategy    | id       | name     | ...
        Row 6: XPath       | //*[...]| //*[...] | ...
        Row 7: Value       | Click   | JOHN     | ...
    """
    if not entries:
        return pd.DataFrame()

    # Build column headers from labels
    labels = [e["label"] for e in entries]
    groups = [e.get("group", "") for e in entries]
    actions = [e["action"] for e in entries]
    properties = [e.get("property", "") for e in entries]
    strategies = [e.get("strategy", "") for e in entries]
    xpaths = [e["xpath"] for e in entries]
    values = ["Click" if e["action"] == "click" else e.get("values", "") for e in entries]

    # Create transposed rows
    rows = [
        ["Group"] + groups,
        ["Description"] + labels,
        ["Action"] + actions,
        ["Property"] + properties,
        ["Strategy"] + strategies,
        ["XPath"] + xpaths,
        ["Value"] + values
    ]

    return pd.DataFrame(rows)

# CSS Styling
st.markdown("""
<style>
    [data-testid="metric-container"] {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
    }
    .stDataFrame {
        border-radius: 10px;
    }
    .stApp {
        background-color: #0e1117;
    }
    .stMarkdown, h1, h2, h3, p {
        color: #ffffff !important;
    }
    .stSubheader, [data-testid="stSubheader"] {
        color: #ffffff !important;
        font-weight: 600;
    }
    .stRadio label, .stSelectbox label {
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #ffffff !important;
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

DATA_DIR = Path(__file__).parent / "data" / "captures"
STATE_FILE = DATA_DIR / ".recording_state.json"
LIVE_CAPTURE_FILE = DATA_DIR / ".live_capture.jsonl"

# Initialize session state
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'process' not in st.session_state:
    st.session_state.process = None
if 'last_json' not in st.session_state:
    st.session_state.last_json = None

st.markdown("# 🎯 XPath Analytics Recorder")
st.markdown("*Automated element capture for QA testing*")

st.divider()

# ============ SECTION 1: RECORDING ============
st.subheader("🎬 Record New Session")

col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input("Enter URL:", placeholder="https://example.com/app")

with col2:
    st.write("")  # Spacer
    st.write("")  # Spacer

# Format selection with checkboxes
st.write("**Output Formats:**")
format_col1, format_col2, format_col3 = st.columns(3)
with format_col1:
    format_json = st.checkbox("JSON", value=True)
with format_col2:
    format_csv = st.checkbox("CSV", value=True)
with format_col3:
    format_py = st.checkbox("Python", value=False)

# Build format string
formats = []
if format_json:
    formats.append('json')
if format_csv:
    formats.append('csv')
if format_py:
    formats.append('py')

# Start/Stop buttons
if not st.session_state.recording:
    if st.button("🚀 Start Recording", type="primary", use_container_width=True):
        if not url_input:
            st.error("❌ Please enter a URL")
        elif not url_input.startswith(('http://', 'https://')):
            st.error("❌ Invalid URL. Must start with http:// or https://")
        elif not formats:
            st.error("❌ Please select at least one output format")
        else:
            # Start the recorder subprocess
            format_str = ','.join(formats)
            output_dir = str(Path(__file__).parent)

            # Write state file for Live View page
            state = {
                "is_recording": True,
                "url": url_input,
                "started_at": datetime.now().isoformat(),
                "formats": formats
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)

            # Clear previous live capture file
            if LIVE_CAPTURE_FILE.exists():
                LIVE_CAPTURE_FILE.unlink()

            recorder_path = str(Path(__file__).parent / "src" / "recorder.py")
            st.session_state.process = subprocess.Popen(
                ['python', recorder_path, url_input, format_str, str(DATA_DIR), str(LIVE_CAPTURE_FILE)],
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            st.session_state.recording = True
            st.rerun()

else:
    # Show recording status
    st.warning("🔴 **Recording in progress...** Click elements in the browser window.")
    st.info(f"📍 URL: {url_input}")

    if st.button("⏹️ Stop Recording", type="secondary", use_container_width=True):
        if st.session_state.process:
            st.session_state.process.terminate()
            time.sleep(1)  # Wait for files to be saved
            st.session_state.process = None
        st.session_state.recording = False

        # Clean up state file
        if STATE_FILE.exists():
            STATE_FILE.unlink()

        st.success("Recording stopped. Processing data...")
        time.sleep(1)
        st.rerun()


st.divider()

# ============ SECTION 2: LIVE VIEW (Only shown during recording) ============
if st.session_state.recording:
    st.subheader("👁️ Live Capture View")
    st.markdown("*Real-time view of captured elements*")

    # Group assignment section
    st.markdown("##### Assign Group")
    grp_col1, grp_col2 = st.columns([3, 1])
    with grp_col1:
        group_name = st.text_input("Group name:", placeholder="e.g., Personal Info, Contact Details", key="group_input")
    with grp_col2:
        st.write("")  # Spacer
        if st.button("Assign Group", type="primary", use_container_width=True):
            if group_name.strip():
                # Check if last line is a group marker (allow rename)
                should_replace = False
                lines = []
                if LIVE_CAPTURE_FILE.exists():
                    with open(LIVE_CAPTURE_FILE, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            try:
                                last_entry = json.loads(lines[-1].strip())
                                if last_entry.get("type") == "group":
                                    should_replace = True
                            except:
                                pass

                if should_replace:
                    # Remove last line and rewrite
                    with open(LIVE_CAPTURE_FILE, 'w') as f:
                        f.writelines(lines[:-1])

                # Write new group marker
                group_entry = {
                    "type": "group",
                    "name": group_name.strip(),
                    "timestamp": datetime.now().isoformat()
                }
                with open(LIVE_CAPTURE_FILE, 'a') as f:
                    f.write(json.dumps(group_entry) + '\n')
                st.success(f"Group '{group_name}' assigned!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Please enter a group name")

    st.markdown("---")

    # Clear data button (for multi-page recording)
    clear_col1, clear_col2 = st.columns([1, 3])
    with clear_col1:
        if st.button("🗑️ Clear Data", type="secondary", use_container_width=True):
            if LIVE_CAPTURE_FILE.exists():
                # Clear the file but write a marker so recorder knows it was cleared
                with open(LIVE_CAPTURE_FILE, 'w') as f:
                    f.write(json.dumps({
                        "type": "cleared",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Data cleared - starting fresh capture"
                    }) + '\n')
                st.success("Captured data cleared! Browser still recording.")
                time.sleep(0.5)
                st.rerun()
    with clear_col2:
        st.caption("Clear captured data to start fresh (browser stays open)")

    st.markdown("---")

    # Auto-refresh settings
    refresh_col1, refresh_col2 = st.columns([1, 3])
    with refresh_col1:
        auto_refresh = st.checkbox("Auto-refresh", value=True)
    with refresh_col2:
        refresh_interval = st.slider("Interval (seconds)", 1, 10, 2, disabled=not auto_refresh)

    # Display settings
    max_entries = st.slider("Show last N entries", 10, 2000, 1000)

    # View toggle
    view_mode = st.radio("View Mode:", ["Vertical (Standard)", "Horizontal (Company Format)"], horizontal=True)

    st.markdown("---")

    # Load and display live data
    if not LIVE_CAPTURE_FILE.exists():
        st.info("Waiting for first interaction...")
    else:
        # Read JSONL file and process groups
        entries = []
        group_markers = []  # List of (index, group_name)

        with open(LIVE_CAPTURE_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("type") == "cleared":
                        # Reset everything - start fresh from this point
                        entries = []
                        group_markers = []
                    elif entry.get("type") == "group":
                        # Record where this group marker appears
                        group_markers.append((len(entries), entry["name"]))
                    elif entry.get("type") == "xpath":
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue

        if not entries:
            st.info("Waiting for interactions...")
        else:
            # Assign groups to entries (retroactive assignment)
            # Group marker at position N means: all entries BEFORE it (0 to N-1) get that group
            for i, entry in enumerate(entries):
                entry["group"] = ""  # Default: no group

            # Process group markers in order
            prev_idx = 0
            for marker_idx, grp_name in group_markers:
                # Assign group name to entries from prev_idx to marker_idx-1
                for i in range(prev_idx, marker_idx):
                    entries[i]["group"] = grp_name
                prev_idx = marker_idx
            # Entries after last marker remain ungrouped (empty)

            # Summary metrics
            st.markdown(f"##### Captured: {len(entries)} elements")

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            clicks = sum(1 for e in entries if e.get("action", "") == "click")
            inputs = sum(1 for e in entries if e.get("action", "") != "click")
            ungrouped = sum(1 for e in entries if e.get("group", "") == "")
            metric_col1.metric("Total", len(entries))
            metric_col2.metric("Clicks", clicks)
            metric_col3.metric("Inputs", inputs)
            metric_col4.metric("Ungrouped", ungrouped)

            # Show last N entries
            recent_entries = entries[-max_entries:]

            # Display based on view mode
            if view_mode == "Vertical (Standard)":
                df = pd.DataFrame(recent_entries)
                # Reorder columns - Group first, Value last for visibility
                display_cols = ["group", "label", "action", "property", "strategy", "xpath", "values"]
                available_cols = [c for c in display_cols if c in df.columns]
                if available_cols:
                    df = df[available_cols]
                    # Rename columns dynamically based on what's available
                    col_names = {"group": "Group", "label": "Element", "action": "Action",
                                 "property": "Property", "strategy": "Strategy", "xpath": "XPath", "values": "Value"}
                    df.columns = [col_names.get(c, c) for c in available_cols]
                st.dataframe(df, use_container_width=True, height=400)
            else:
                # Horizontal (Company Format) - transposed view
                transposed_df = transpose_to_company_format(recent_entries)
                if not transposed_df.empty:
                    st.dataframe(transposed_df, use_container_width=True, height=250, hide_index=True)
                else:
                    st.info("No data to display in horizontal format")

            # Download current section data
            st.markdown("##### Download Current Section")
            download_col1, download_col2, download_col3 = st.columns(3)

            # Prepare vertical CSV for download
            export_df = pd.DataFrame(entries)
            export_cols = ["group", "label", "action", "property", "strategy", "xpath", "values"]
            available_export_cols = [c for c in export_cols if c in export_df.columns]
            if available_export_cols:
                export_df = export_df[available_export_cols]
                col_names = {"group": "Group", "label": "Element", "action": "Action",
                             "property": "Property", "strategy": "Strategy", "xpath": "XPath", "values": "Value"}
                export_df.columns = [col_names.get(c, c) for c in available_export_cols]

            # Prepare transposed CSV for download
            transposed_export = transpose_to_company_format(entries)

            with download_col1:
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    "📥 Vertical CSV",
                    csv_data,
                    file_name=f"section_{datetime.now().strftime('%H%M%S')}_vertical.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with download_col2:
                transposed_csv = transposed_export.to_csv(index=False, header=False)
                st.download_button(
                    "📥 Company Format CSV",
                    transposed_csv,
                    file_name=f"section_{datetime.now().strftime('%H%M%S')}_company.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with download_col3:
                st.caption("Vertical: for Test Data Generator | Company: for QA team")

            st.markdown("---")

            # Show latest entry highlighted
            st.markdown("##### Latest Capture")
            latest = entries[-1]
            st.code(f"""Group:    {latest.get('group', '')}
Element:  {latest['label']}
Action:   {latest['action']}
Property: {latest.get('property', '')}
Value:    {latest.get('values', '')}
XPath:    {latest['xpath']}
Strategy: {latest['strategy']}""")

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

st.divider()

# ============ SECTION 3: RESULTS (Collapsed by default) ============
json_files = sorted(DATA_DIR.glob("xpaths_*.json"), reverse=True)

if json_files:
    with st.expander(f"📊 View Previous Sessions ({len(json_files)} available)", expanded=False):
        # File selector
        selected_file = st.selectbox(
            "Select captured session:",
            json_files,
            format_func=lambda x: x.name
        )

        # Load data
        with open(selected_file) as f:
            data = json.load(f)

        st.success(f"✅ Loaded {data['total_elements']} elements from session")

        # Summary stats
        st.markdown("#### Summary")
        col1, col2, col3, col4 = st.columns(4)

        clicks = sum(1 for x in data["xpaths"] if x["action"] == "click")
        changes = sum(1 for x in data["xpaths"] if x["action"] == "change")

        col1.metric("Total Elements", data["total_elements"])
        col2.metric("Clicks", clicks)
        col3.metric("Input (Changes)", changes)
        col4.metric("URL", data["url"][:30] + "...")

        # View options
        st.markdown("#### Captured Data")

        view_option = st.radio(
            "Select view:",
            [
                "Full Data (with XPath)",
                "Simple View (no XPath)",
                "Developer View (XPath Only)",
                "QA View (Label + Action + Value)"
            ],
            horizontal=True
        )

        # Create dataframe
        df = pd.DataFrame(data["xpaths"])
        df["action"] = df["action"].replace("change", "Input")

        # Display based on selection
        if view_option == "Full Data (with XPath)":
            st.dataframe(df, use_container_width=True)

        elif view_option == "Simple View (no XPath)":
            simple_df = df[["label", "action", "strategy", "values"]].copy()
            simple_df.columns = ["Element Name", "Action", "Strategy Used", "Value Entered"]
            st.dataframe(simple_df, use_container_width=True)

        elif view_option == "Developer View (XPath Only)":
            dev_df = df[["label", "xpath", "action"]].copy()
            dev_df.columns = ["Element", "XPath", "Action"]
            st.dataframe(dev_df, use_container_width=True)

        elif view_option == "QA View (Label + Action + Value)":
            qa_df = df[["label", "action", "values"]].copy()
            qa_df.columns = ["Element", "Action", "Value"]
            st.dataframe(qa_df, use_container_width=True)

        st.divider()

        # Download Section
        st.markdown("#### Download")

        col1, col2 = st.columns(2)

        with col1:
            csv_data = df.to_csv(index=False)
            st.download_button("Download CSV", csv_data, file_name="xpaths_export.csv", mime="text/csv")

        with col2:
            st.download_button("Download JSON", json.dumps(data, indent=2), file_name="xpaths_export.json", mime="application/json")

st.divider()
st.markdown("*Built by QA Automation Team • Impacto Digital*")
