def test_streamlit_app_imports():
    import streamlit_app

    assert hasattr(streamlit_app, "main")
