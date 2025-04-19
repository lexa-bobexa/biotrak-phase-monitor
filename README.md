# Biotrak Phase Monitor

A tool for monitoring clinical trials from ClinicalTrials.gov, focusing on interventions in the US, Canada, and European countries.

## Features

- Fetches clinical trial data from ClinicalTrials.gov API
- Filters trials by location (US, Canada, and European countries)
- Caches API responses for improved performance
- Exports results to Excel with automatic duplicate removal

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
- Ensure your config.py contains the correct BASE_URL and EUROPEAN_COUNTRIES list

## Usage

1. Prepare your input Excel file with columns:
   - 'Product Name'
   - 'Original Phase'
   - Your specified ID column

2. Run the tool:
```python
from logic.data_processing import get_trials, save_results_to_excel

# Process your data
results = get_trials(your_dataframe, 'your_id_column')

# Save results
save_results_to_excel(results_dict, 'output_directory', ['sheet_names'])
```

## Output

The tool generates an Excel file with the following information for each trial:
- Product ID and name
- Trial phase information
- NCT number
- Sponsor name
- Trial status
- Location information
- Start and end dates
- FDA regulation status
- Conditions studied

## Cache

- API responses are cached in the `.cache` directory
- Cache persists between runs for improved performance
- Cache can be safely deleted if needed

## Notes

- The tool automatically handles pagination and rate limiting
- Results are filtered to include only trials in specified regions
- Duplicate NCT numbers are automatically removed from the output 