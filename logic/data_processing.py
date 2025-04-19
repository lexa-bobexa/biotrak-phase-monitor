import pandas as pd
import requests
import urllib.parse
from datetime import datetime
from config import BASE_URL, EUROPEAN_COUNTRIES
from logic.logging_config import logger

def get_trials(df_input, id_column):
    """Retrieve trials for specific interventions and return filtered data."""
    results = []
    page_size = 1000  # Adjust based on expected data volume
    european_countries = set(EUROPEAN_COUNTRIES)  # Convert list to set for efficient lookups
    
    for index, row in df_input.iterrows():
        intervention_name = row['Product Name']
        product_id = row.get(id_column, None)
        original_phase = row['Original Phase']

        if product_id is None:
            logger.warning(f"Skipping row {index} due to missing '{id_column}'")
            continue

        page_token = None

        while True:
            encoded_intervention_name = urllib.parse.quote(intervention_name.strip(), safe="")
            # Replace URL-encoded brackets with \[ and \] for clinicaltrials.gov search syntax
            encoded_intervention_name = encoded_intervention_name.replace('%5B', '\\[').replace('%5D', '\\]')
            url = f"{BASE_URL}?query.intr={encoded_intervention_name}&format=json&pageSize={page_size}"
            if page_token:
                url += f"&pageToken={page_token}"

            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    page_token = data.get('nextPageToken')
                    studies = data.get('studies', [])
                    for study in studies:
                        protocol_section = study['protocolSection']
                        study_info = protocol_section['identificationModule']
                        status_info = protocol_section['statusModule']
                        sponsor_info = protocol_section['sponsorCollaboratorsModule']
                        design_info = protocol_section.get('designModule', {})
                        oversight_info = protocol_section.get('oversightModule', {})
                        conditions_info = protocol_section.get('conditionsModule', {})
                        locations = protocol_section.get('contactsLocationsModule', {}).get('locations', [])
                        countries = {location['country'] for location in locations if 'country' in location}  # Set comprehension to gather unique countries
                        
                        if countries.intersection({'United States', 'Canada'} | european_countries):  # Filter for US, Canada and Europe
                            details = {
                                id_column: product_id,
                                'Product Name': intervention_name,
                                'Product Name on CT.gov':', '.join([intervention.get('name', 'Unknown intervention') for intervention in protocol_section.get('armsInterventionsModule', {}).get('interventions', [])]),
                                'original_phase': original_phase,
                                'Phase on CT.gov': design_info.get('phases', ['Not Available'])[0],
                                'NCT Number': study_info['nctId'],
                                'sponsor_name': sponsor_info['leadSponsor']['name'],
                                'Status on CT.gov': status_info['overallStatus'],
                                'Location on CT.gov': ', '.join(countries),
                                'Trial Start Date': status_info.get('startDateStruct', {}).get('date', 'Not Available'),
                                'Trial End Date': status_info.get('completionDateStruct', {}).get('date', 'Not Available'),
                                'Is FDA Regulated Drug': oversight_info.get('isFdaRegulatedDrug', False),  # Default to False if the field is missing
                                'Conditions': ', '.join(conditions_info.get('conditions', []))  # Combine all conditions into a single string
                            }
                            results.append(details)
                else:
                    logger.error(f"Failed to retrieve data with status code {response.status_code} for {intervention_name}")
                    break
            except Exception as e:
                logger.error(f"Error making API request for {intervention_name}: {str(e)}")
                break

            if not page_token:  # Last page
                break
    return results

def save_results_to_excel(results_dict, output_dir, input_sheet_names):
    """
    Save the filtered results to an Excel file, removing duplicate NCT numbers.

    Args:
        results_dict (dict): A dictionary of {sheet_name: pd.DataFrame} to save.
        output_dir (str): The directory where the output file will be saved.
        input_sheet_names (iterable): The sheet names processed, used to name the sheets in the output file.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/biotrak_scrape_{timestamp}.xlsx"

        with pd.ExcelWriter(output_path) as writer:
            for sheet_name in input_sheet_names:
                df_results = results_dict.get(sheet_name)
                if df_results is not None:
                    # Remove duplicates based on NCT Number
                    df_results.drop_duplicates(subset=['NCT Number'], inplace=True)
                    df_results.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results to Excel: {e}")