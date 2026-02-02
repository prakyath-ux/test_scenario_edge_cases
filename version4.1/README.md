# XPath Analytics Recorder

Automated QA testing tool for web element capture and test scenario generation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure API key
cp config/.env.example .env
# Edit .env with your Groq API key

# Run the app
streamlit run app.py
```

## Project Structure

```
version4.1/
├── app.py                 # Main Streamlit dashboard
├── pages/                 # Streamlit multipage apps
│   └── 2_Live_View.py     # Real-time capture viewer
├── src/                   # Core modules
│   ├── recorder.py        # Playwright browser automation
│   ├── llm_generator.py   # LLM test scenario generator
│   └── csv_validator.py   # Test case validator
├── data/
│   ├── samples/           # Sample/reference data
│   └── captures/          # Runtime capture output
├── notebooks/             # Analysis notebooks
├── config/                # Configuration files
└── requirements.txt
```

## Usage

1. **Record**: Enter URL and click "Start Recording" to capture element interactions
2. **Generate**: Use LLM generator to create edge case test scenarios
3. **Validate**: Verify generated test cases meet quality standards

## Built by QA Automation Team - Impacto Digital
