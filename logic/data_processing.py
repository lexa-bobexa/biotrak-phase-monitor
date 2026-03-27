import logging
from datetime import datetime
from io import BytesIO
from typing import Callable, Dict, Iterable, Optional

import pandas as pd
import requests
import urllib.parse

LOGGER = logging.getLogger(__name__)
EUROPEAN_COUNTRIES = {
    "Austria",
    "Belgium",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "United Kingdom",
}
TARGET_COUNTRIES = {"United States", "Canada"} | EUROPEAN_COUNTRIES


def get_trials(
    df_input: pd.DataFrame,
    id_column: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    request_timeout_seconds: int = 30,
) -> list[dict]:
    """Retrieve ClinicalTrials.gov studies for each product row."""
    results = []
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    page_size = 1000
    total_rows = len(df_input.index) or 1

    for row_position, (index, row) in enumerate(df_input.iterrows(), start=1):
        intervention_name = str(row["Product Name"])
        product_id = row.get(id_column, None)
        original_phase = row["Original Phase"]

        if product_id is None:
            LOGGER.warning("Skipping row %s due to missing '%s'", index, id_column)
            continue

        page_token = None

        while True:
            encoded_intervention_name = urllib.parse.quote(intervention_name.strip(), safe="")
            url = f"{base_url}?query.intr={encoded_intervention_name}&format=json&pageSize={page_size}"
            if page_token:
                url += f"&pageToken={page_token}"

            response = requests.get(url, timeout=request_timeout_seconds)
            if response.status_code == 200:
                data = response.json()
                page_token = data.get("nextPageToken")
                studies = data.get("studies", [])
                for study in studies:
                    protocol_section = study["protocolSection"]
                    study_info = protocol_section["identificationModule"]
                    status_info = protocol_section["statusModule"]
                    sponsor_info = protocol_section["sponsorCollaboratorsModule"]
                    design_info = protocol_section.get("designModule", {})
                    oversight_info = protocol_section.get("oversightModule", {})
                    conditions_info = protocol_section.get("conditionsModule", {})
                    locations = protocol_section.get("contactsLocationsModule", {}).get("locations", [])
                    countries = {location["country"] for location in locations if "country" in location}

                    if countries.intersection(TARGET_COUNTRIES):
                        details = {
                            id_column: product_id,
                            "Product Name": intervention_name,
                            "Product Name on CT.gov": ", ".join(
                                [
                                    intervention.get("name", "Unknown intervention")
                                    for intervention in protocol_section.get("armsInterventionsModule", {}).get(
                                        "interventions", []
                                    )
                                ]
                            ),
                            "original_phase": original_phase,
                            "Phase on CT.gov": design_info.get("phases", ["Not Available"])[0],
                            "NCT Number": study_info["nctId"],
                            "sponsor_name": sponsor_info["leadSponsor"]["name"],
                            "Status on CT.gov": status_info["overallStatus"],
                            "Location on CT.gov": ", ".join(sorted(countries)),
                            "Trial Start Date": status_info.get("startDateStruct", {}).get("date", "Not Available"),
                            "Trial End Date": status_info.get(
                                "completionDateStruct", {}
                            ).get("date", "Not Available"),
                            "Is FDA Regulated Drug": oversight_info.get("isFdaRegulatedDrug", False),
                            "Conditions": ", ".join(conditions_info.get("conditions", [])),
                        }
                        results.append(details)

                if not page_token:
                    break
            else:
                LOGGER.error(
                    "Failed to retrieve data with status code %s for '%s'",
                    response.status_code,
                    intervention_name,
                )
                break

        if progress_callback:
            percent_complete = int((row_position / total_rows) * 100)
            progress_callback(percent_complete, f"Processed {row_position}/{total_rows} products")

    return results


def create_results_workbook_bytes(
    results_dict: Dict[str, pd.DataFrame],
    input_sheet_names: Iterable[str],
) -> bytes:
    """Serialize results into an Excel workbook stored in memory."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name in input_sheet_names:
            dataframe = results_dict.get(sheet_name)
            if dataframe is None:
                continue

            deduplicated = dataframe.drop_duplicates(subset=["NCT Number"])
            deduplicated.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    return buffer.getvalue()


def save_results_to_excel(
    results_dict: Dict[str, pd.DataFrame],
    output_dir: str,
    input_sheet_names: Iterable[str],
) -> str:
    """Persist results workbook to disk for compatibility with existing flows."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/biotrak_scrape_{timestamp}.xlsx"
    workbook_bytes = create_results_workbook_bytes(results_dict, input_sheet_names)
    with open(output_path, "wb") as output_file:
        output_file.write(workbook_bytes)
    LOGGER.info("Results saved to %s", output_path)
    return output_path