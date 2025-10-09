# extractor.py
import fitz  # PyMuPDF
import re
import zipfile
import os
import shutil
import pandas as pd
from pathlib import Path

# -----------------------------
# Helper: clean_description
# -----------------------------
def clean_description(desc: str) -> str:
    """
    Trim and remove repeated prefix/suffix patterns.
    If the start and end repeated and the middle contains 'Each' or floats,
    prefer the longer repeated substring.
    """
    desc = (desc or "").strip()
    if not desc:
        return ""
    words = desc.split()
    # Check for repeated substring (try longer first)
    for length in range(len(words)//2, 0, -1):
        start_sub = " ".join(words[:length])
        end_sub = " ".join(words[-length:])
        if start_sub.lower() == end_sub.lower():
            middle = " ".join(words[length:-length])
            if re.search(r'\bEach\b', middle, flags=re.IGNORECASE) or re.search(r'\d+\.\d+', middle):
                return max(start_sub, end_sub, key=len).strip()
    return desc

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
    """
    Extract item details from PDF table blocks.
    This looks for a start marker like 'Tax %'/'Tax%Tax%' to identify table area,
    collects blocks until a stop marker, then parses by Delivery Date grouping.
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_blocks = page.get_text("blocks")
            text_blocks.sort(key=lambda block: (block[1], block[0]))
            for block in text_blocks:
                full_text += (block[4] or "") + "\n"
        doc.close()

        # Normalize numbers (remove thousands separators)
        full_text = re.sub(r'(?<=\d),(?=\d)', '', full_text)
        lines = full_text.splitlines()
        stop_marker = "▌Tax Details"

        inside_table = False
        blocks = []
        current_block = []
        waiting_for_date = False
        prev_line = ""  # carry previous line to detect split 'Tax %' markers
        start_marker_found = False

        for line in lines:
            line_strip = line.strip()

            # --------------------
            # Find start marker (handles 'Tax %' split across lines)
            # --------------------
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

            # --------------------
            # Stop marker
            # --------------------
            if line_strip.startswith(stop_marker):
                inside_table = False
                continue

            # --------------------
            # Collect block lines
            # --------------------
            current_block.append(line_strip)

            if line_strip.startswith("Delivery Date:"):
                waiting_for_date = True
                continue

            if waiting_for_date:
                # expecting a date like d/m/yyyy or dd/mm/yyyy
                if re.match(r"\d{1,2}/\d{1,2}/\d{4}", line_strip):
                    # attach the date line
                    current_block.append(line_strip)
                    # If block contains 'page' (page footer/header), skip and reset
                    if any(re.search(r'page', l, re.IGNORECASE) for l in current_block):
                        current_block = []
                        waiting_for_date = False
                        inside_table = False
                        prev_line = ""
                        continue
                    # Otherwise parse this block
                    data = parse_block(current_block)
                    blocks.append(data)
                    current_block = []
                    waiting_for_date = False

        if not start_marker_found:
            return {"error": f"❌ '{os.path.basename(pdf_path)}' cannot convert to CSV, maybe format mismatch."}

        return blocks

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# Parse one item block
# -----------------------------
def parse_block(block_lines: list) -> dict:
    """
    Parse an individual item block (list of stripped lines) and return a dictionary.
    """
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

    # Delivery Date (line after 'Delivery Date:')
    for i, line in enumerate(block_lines):
        if line.startswith("Delivery Date:") and i + 1 < len(block_lines):
            data["Delivery Date"] = block_lines[i+1].strip()
            break

    # Item Code (line after 'Item Code:')
    item_code_index = -1
    for i, line in enumerate(block_lines):
        if line.startswith("Item Code:") and i + 1 < len(block_lines):
            data["Item_Code"] = block_lines[i+1].strip()
            item_code_index = i + 1
            break

    # Price & Total: find float-like lines (e.g., 123.45), exclude "0.0000"
    float_lines = [ln for ln in block_lines if re.match(r"^\d+\.\d+$", ln) and ln != "0.0000"]
    if float_lines:
        data["Price"] = float_lines[0]
        # Total is the maximum numeric value
        try:
            data["Total"] = max(float_lines, key=lambda x: float(x))
        except Exception:
            data["Total"] = float_lines[-1]

    # Quantity calculation
    try:
        if data["Price"] and data["Total"]:
            qty = float(data["Total"]) / float(data["Price"])
            data["Quantity"] = str(round(qty, 4))
    except Exception:
        data["Quantity"] = ""

    # Detect UoM
    for ln in block_lines:
        if ln == "Each":
            data["UoM(optional)"] = "Each"
            break

    # Item Details: look for lines starting with Rev/REV
    rev_index = -1
    for i, ln in enumerate(block_lines):
        if re.match(r"^(Rev|REV)\s+\w+", ln):
            data["Item Details"] = ln
            rev_index = i
            break

    # Description: try to locate slice between detected indices
    if item_code_index != -1:
        if rev_index != -1:
            desc_lines = block_lines[rev_index+1:item_code_index]
        else:
            # find nearest integer-only line before item_code_index (like an index)
            int_index = -1
            for j in range(item_code_index-1, -1, -1):
                if re.match(r"^\d+$", block_lines[j].strip()):
                    int_index = j
                    break
            if int_index != -1:
                desc_lines = block_lines[int_index+1:item_code_index]
            else:
                desc_lines = block_lines[:item_code_index]

        # Remove 'Item Code:' if present and empty lines
        desc_lines = [l for l in desc_lines if not l.strip().startswith("Item Code:") and l.strip()]
        combined_desc = " ".join(desc_lines).strip()
        data["Description"] = clean_description(combined_desc)

    return data


# -----------------------------
# Function to extract required info
# -----------------------------
def extract_po_info_Westl(pdf_path):
    rows = []
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

        ##print(full_text)

        lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # -------------------
        # Document Number
        # -------------------
        first_int = None
        for token in re.findall(r"\d+", full_text):
            first_int = token
            break
        document_number = f"PO{first_int}" if first_int else ""

        # -------------------
        # Header info: PO Issue Date, Payment Term, Ship Via, FOB
        # -------------------
        po_issue_date, payment_term, ship_via, fob = "", "", "", ""
        for i, line in enumerate(lines):
            if not po_issue_date and re.search(r"\d{1,2}/\d{1,2}/\d{4}", line):
                po_issue_date = re.search(r"\d{1,2}/\d{1,2}/\d{4}", line).group(0)

            net_match = re.search(r"(Net\s*\d+)", line, re.IGNORECASE)
            if net_match:
                payment_term = net_match.group(1)
                fob_part = line[:net_match.start()].strip()
                fob = fob_part if fob_part else ""

                if i-1 >= 0:
                    upper_line = lines[i-1].strip()
                    if not re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", upper_line) \
                       and not re.match(r"^\d+", upper_line) \
                       and not re.search(r"Net\s*\d+", upper_line, re.IGNORECASE):
                        ship_via = upper_line
                break

        # -------------------
        # Buyer, REQ# and Requisitioner
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

                if re.match(r"^\d+$", candidate_buyer):
                    buyer = candidate_buyer
                else:
                    buyer = ""
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
            qty_index = None

            # --- Find Quantity & UoM ---
            for i, l in enumerate(clean_blk):
                if l in used_lines:
                    continue
                m = re.match(r"^(\d+)\s+(\w+)?", l)
                if m:
                    qty = m.group(1)
                    uom = m.group(2) if m.group(2) else ""
                    qty_index = i
                    used_lines.add(l)
                    break

            # --- Capture any lines between item_code and quantity ---
            pre_desc_part = ""
            if qty_index is not None and qty_index > 1:
                between_lines = clean_blk[1:qty_index]
                if between_lines:
                    pre_desc_part = " ".join(between_lines).strip()

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

            # --- Merge pre-quantity lines (if any) ---
            if pre_desc_part:
                desc = f"{pre_desc_part} {desc}".strip()

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