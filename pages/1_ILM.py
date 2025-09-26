import streamlit as st
import pandas as pd
import zipfile
from io import BytesIO
from helpers import extract_po_info, extract_item_blocks

# Check if the user is logged in
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("You must be logged in to access this page.")
    st.stop()  # Stop further execution of the page

# Main content for the 1_ILM page
st.title("1_ILM Parser: PDF to CSV Converter")
st.write("This page allows you to upload PDF files and convert them into CSV format.")

# File uploader for ZIP or multiple PDFs
uploaded_files = st.file_uploader(
    "Upload a ZIP file or multiple PDF files", 
    type=["zip", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    pdf_files = []

    # Handle ZIP file or individual PDFs
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.endswith(".pdf"):
                        pdf_files.append(BytesIO(zip_ref.read(file_name)))
        elif uploaded_file.name.endswith(".pdf"):
            pdf_files.append(uploaded_file)  # Keep as is, already file-like

    if pdf_files:
        st.success(f"Found {len(pdf_files)} PDF file(s) to process.")

        # Process each PDF and extract data
        all_data = []
        for pdf_file in pdf_files:
            # Ensure the file pointer is at the start
            pdf_file.seek(0)

            # Extract PO info and item blocks
            po_info = extract_po_info(pdf_file)
            item_blocks = extract_item_blocks(pdf_file)

            # Combine PO info and item blocks into a single dictionary
            if isinstance(item_blocks, list):  # Ensure item_blocks is a list of dictionaries
                for item in item_blocks:
                    combined_data = {**po_info, **item}
                    all_data.append(combined_data)
            else:
                all_data.append({**po_info, "error": item_blocks.get("error", "Unknown error")})

        # Convert extracted data to a DataFrame
        df = pd.DataFrame(all_data)

        # Display the DataFrame as a table
        st.dataframe(df)

        # Provide a download link for the CSV
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        st.download_button(
            label="Download CSV",
            data=csv_buffer,
            file_name="extracted_data.csv",
            mime="text/csv"
        )
    else:
        st.error("No valid PDF files found in the uploaded files.")