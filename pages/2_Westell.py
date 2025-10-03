import streamlit as st
import tempfile
import zipfile
import os
import pandas as pd
from pathlib import Path
from extractor import extract_po_info_Westl

st.set_page_config(page_title="PO PDF Extractor", layout="wide")
# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("You must be logged in to access this page.")
    st.stop()  # Stop further execution of the page
# -----------------------------
# Modern Dual-mode CSS Styling for st.data_editor
# -----------------------------
st.markdown(
    """
    <style>
    button[title], div.stDataEditor div[role="button"] {
        opacity: 1 !important;
        visibility: visible !important;
    }
    input[type="checkbox"] {
        width: 18px;
        height: 18px;
        cursor: pointer;
    }
    div.stDataEditor td, div.stDataEditor th {
        padding: 8px 12px;
        border-radius: 6px;
        transition: background-color 0.2s ease, color 0.2s ease;
    }
    div.stDataEditor table {
        border-collapse: separate !important;
        border-spacing: 0 4px !important;
    }
    div.stDataEditor td {
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    /* Light Mode */
    [data-baseweb="light"] div.stDataEditor th {
        background-color: #f0f2f6 !important;
        color: #000 !important;
        font-weight: bold;
    }
    [data-baseweb="light"] div.stDataEditor td {
        background-color: #ffffff !important;
        color: #000 !important;
    }
    [data-baseweb="light"] div.stDataEditor tr:nth-child(even) td {
        background-color: #f9f9f9 !important;
    }
    [data-baseweb="light"] div.stDataEditor tr:hover td {
        background-color: #e6f2ff !important;
    }

    /* Dark Mode */
    [data-baseweb="dark"] div.stDataEditor th {
        background-color: #2c2c2c !important;
        color: #f0f0f0 !important;
        font-weight: bold;
    }
    [data-baseweb="dark"] div.stDataEditor td {
        background-color: #1e1e1e !important;
        color: #f0f0f0 !important;
    }
    [data-baseweb="dark"] div.stDataEditor tr:nth-child(even) td {
        background-color: #2a2a2a !important;
    }
    [data-baseweb="dark"] div.stDataEditor tr:hover td {
        background-color: #3a3a3a !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Process uploaded files
# -----------------------------
def process_files(uploaded_files):
    temp_dir = Path(tempfile.mkdtemp())
    pdf_dir = temp_dir / "pdf_folder"
    pdf_dir.mkdir(exist_ok=True)

    for uploaded_file in uploaded_files:
        file_path = pdf_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        if uploaded_file.name.lower().endswith(".zip"):
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(pdf_dir)
            file_path.unlink()

    pdf_files = [
        os.path.join(root, f)
        for root, _, files_in_dir in os.walk(pdf_dir)
        for f in files_in_dir
        if f.lower().endswith(".pdf") and not f.startswith("._") and "__MACOSX" not in root
    ]

    all_rows = []
    for pdf_file in pdf_files:
        all_rows.extend(extract_po_info_Westl(pdf_file))


    if all_rows:
        df = pd.DataFrame(all_rows, columns=[
        "Document Number", "Part/Description", "Item_Code", "PO_issue Date", "Delivery Date",
        "SHIP VIA", "FOB", "UoM(optional)", "Quantity", "Price", "Total",
        "Payment Term", "BUYER", "REQ#", "REQUISITIONER"
    ])

    # Remove exact duplicate rows
        df.drop_duplicates(inplace=True)

    # Sort by Document Number
        df.sort_values(by="Document Number", inplace=True)

        df.to_csv("po_extracted.csv", index=False)
        print("✅ Extraction complete. Saved to po_extracted.csv")

    if not all_rows:
        return pd.DataFrame()

    return df

# -----------------------------
# Main Streamlit app
# -----------------------------
def main():
    # Centered company + app heading
    st.markdown(
        """
        <h2 style='text-align: center;'>
            Westell
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <h3 style='text-align: center;'>
            Start converting PO to CSV
        </h3>""",
        unsafe_allow_html=True)

    st.write("---")

    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if "df_display" not in st.session_state:
        st.session_state.df_display = pd.DataFrame()

    uploaded_files = st.file_uploader(
        "Upload PDF(s) or ZIP containing PDFs",
        type=["pdf", "zip"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.session_state.uploaded_files = list(uploaded_files)
        st.session_state.df = process_files(st.session_state.uploaded_files)

        if not st.session_state.df.empty:
            st.session_state.df_display = st.session_state.df.copy()
            st.session_state.df_display.insert(0, "Select", True)
    else:
        st.session_state.uploaded_files = []
        st.session_state.df = pd.DataFrame()
        st.session_state.df_display = pd.DataFrame()

    if st.session_state.df.empty:
        st.info("Upload PDF(s) or ZIP to start extraction.")
        return

    st.success("✅ Extraction complete!")

    df_view = st.session_state.df_display.copy()

    # -----------------------------
    # Sidebar Controls
    # -----------------------------
    st.sidebar.header("⚙️ Table Controls")

    # 1. Keep/Delete columns
    keep_cols = st.sidebar.multiselect(
        "Column Remove / Reorder",
        options=[c for c in df_view.columns if c != "Select"],
        default=[c for c in df_view.columns if c != "Select"]
    )

    if not keep_cols:
        st.warning("⚠️ Please select at least one column to view or refresh & upload again to see all columns.")
        return

    df_view = df_view[["Select"] + keep_cols]

    # 2. Sort
    sort_col = st.sidebar.selectbox("Sort by column", options=keep_cols)
    sort_order = st.sidebar.radio("Order", ["Ascending", "Descending"], horizontal=True)
    df_view = df_view.sort_values(
        by=sort_col,
        ascending=(sort_order == "Ascending"),
        ignore_index=True
    )

    # 3. Search
    search_text = st.sidebar.text_input("🔍 Search to filter row ")
    if search_text:
        df_view = df_view[df_view.apply(
            lambda row: row.astype(str).str.contains(search_text, case=False).any(),
            axis=1
        )]

    # -----------------------------
    # Editable table
    # -----------------------------
    st.subheader("Select Rows to Download")
    edited_df = st.data_editor(
        df_view,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select row to download",
                width="medium"
            )
        },
        hide_index=True,
        key="data_editor",
        width="stretch"   # ✅ replaces use_container_width=True
    )

    st.session_state.df_display = edited_df

    # -----------------------------
    # Download selected rows as CSV
    # -----------------------------
    selected_df = st.session_state.df_display[st.session_state.df_display["Select"]]

    if not selected_df.empty:
        download_df = selected_df.drop(columns=["Select"])
        file_data = download_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Selected Rows as CSV",
            data=file_data,
            file_name="Extracted_Selected.csv",
            mime="text/csv",
            width="stretch"   # ✅ replaces use_container_width=True
        )

if __name__ == "__main__":
    main()