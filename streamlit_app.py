import logging
from datetime import datetime
from typing import List, Tuple

import streamlit as st

from logic.data_processing import create_results_workbook_bytes
from logic.workflow import process_workbook

LOGGER = logging.getLogger(__name__)

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )


def _process_uploaded_file(
    file_bytes: bytes, progress_bar: "st.delta_generator.DeltaGenerator"
) -> Tuple[bytes, str, List[str]]:
    def _on_progress(progress_value: float, message: str) -> None:
        progress_bar.progress(progress_value, text=message)

    results_dict, summary_messages = process_workbook(file_bytes, progress_callback=_on_progress)
    workbook_bytes = create_results_workbook_bytes(results_dict, results_dict.keys())
    output_filename = f"biotrak_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return workbook_bytes, output_filename, summary_messages


def main() -> None:
    st.set_page_config(page_title="Biotrak Phase Monitor", layout="wide")
    st.title("Biotrak Phase Monitor")
    st.caption("Upload an Excel file, query ClinicalTrials.gov, and download a cleaned output workbook.")

    if "result_bytes" not in st.session_state:
        st.session_state.result_bytes = None
    if "result_filename" not in st.session_state:
        st.session_state.result_filename = None
    if "summary_messages" not in st.session_state:
        st.session_state.summary_messages = []

    uploaded_file = st.file_uploader("Upload input workbook", type=["xlsx", "xls"])

    action_col, reset_col = st.columns([1, 1])
    with action_col:
        run_processing = st.button(
            "Run ClinicalTrials processing",
            type="primary",
            disabled=uploaded_file is None,
        )
    with reset_col:
        if st.button("Clear current output"):
            st.session_state.result_bytes = None
            st.session_state.result_filename = None
            st.session_state.summary_messages = []
            st.rerun()

    if run_processing:
        if uploaded_file is None:
            st.error("Please upload an Excel file before running processing.")
        else:
            progress_bar = st.progress(0.0, text="Preparing workbook...")
            try:
                file_bytes = uploaded_file.getvalue()
                result_bytes, result_filename, summary_messages = _process_uploaded_file(
                    file_bytes,
                    progress_bar,
                )
                st.session_state.result_bytes = result_bytes
                st.session_state.result_filename = result_filename
                st.session_state.summary_messages = summary_messages
                st.success("Processing complete. Download your output workbook below.")
            except Exception as exc:
                LOGGER.exception("Processing failed")
                st.error(f"Processing failed: {exc}")

    if st.session_state.summary_messages:
        with st.expander("Validation and processing summary", expanded=False):
            for message in st.session_state.summary_messages:
                st.write(f"- {message}")

    if st.session_state.result_bytes and st.session_state.result_filename:
        st.download_button(
            label="Download processed workbook",
            data=st.session_state.result_bytes,
            file_name=st.session_state.result_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
