# extractor.py
import fitz  # PyMuPDF
import re
import zipfile
import os
import shutil
import pandas as pd
from pathlib import Path


# -----------------------------
# Functions
# -----------------------------
def extract_po_info_ILM(pdf_path: str) -> dict:
    """Extract purchase order header info from a single PDF."""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_blocks = page.get_text("blocks")
            # sort by y (top) then x (left) for deterministic ordering
            text_blocks.sort(key=lambda block: (block[1], block[0]))
            for block in text_blocks:
                full_text += (block[4] or "") + "\n"
        doc.close()

        # Document Number (e.g., PO12345)
        doc_number_match = re.search(r"\bPO\d+\b", full_text, flags=re.IGNORECASE)
        document_number = doc_number_match.group(0) if doc_number_match else ""

        # Reference
        reference_match = re.search(r"Your Reference\s+([\w\-\./]*)", full_text, flags=re.IGNORECASE)
        reference = reference_match.group(1).strip() if reference_match else ""
        if reference.lower() == "your":
            reference = ""

        # Payment Term
        payment_match = re.search(r"Payment Term:\s*(.+)", full_text, flags=re.IGNORECASE)
        payment_term = payment_match.group(1).strip() if payment_match else ""

        # Document Date (first occurrence of dd/mm/yyyy)
        doc_date_match = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", full_text)
        document_date = doc_date_match.group(0) if doc_date_match else ""

        return {
            "Document Number": document_number,
            "Reference": reference,
            "Payment Term": payment_term,
            "Document Date": document_date,
        }

    except Exception as e:
        return {"error": str(e)}



def extract_item_blocks_ILM(pdf_path: str):
    """Extract item details from PDF table blocks."""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda block: (block[1], block[0]))
            for block in text_blocks:
                full_text += block[4] + "\n"
        doc.close()

        # Remove commas in numbers (e.g., 1,000 → 1000)
        full_text = re.sub(r'(?<=\d),(?=\d)', '', full_text)
        lines = full_text.splitlines()
        stop_marker = "▌Tax Details"

        inside_table = False
        blocks = []
        current_block = []
        waiting_for_date = False
        prev_line = ""
        start_marker_found = False

        for line in lines:
            line_strip = line.strip()

            if not inside_table:
                combined = (prev_line + line_strip).replace(" ", "")
                if combined == "Tax%Tax%":
                    inside_table = True
                    prev_line = ""
                    start_marker_found = True
                    continue
                if line_strip == "Tax %":
                    prev_line = line_strip
                    continue
                prev_line = line_strip
                continue

            if line_strip.startswith(stop_marker):
                break

            current_block.append(line)

            if line_strip.startswith("Delivery Date:"):
                waiting_for_date = True
                continue

            if waiting_for_date:
                if re.match(r"\d{1,2}/\d{1,2}/\d{4}", line_strip):
                    current_block.append(line_strip)
                    blocks.append(parse_block(current_block))
                    current_block = []
                    waiting_for_date = False

        if not start_marker_found:
            return {"error": f"❌ '{os.path.basename(pdf_path)}' cannot convert to CSV, maybe format mismatch."}

        return blocks
    except Exception as e:
        return {"error": str(e)}


def parse_block(block_lines: list) -> dict:
    """Parse individual block of item details."""
    data = {
        "Item_Code": "",
        "Delivery Date": "",
        "Description": "",
        "Item Details": "",
        "UoM(optional)": "",
        "Quantity": "",
        "Price": "",
        "Total": ""
    }

    # Delivery Date
    for i, line in enumerate(block_lines):
        if line.strip().startswith("Delivery Date:") and i + 1 < len(block_lines):
            data["Delivery Date"] = block_lines[i+1].strip()
            break

    # Item Code
    for i, line in enumerate(block_lines):
        if line.strip().startswith("Item Code:") and i + 1 < len(block_lines):
            data["Item_Code"] = block_lines[i+1].strip()
            break

    # Price & Total
    float_lines = [line.strip() for line in block_lines if re.match(r"^\d+\.\d+$", line.strip()) and line.strip() != "0.0000"]
    if float_lines:
        data["Price"] = float_lines[0]
        data["Total"] = max(float_lines, key=lambda x: float(x))

    # Quantity
    try:
        if data["Price"] and data["Total"]:
            data["Quantity"] = str(round(float(data["Total"]) / float(data["Price"]), 4))
    except ZeroDivisionError:
        data["Quantity"] = ""

    # Detect UoM
    for line in block_lines:
        if line.strip() == "Each":
            data["UoM(optional)"] = "Each"
            break

    # Description & Item Details
    candidates = []
    ignore_patterns = [r"^\d+\.\d+$", r"^Each$", r"Delivery Date:", r"Item Code:"]
    for line in block_lines:
        line_strip = line.strip()
        if not any(re.match(p, line_strip) for p in ignore_patterns) and line_strip not in [data["Price"], data["Total"], data["Delivery Date"], data["Item_Code"]]:
            candidates.append(line_strip)

    seen = {}
    duplicates = []
    for line in candidates:
        if line in seen:
            duplicates.append(line)
        else:
            seen[line] = 1

    data["Description"] = " ".join(duplicates).strip()

    for line in block_lines:
        line_strip = line.strip()
        if line_strip in [data["Price"], data["Total"], data["Quantity"], data["Delivery Date"], "Each", data["Item_Code"]]:
            continue
        if line_strip.startswith(("Delivery Date:", "Item Code:")):
            continue
        if line_strip in duplicates:
            continue
        try:
            float(line_strip)
            continue
        except ValueError:
            data["Item Details"] = line_strip
            break

    return data


