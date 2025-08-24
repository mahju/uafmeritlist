from flask import Flask, jsonify, request, render_template, render_template_string
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pdfplumber
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# -------- Settings --------
BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MeritListBot/1.0)"}

MAX_PDFS = 1
MAX_MATCHES = 1
REQ_TIMEOUT = 10

def fetch_merit_lists():
    """Fetch merit lists from UAF website - MEMORY EFFICIENT VERSION"""
    try:
        logger.info(f"Fetching merit lists from: {MERIT_LIST_PAGE}")
        resp = requests.get(MERIT_LIST_PAGE, headers=HEADERS, timeout=REQ_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        data = []
        table = soup.find("table")
        if not table:
            return data
        
        # Only get the first few entries to save memory - MAX 5 ROWS
        for row in list(table.find_all("tr")[1:])[:5]:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
            file_link = ""
            a = cols[4].find("a")
            if a and a.get("href"):
                href = a["href"].strip()
                if href.startswith("http"):
                    file_link = href
                else:
                    file_link = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            data.append({
                "listno": cols[0].get_text(strip=True),
                "title": cols[1].get_text(strip=True),
                "campus": cols[2].get_text(strip=True),
                "degree": cols[3].get_text(strip=True),
                "file": file_link,
            })
        return data
    except Exception as e:
        logger.error(f"fetch_merit_lists failed: {e}")
        return []

def search_in_pdf(pdf_url: str, cnic: str):
    """Search for CNIC in PDF - WITH TABLES & MORE PAGES"""
    try:
        # Stream the PDF instead of loading it all into memory
        logger.info(f"Streaming PDF: {pdf_url}")
        with requests.get(pdf_url, headers=HEADERS, timeout=REQ_TIMEOUT, stream=True) as r:
            r.raise_for_status()
            content = BytesIO()
            for chunk in r.iter_content(chunk_size=8192):  # Stream in 8KB chunks
                if chunk:
                    content.write(chunk)
        
        # Search first 5 pages with table support
        with pdfplumber.open(content) as pdf:
            for page_num, page in enumerate(pdf.pages[:5]):  # FIRST 5 PAGES
                logger.info(f"Scanning page {page_num + 1}")
                
                # 1. SEARCH TABLES FIRST (where CNIC usually is)
                try:
                    tables = page.extract_tables() or []
                    for table_num, table in enumerate(tables):
                        for row_num, row in enumerate(table):
                            if not row:
                                continue
                            # Check every cell for CNIC
                            for cell in row:
                                cell_text = (cell or "").strip()
                                if not cell_text:
                                    continue
                                # Remove non-digits and search
                                cell_digits = "".join(ch for ch in cell_text if ch.isdigit())
                                if cnic in cell_digits:
                                    logger.info(f"CNIC found in table {table_num}, row {row_num}")
                                    return {
                                        "row": " | ".join((c or "").strip() for c in row),
                                        "columns": [(c or "").strip() for c in row],
                                    }
                except Exception as e:
                    logger.warning(f"Error extracting tables from page {page_num + 1}: {e}")
                
                # 2. SEARCH TEXT (fallback)
                text = page.extract_text() or ""
                clean_text = "".join(ch for ch in text if ch.isdigit())
                if cnic in clean_text:
                    # Find the line containing CNIC
                    for line in text.split("\n"):
                        line_clean = "".join(ch for ch in line if ch.isdigit())
                        if cnic in line_clean:
                            logger.info(f"CNIC found in text on page {page_num + 1}")
                            return {
                                "row": line.strip(),
                                "columns": line.split(),
                            }
        
        # Only return None if no match found in any page
        logger.info(f"No CNIC {cnic} found in PDF")
        return None
        
    except Exception as e:
        logger.error(f"search_in_pdf failed for {pdf_url}: {e}")
        return None
@app.route("/search", methods=["POST"])
def search_cnic():
    try:
        cnic = (request.form.get("cnic") or "").strip()
        if not cnic:
            return render_template("index.html", error="Please enter CNIC.")
        if not cnic.isdigit():
            return render_template("index.html", error="CNIC must be digits only (no dashes).")
        
        lists = fetch_merit_lists()
        if not lists:
            return render_template("results.html", cnic=cnic, results=[])
        
        results = []
        scanned = 0
        for entry in lists:
            if scanned >= MAX_PDFS:
                break
            if not entry.get("file"):
                continue
            match = search_in_pdf(entry["file"], cnic)
            scanned += 1
            if match:
                results.append({
                    "list": entry["title"],
                    "url": entry["file"],
                    "row": match.get("row", ""),
                    "columns": match.get("columns", []),
                    "listno": entry.get("listno", ""),
                    "campus": entry.get("campus", ""),
                    "degree": entry.get("degree", ""),
                })
                if len(results) >= MAX_MATCHES:
                    break
        return render_template("results.html", cnic=cnic, results=results)
    except Exception as e:
        return render_template("index.html", error=f"Error: {str(e)}")

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




