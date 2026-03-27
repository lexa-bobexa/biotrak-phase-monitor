# Biotrak Phase Monitor (Streamlit)

This repository is the Streamlit runtime for Biotrak Phase Monitor.
It processes uploaded Excel sheets, queries ClinicalTrials.gov, and returns a cleaned output workbook.

## Local Development

### Prerequisites
- Python `3.10.4` (aligned with `.python-version`)
- Network access to `https://clinicaltrials.gov/api/v2/studies`

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Run App
```bash
streamlit run streamlit_app.py
```

## Application Flow

1. Upload input workbook (`.xlsx` or `.xls`).
2. Validate required columns per sheet:
   - At least one ID column: `bioTRAK Product ID` or `TC Scrape Number`
   - Required fields: `Product Name`, `Original Phase`
3. Query ClinicalTrials.gov for each product.
4. Filter studies by US/Canada/Europe locations.
5. Download generated output workbook.

## Tests
```bash
pytest -q
```

## Safe Deploy Checklist

Run this checklist before every deploy:

1. `pip install -r requirements.txt` succeeds in a clean environment.
2. `pytest -q` passes.
3. `streamlit run streamlit_app.py` boots locally.
4. Run one sample workbook end-to-end and verify download output.
5. Confirm there are no `PyQt6` imports and no `st.experimental_rerun` usage.
6. Merge/deploy only from reviewed branch.

## Rollback Plan

If deploy health checks fail:

1. Redeploy the previous known-good commit.
2. Validate app boot and one sample processing run.
3. Open follow-up fix on a new branch; do not patch production directly.
