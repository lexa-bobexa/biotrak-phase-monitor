from io import BytesIO

import pandas as pd

from logic.data_processing import create_results_workbook_bytes, get_trials


def test_create_results_workbook_bytes_deduplicates_nct_numbers():
    dataframe = pd.DataFrame(
        [
            {"NCT Number": "NCT001", "Product Name": "Drug A"},
            {"NCT Number": "NCT001", "Product Name": "Drug A"},
        ]
    )
    workbook_bytes = create_results_workbook_bytes({"SheetA": dataframe}, ["SheetA"])
    loaded = pd.read_excel(BytesIO(workbook_bytes), sheet_name=None)

    assert "SheetA" in loaded
    assert len(loaded["SheetA"]) == 1
    assert loaded["SheetA"].iloc[0]["NCT Number"] == "NCT001"


def test_get_trials_returns_filtered_trial_and_reports_progress(monkeypatch):
    input_frame = pd.DataFrame(
        [
            {
                "bioTRAK Product ID": "A-1",
                "Product Name": "Drug A",
                "Original Phase": "Phase 1",
            }
        ]
    )
    progress_updates = []

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "nextPageToken": None,
                "studies": [
                    {
                        "protocolSection": {
                            "identificationModule": {"nctId": "NCT001"},
                            "statusModule": {
                                "overallStatus": "RECRUITING",
                                "startDateStruct": {"date": "2025-01-01"},
                                "completionDateStruct": {"date": "2026-01-01"},
                            },
                            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor A"}},
                            "designModule": {"phases": ["PHASE2"]},
                            "oversightModule": {"isFdaRegulatedDrug": True},
                            "conditionsModule": {"conditions": ["Condition A"]},
                            "armsInterventionsModule": {"interventions": [{"name": "Drug A"}]},
                            "contactsLocationsModule": {
                                "locations": [{"country": "United States"}]
                            },
                        }
                    }
                ],
            }

    def mock_get(_url, timeout):
        assert timeout == 30
        return MockResponse()

    monkeypatch.setattr("logic.data_processing.requests.get", mock_get)

    results = get_trials(
        input_frame,
        "bioTRAK Product ID",
        progress_callback=lambda pct, msg: progress_updates.append((pct, msg)),
    )

    assert len(results) == 1
    assert results[0]["NCT Number"] == "NCT001"
    assert progress_updates[-1][0] == 100
