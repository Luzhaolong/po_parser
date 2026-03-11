import streamlit as st
import tempfile
import zipfile
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from helpers.extractor import extract_po_info_ILM, extract_item_blocks_ILM, extract_po_info_Westl

st.set_page_config(page_title="PO Tracking", layout="wide")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("You must be logged in to access this page.")
    st.stop()

# -----------------------------
# CSS for progress bar styling
# -----------------------------
st.markdown(
    """
    <style>
    .po-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        transition: background-color 0.2s ease;
    }
    [data-theme="dark"] .po-card,
    [data-baseweb="dark"] .po-card {
        border-color: #444;
        background-color: #1e1e1e;
    }
    .po-title {
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .po-dates {
        font-size: 0.85rem;
        color: #888;
        margin-bottom: 8px;
    }
    .progress-container {
        background-color: #e0e0e0;
        border-radius: 8px;
        height: 22px;
        width: 100%;
        overflow: hidden;
        position: relative;
    }
    .progress-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.4s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: bold;
        color: white;
        min-width: 40px;
    }
    .progress-green { background: linear-gradient(90deg, #4caf50, #66bb6a); }
    .progress-orange { background: linear-gradient(90deg, #ff9800, #ffb74d); }
    .progress-red { background: linear-gradient(90deg, #f44336, #e57373); }
    .progress-blue { background: linear-gradient(90deg, #2196f3, #64b5f6); }
    .status-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-left: 10px;
    }
    .tag-on-track { background-color: #e8f5e9; color: #2e7d32; }
    .tag-due-soon { background-color: #fff3e0; color: #e65100; }
    .tag-overdue { background-color: #ffebee; color: #c62828; }
    .tag-complete { background-color: #e3f2fd; color: #1565c0; }
    </style>
    """,
    unsafe_allow_html=True
)


def process_files_for_tracking(uploaded_files, parser_type):
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

    all_data = []

    if parser_type == "ILM":
        for pdf_file in pdf_files:
            po_info = extract_po_info_ILM(pdf_file)
            item_blocks = extract_item_blocks_ILM(pdf_file)
            if isinstance(item_blocks, dict) and "error" in item_blocks:
                continue
            if not isinstance(item_blocks, list):
                continue
            for block in item_blocks:
                if not po_info.get("Document Date", ""):
                    continue
                all_data.append({
                    "Document Number": po_info.get("Document Number", ""),
                    "Item_Code": block.get("Item_Code", ""),
                    "PO_issue Date": po_info.get("Document Date", ""),
                    "Delivery Date": block.get("Delivery Date", ""),
                    "Description": block.get("Description", ""),
                })
    else:  # Westell
        for pdf_file in pdf_files:
            rows = extract_po_info_Westl(pdf_file)
            for row in rows:
                all_data.append({
                    "Document Number": row[0],
                    "Item_Code": row[2],
                    "PO_issue Date": row[3],
                    "Delivery Date": row[4],
                    "Description": row[1],
                })

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df = df.dropna(subset=["PO_issue Date"])
    df.drop_duplicates(inplace=True)
    return df


def parse_date(date_str):
    """Try multiple date formats to parse a date string."""
    if not date_str or pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    formats = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def compute_progress(start_date, end_date, today=None):
    """Compute progress percentage between start and end date."""
    if today is None:
        today = datetime.now()
    if not start_date or not end_date:
        return 0, "unknown"
    total_days = (end_date - start_date).days
    if total_days <= 0:
        return 100, "complete"
    elapsed = (today - start_date).days
    if elapsed < 0:
        return 0, "not-started"
    pct = min(100, max(0, int((elapsed / total_days) * 100)))
    if today > end_date:
        return 100, "overdue"
    if pct >= 100:
        return 100, "complete"
    if pct >= 75:
        return pct, "due-soon"
    return pct, "on-track"