# -----------------------------
# Function to extract required info
# -----------------------------
def extract_po_info_Westl(pdf_path: str) -> list:
    rows = []
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            for b in blocks:
                full_text += b[4] + "\n"
        doc.close()

        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # -------------------
        # Document Number
        # -------------------
        first_int = re.search(r"\d+", full_text)
        document_number = f"PO{first_int.group(0)}" if first_int else ""

        # -------------------
        # Header info
        # -------------------
        po_issue_date, payment_term, ship_via, fob = "", "", "", ""
        for i, line in enumerate(lines):
            if not po_issue_date and re.search(r"\d{1,2}/\d{1,2}/\d{4}", line):
                po_issue_date = re.search(r"\d{1,2}/\d{1,2}/\d{4}", line).group(0)

            net_match = re.search(r"(Net\s*\d+)", line, re.IGNORECASE)
            if net_match:
                payment_term = net_match.group(1)
                fob = line[:net_match.start()].strip()
                if i-1 >= 0:
                    upper_line = lines[i-1].strip()
                    if not re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", upper_line) \
                       and not re.match(r"^\d+$", upper_line):
                        ship_via = upper_line
                break

        # -------------------
        # Buyer, REQ# and Requisitioner (dynamic logic)
        # -------------------
        buyer, req_num, requisitioner = "", "", ""
        for i, line in enumerate(lines):
            if line.strip().upper() == "ITEM":
                # Requisitioner: 1 line above ITEM
                candidate_req_name = lines[i-1].strip() if i-1 >= 0 else ""
                if candidate_req_name and not re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", candidate_req_name) \
                   and not re.match(r"^\d+$", candidate_req_name) \
                   and not re.search(r"Net\s*\d+", candidate_req_name, re.IGNORECASE):
                    requisitioner = candidate_req_name
                else:
                    requisitioner = ""

                # REQ#: 2 lines above ITEM
                candidate_req = lines[i-2].strip() if i-2 >= 0 else ""
                if re.match(r"^\d+$", candidate_req):
                    req_num = candidate_req
                else:
                    req_num = ""

                # Buyer: dynamic based on other fields
                if requisitioner == "" and req_num == "":
                    candidate_buyer = lines[i-1].strip() if i-1 >= 0 else ""  # 1 line above
                elif requisitioner == "":
                    candidate_buyer = lines[i-2].strip() if i-2 >= 0 else ""  # 2 lines above
                else:
                    candidate_buyer = lines[i-3].strip() if i-3 >= 0 else ""  # 3 lines above

                buyer = candidate_buyer if re.match(r"^\d+$", candidate_buyer) else ""
                break

        # -------------------
        # Parse line-item blocks
        # -------------------
        blocks = []
        in_block_section = False
        current_block = []
        skip_header = False

        for i, line in enumerate(lines):
            if not in_block_section:
                if i < len(lines)-1 and lines[i] == "Unit Cost" and lines[i+1] == "Extended Cost":
                    in_block_section = True
                    skip_header = True
                continue

            if skip_header and line == "Extended Cost":
                skip_header = False
                continue

            if line.strip().upper() == "TOTAL":
                if current_block:
                    blocks.append(current_block)
                break

            if re.match(r"^\d+$", line):
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                current_block.append(line)
            else:
                current_block.append(line)

        if not blocks:
            print(f"⚠️ No rows can be extracted from '{os.path.basename(pdf_path)}' – no blocks found.")
            return []

        # -------------------
        # Extract rows per block
        # -------------------
        for blk in blocks:
            clean_blk = [re.sub(r",", "", l) for l in blk]
            used_lines = set()

            item_code = clean_blk[0] if clean_blk else ""
            used_lines.add(item_code)

            qty, uom = "", ""
            for l in clean_blk:
                if l in used_lines:
                    continue
                m = re.match(r"^(\d+)\s+(\w+)?", l)
                if m:
                    qty = m.group(1)
                    uom = m.group(2) if m.group(2) else ""
                    used_lines.add(l)
                    break

            floats = []
            for l in clean_blk:
                if l in used_lines:
                    continue
                floats += re.findall(r"\d+\.\d+", l)
            price = floats[0] if floats else ""
            total = floats[-1] if floats else ""

            delivery_date = ""
            for l in clean_blk:
                if l in used_lines:
                    continue
                date_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", l)
                if date_match:
                    delivery_date = date_match.group(0)
                    used_lines.add(l)
                    break

            desc = ""
            usd_idx = None
            for i, l in enumerate(clean_blk):
                if l in used_lines:
                    continue
                if "USD" in l.upper():
                    usd_idx = i
                    used_lines.add(l)
                    break
            if usd_idx is not None and usd_idx + 1 < len(clean_blk):
                desc = " ".join(clean_blk[usd_idx+1:]).strip()
            elif usd_idx is None:
                desc = " ".join(clean_blk[1:]).strip()

            row = {
                "Document Number": document_number,
                "Part/Description": desc,
                "Item_Code": item_code,
                "PO_issue Date": po_issue_date,
                "Delivery Date": delivery_date,
                "SHIP VIA": ship_via,
                "FOB": fob,
                "UoM(optional)": uom,
                "Quantity": qty,
                "Price": price,
                "Total": total,
                "Payment Term": payment_term,
                "BUYER": buyer,
                "REQ#": req_num,
                "REQUISITIONER": requisitioner
            }
            rows.append(row)

    except Exception as e:
        print(f"❌ Error in {pdf_path}: {e}")
    return rows

