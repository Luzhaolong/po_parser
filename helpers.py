import fitz  # PyMuPDF
import re
import zipfile
import os
import shutil
import tempfile
#from google.colab import files
import pandas as pd

def extract_po_info(pdf_path):
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

        doc_number_match = re.search(r"\bPO\d+\b", full_text)
        document_number = doc_number_match.group(0) if doc_number_match else ""

        reference_match = re.search(r"Your Reference\s+([\w\-\/]*)", full_text)
        reference = reference_match.group(1).strip() if reference_match else ""
        if reference.lower() == "your":
            reference = ""

        payment_match = re.search(r"Payment Term:\s*(.+)", full_text)
        payment_term = payment_match.group(1).strip() if payment_match else ""

        return {
            "Document Number": document_number,
            "Reference": reference,
            "Payment Term": payment_term,
        }

    except Exception as e:
        return {"error": str(e)}


def extract_item_blocks(pdf_path):
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

        # Remove commas in numbers
        full_text = re.sub(r'(?<=\d),(?=\d)', '', full_text)
        lines = full_text.splitlines()
        stop_marker = "▌Tax Details"

        inside_table = False
        blocks = []
        current_block = []
        waiting_for_date = False

        prev_line = ""  # for multi-line start marker
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
                    data = parse_block(current_block)
                    blocks.append(data)
                    current_block = []
                    waiting_for_date = False

        if not start_marker_found:
            return {"error": f"❌ '{os.path.basename(pdf_path)}' cannot convert to CSV, maybe format mismatch."}

        return blocks
    except Exception as e:
        return {"error": str(e)}


def parse_block(block_lines):
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
    except:
        data["Quantity"] = ""

    # Detect UoM
    for line in block_lines:
        if line.strip() == "Each":
            data["UoM(optional)"] = "Each"
            break

    # Description
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

    # Item Details
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
        except:
            data["Item Details"] = line_strip
            break

    return data

