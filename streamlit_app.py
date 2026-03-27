import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from logic.data_processing import create_results_workbook_bytes
from logic.workflow import get_workbook_validation_report, process_workbook

LOGGER = logging.getLogger(__name__)
APP_VERSION = os.getenv("APP_VERSION", "v1.1.0")
DEFAULT_APP_USERNAME = os.getenv("APP_USERNAME", "admin")
DEFAULT_APP_PASSWORD = os.getenv("APP_PASSWORD", "admin123")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )


def _get_secret_or_default(secret_key: str, default_value: str) -> str:
    try:
        return st.secrets.get(secret_key, default_value)
    except Exception:
        return default_value


def _initialize_auth_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None


def _show_login_page() -> None:
    st.title("BT Phase Monitor Login")
    st.caption(f"App version: {APP_VERSION}")

    col_left, col_center, col_right = st.columns([1, 1.2, 1])
    with col_center:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", use_container_width=True):
            valid_username = _get_secret_or_default("auth_username", DEFAULT_APP_USERNAME)
            valid_password = _get_secret_or_default("auth_password", DEFAULT_APP_PASSWORD)
            if username == valid_username and password == valid_password:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")


def _process_uploaded_file(
    file_bytes: bytes,
    progress_bar: "st.delta_generator.DeltaGenerator",
    trial_end_cutoff_years: int,
    include_unknown_end_dates: bool,
) -> Tuple[bytes, str, List[str], Dict[str, int]]:
    def _on_progress(progress_value: float, message: str) -> None:
        progress_bar.progress(progress_value, text=message)

    results_dict, summary_messages, metrics = process_workbook(
        file_bytes,
        progress_callback=_on_progress,
        trial_end_cutoff_years=trial_end_cutoff_years,
        include_unknown_end_dates=include_unknown_end_dates,
    )
    workbook_bytes = create_results_workbook_bytes(results_dict, results_dict.keys())
    output_filename = f"biotrak_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return workbook_bytes, output_filename, summary_messages, metrics


def main() -> None:
    st.set_page_config(page_title="Biotrak Phase Monitor", page_icon="📊", layout="wide")
    _initialize_auth_state()

    if not st.session_state.authenticated:
        _show_login_page()
        return

    st.title("Biotrak Phase Monitor")
    st.caption("Upload an Excel file, query ClinicalTrials.gov, and download a cleaned output workbook.")
    st.caption(f"App version: {APP_VERSION}")

    if "result_bytes" not in st.session_state:
        st.session_state.result_bytes = None
    if "result_filename" not in st.session_state:
        st.session_state.result_filename = None
    if "summary_messages" not in st.session_state:
        st.session_state.summary_messages = []
    if "run_metrics" not in st.session_state:
        st.session_state.run_metrics = None

    with st.sidebar:
        st.caption(f"Logged in as: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()
        st.divider()
        st.header("Processing Options")
        st.caption(f"Version: {APP_VERSION}")
        trial_end_cutoff_years = st.number_input(
            "Trial end cutoff (years)",
            min_value=1,
            max_value=20,
            value=8,
            step=1,
            help="Studies ending before this cutoff are excluded.",
        )
        include_unknown_end_dates = st.checkbox(
            "Include studies with unknown end date",
            value=True,
            help="If disabled, studies missing completion date are excluded.",
        )

    uploaded_file = st.file_uploader("Upload input workbook", type=["xlsx", "xls"])
    uploaded_file_bytes = uploaded_file.getvalue() if uploaded_file is not None else None

    if uploaded_file_bytes:
        try:
            validation_report = get_workbook_validation_report(uploaded_file_bytes)
            with st.expander("Pre-run validation", expanded=True):
                metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
                metric_col_1.metric("Total sheets", validation_report["total_sheets"])
                metric_col_2.metric("Valid sheets", validation_report["valid_sheets"])
                metric_col_3.metric(
                    "Non-empty valid sheets", validation_report["non_empty_valid_sheets"]
                )
                st.dataframe(pd.DataFrame(validation_report["rows"]), use_container_width=True)
        except Exception as exc:
            st.error(f"Could not validate uploaded workbook: {exc}")

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
            st.session_state.run_metrics = None
            st.rerun()

    if run_processing:
        if uploaded_file is None:
            st.error("Please upload an Excel file before running processing.")
        else:
            progress_bar = st.progress(0.0, text="Preparing workbook...")
            try:
                result_bytes, result_filename, summary_messages, run_metrics = _process_uploaded_file(
                    uploaded_file_bytes,
                    progress_bar,
                    trial_end_cutoff_years=trial_end_cutoff_years,
                    include_unknown_end_dates=include_unknown_end_dates,
                )
                st.session_state.result_bytes = result_bytes
                st.session_state.result_filename = result_filename
                st.session_state.summary_messages = summary_messages
                st.session_state.run_metrics = run_metrics
                st.success("Processing complete. Download your output workbook below.")
            except Exception as exc:
                LOGGER.exception("Processing failed")
                st.error(f"Processing failed: {exc}")

    if st.session_state.run_metrics:
        st.subheader("Run summary")
        summary_col_1, summary_col_2, summary_col_3 = st.columns(3)
        summary_col_1.metric("Processed sheets", st.session_state.run_metrics["processed_sheets"])
        summary_col_2.metric("Output rows", st.session_state.run_metrics["output_rows"])
        summary_col_3.metric("Skipped (missing ID)", st.session_state.run_metrics["skipped_missing_id"])

        details_col_1, details_col_2, details_col_3 = st.columns(3)
        details_col_1.metric("Total sheets", st.session_state.run_metrics["total_sheets"])
        details_col_2.metric("Valid sheets", st.session_state.run_metrics["valid_sheets"])
        details_col_3.metric(
            "Non-empty valid sheets", st.session_state.run_metrics["non_empty_valid_sheets"]
        )

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
