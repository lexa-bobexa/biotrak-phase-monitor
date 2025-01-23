import pandas as pd
import requests
import logging
import urllib.parse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_trials(df_input):
    """Retrieve trials for specific interventions and return filtered data."""
    results = []
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    page_size = 600  # Adjust based on expected data volume
    european_countries = {
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 
        'Germany', 'Greece', 'Hungary', 'Iceland', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands', 
        'Norway', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden', 'Switzerland', 'United Kingdom'
    }
    
    for index, row in df_input.iterrows():
        intervention_name = row['Product Name']
        product_id = row['bioTRAK Product ID']
        original_phase = row['Original Phase']
        page_token = None

        while True:
            encoded_intervention_name = urllib.parse.quote(intervention_name.strip())
            url = f"{base_url}?query.intr={encoded_intervention_name}&format=json&pageSize={page_size}"
            if page_token:
                url += f"&pageToken={page_token}"

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
                            'bioTRAK Product ID': product_id,
                            'bioTRAK Product Name': intervention_name,
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

                if not page_token:  # Last page
                    break
            else:
                logging.error(f"Failed to retrieve data with status code {response.status_code} for {intervention_name}")
                break
    return results

def load_interventions_from_excel(file_path):
    """Load intervention names and associated product ids from an Excel file."""
    try:
        df = pd.read_excel(file_path)
        return df[['Product Name', 'bioTRAK Product ID', 'Original Phase']]
    except Exception as e:
        logging.error(f"Failed to load Excel file: {e}")
        return pd.DataFrame()

def save_results_to_excel(results, output_dir):
    """Save the filtered results to an Excel file, removing duplicate NCT numbers."""
    try:
        df_results = pd.DataFrame(results)
        df_results.drop_duplicates(subset=['NCT Number'], inplace=True)  # Remove duplicates based on NCT Number
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/biotrak_scrape_{timestamp}.xlsx"
        df_results.to_excel(output_path, index=False)
        logging.info(f"Results saved to {output_path}")
    except Exception as e:
        logging.error(f"Failed to save results to Excel: {e}")

def main():
    input_file_path = '/Users/lexkopf/Documents/code_projects/biotrak_phase_monitor/DataScraping_2025-01-21.xlsx'
    output_directory = '/Users/lexkopf/Documents/code_projects/biotrak_phase_monitor'

    df_input = load_interventions_from_excel(input_file_path)
    if not df_input.empty:
        results = get_trials(df_input)
        save_results_to_excel(results, output_directory)
    else:
        logging.info("No intervention names found to process.")

if __name__ == '__main__':
    main()