# -----------------------------
# Main script
# -----------------------------
def main():
    input_pdf_folder = Path("input_pdf_folder")
    output_dir = Path("output")

    # Reset folders
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = []
    for root, _, files_in_dir in os.walk(input_pdf_folder):
        for f in files_in_dir:
            if f.lower().endswith(".pdf") and not f.startswith("._") and "__MACOSX" not in root:
                pdf_files.append(os.path.join(root, f))

    all_data = []
    for pdf_file in pdf_files:
        po_info = extract_po_info(pdf_file)
        item_blocks = extract_item_blocks(pdf_file)

        if isinstance(item_blocks, dict) and "error" in item_blocks:
            print(item_blocks["error"])
            continue
        elif not isinstance(item_blocks, list):
            continue

        for block in item_blocks:
            if not po_info.get("Document Date", ""):
                continue

            row = {
                "Document Number": po_info.get("Document Number", ""),
                "Reference": po_info.get("Reference", ""),
                "Item_Code": block.get("Item_Code", ""),
                "PO_issue Date": po_info.get("Document Date", ""),
                "Delivery Date": block.get("Delivery Date", ""),
                "Description": block.get("Description", ""),
                "Item Details": block.get("Item Details", ""),
                "UoM(optional)": block.get("UoM(optional)", ""),
                "Quantity": block.get("Quantity", ""),
                "Price": block.get("Price", ""),
                "Total": block.get("Total", ""),
                "Payment Term": po_info.get("Payment Term", "")
            }
            all_data.append(row)

    if all_data:
        df = pd.DataFrame(all_data)
        expected_cols = [
            "Document Number","Reference","Item_Code",
            "PO_issue Date","Delivery Date",
            "Description","Item Details","UoM(optional)",
            "Quantity","Price","Total","Payment Term"
        ]
        df = df.dropna(subset=["PO_issue Date"])
        existing_cols = [c for c in expected_cols if c in df.columns]
        df = df[existing_cols]

        if "Document Number" in df.columns:
            df["Document Number Sort"] = df["Document Number"].str.extract(r"(\d+)").astype(int)
            df = df.sort_values(by="Document Number Sort").drop(columns=["Document Number Sort"])

        out_file = output_dir / "Extracted.csv"
        df.to_csv(out_file, index=False)
        print(f"✅ Extraction complete → {out_file}")
    else:
        print("⚠️ No data extracted.")


if __name__ == "__main__":
    main()