def render_progress_card(doc_num, item_code, description, start_str, end_str):
    """Render a single PO tracking card with progress bar."""
    start_dt = parse_date(start_str)
    end_dt = parse_date(end_str)
    pct, status = compute_progress(start_dt, end_dt)

    # Pick color class
    color_map = {
        "on-track": "progress-green",
        "due-soon": "progress-orange",
        "overdue": "progress-red",
        "complete": "progress-blue",
        "not-started": "progress-green",
        "unknown": "progress-green",
    }
    tag_map = {
        "on-track": "tag-on-track",
        "due-soon": "tag-due-soon",
        "overdue": "tag-overdue",
        "complete": "tag-complete",
        "not-started": "tag-on-track",
        "unknown": "tag-on-track",
    }
    label_map = {
        "on-track": "On Track",
        "due-soon": "Due Soon",
        "overdue": "Overdue",
        "complete": "Complete",
        "not-started": "Not Started",
        "unknown": "Unknown",
    }

    color_class = color_map[status]
    tag_class = tag_map[status]
    label = label_map[status]

    title = f"PO {doc_num} - Item {item_code}" if item_code else f"PO {doc_num}"
    start_display = start_str if start_str else "N/A"
    end_display = end_str if end_str else "N/A"
    desc_display = f" | {description}" if description else ""

    # For overdue, show 100% but red
    display_pct = pct if status != "overdue" else 100

    html = f"""
    <div class="po-card">
        <div class="po-title">
            {title}{desc_display}
            <span class="status-tag {tag_class}">{label}</span>
        </div>
        <div class="po-dates">
            Start: {start_display} &nbsp;&nbsp;|&nbsp;&nbsp; Delivery: {end_display}
        </div>
        <div class="progress-container">
            <div class="progress-fill {color_class}" style="width: {display_pct}%;">
                {pct}%
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def main():
    st.markdown(
        "<h2 style='text-align: center;'>PO Tracking Dashboard</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<h4 style='text-align: center; color: #888;'>Upload PO files to visualize delivery progress</h4>",
        unsafe_allow_html=True
    )
    st.write("---")

    # Parser selection
    parser_type = st.radio(
        "Select PO format",
        ["ILM", "Westell"],
        horizontal=True
    )

    uploaded_files = st.file_uploader(
        "Upload PDF(s) or ZIP containing PDFs",
        type=["pdf", "zip"],
        accept_multiple_files=True,
        key="tracking_uploader"
    )

    if not uploaded_files:
        st.info("Upload PO PDF(s) or ZIP to start tracking.")
        return

    df = process_files_for_tracking(uploaded_files, parser_type)

    if df.empty:
        st.warning("No PO data could be extracted from the uploaded files.")
        return

    st.success(f"Extracted {len(df)} line item(s) from PO files.")

    # Sidebar filters
    st.sidebar.header("Filter Tracking")

    # Filter by PO number
    po_numbers = sorted(df["Document Number"].unique())
    selected_pos = st.sidebar.multiselect(
        "Filter by PO Number",
        options=po_numbers,
        default=po_numbers
    )

    # Filter by status
    status_filter = st.sidebar.multiselect(
        "Filter by Status",
        options=["On Track", "Due Soon", "Overdue", "Complete", "Not Started"],
        default=["On Track", "Due Soon", "Overdue", "Complete", "Not Started"]
    )

    status_label_map = {
        "On Track": "on-track",
        "Due Soon": "due-soon",
        "Overdue": "overdue",
        "Complete": "complete",
        "Not Started": "not-started",
    }

    # Sort option
    sort_by = st.sidebar.selectbox(
        "Sort by",
        ["Delivery Date (earliest first)", "Delivery Date (latest first)", "PO Number"]
    )

    # Apply PO filter
    filtered_df = df[df["Document Number"].isin(selected_pos)].copy()

    # Compute status for each row for filtering
    filtered_df["_status"] = filtered_df.apply(
        lambda r: compute_progress(parse_date(r["PO_issue Date"]), parse_date(r["Delivery Date"]))[1],
        axis=1
    )
    selected_statuses = [status_label_map[s] for s in status_filter]
    filtered_df = filtered_df[filtered_df["_status"].isin(selected_statuses)]

    # Sort
    if sort_by == "Delivery Date (earliest first)":
        filtered_df["_sort_date"] = filtered_df["Delivery Date"].apply(lambda x: parse_date(x) or datetime.max)
        filtered_df = filtered_df.sort_values("_sort_date")
    elif sort_by == "Delivery Date (latest first)":
        filtered_df["_sort_date"] = filtered_df["Delivery Date"].apply(lambda x: parse_date(x) or datetime.min)
        filtered_df = filtered_df.sort_values("_sort_date", ascending=False)
    else:
        filtered_df = filtered_df.sort_values("Document Number")

    # Summary metrics
    total = len(filtered_df)
    overdue_count = len(filtered_df[filtered_df["_status"] == "overdue"])
    due_soon_count = len(filtered_df[filtered_df["_status"] == "due-soon"])
    on_track_count = len(filtered_df[filtered_df["_status"] == "on-track"])
    complete_count = len(filtered_df[filtered_df["_status"] == "complete"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Items", total)
    col2.metric("On Track", on_track_count)
    col3.metric("Due Soon", due_soon_count)
    col4.metric("Overdue", overdue_count)
    col5.metric("Complete", complete_count)

    st.write("---")

    # Render progress cards
    for _, row in filtered_df.iterrows():
        render_progress_card(
            row["Document Number"],
            row.get("Item_Code", ""),
            row.get("Description", ""),
            row.get("PO_issue Date", ""),
            row.get("Delivery Date", ""),
        )

    if filtered_df.empty:
        st.info("No PO items match the current filters.")


if __name__ == "__main__":
    main()
