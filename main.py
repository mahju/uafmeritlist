from flask import Flask, jsonify, request, render_template, render_template_string
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pdfplumber

app = Flask(__name__)

# -------- Settings --------
BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MeritListBot/1.0)"}

# Limit how many PDFs to scan per request to avoid timeouts on free hosting
MAX_PDFS = 2  # Reduced to only scan 2 PDFs
MAX_MATCHES = 2  # Reduced to stop after 2 matches
REQ_TIMEOUT = 15  # Reduced timeout

# Simple cache for search results (optional)
search_cache = {}

def fetch_merit_lists():
    """
    Scrape the UAF page and return a list of dicts:
    {listno, title, campus, degree, file}
    """
    try:
        resp = requests.get(MERIT_LIST_PAGE, headers=HEADERS, timeout=REQ_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        data = []
        table = soup.find("table")
        if not table:
            return data

        for row in table.find_all("tr")[1:]:  # skip header
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            file_link = ""
            a = cols[4].find("a")
            if a and a.get("href"):
                href = a["href"].strip()
                # Normalize to absolute URL
                if href.startswith("http"):
                    file_link = href
                else:
                    file_link = BASE_URL.rstrip("/") + "/" + href.lstrip("/")

            data.append(
                {
                    "listno": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "campus": cols[2].get_text(strip=True),
                    "degree": cols[3].get_text(strip=True),
                    "file": file_link,
                }
            )
        return data

    except Exception as e:
        print(f"[Error] fetch_merit_lists failed: {e}")
        return []


def search_in_pdf(pdf_url: str, cnic: str):
    """
    Open the PDF and search for the CNIC:
    - Scan tables (all cells)
    - Scan page text
    Returns dict with 'row' and 'columns' if found, else None.
    """
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=REQ_TIMEOUT)
        r.raise_for_status()

        with pdfplumber.open(BytesIO(r.content)) as pdf:
            for page in pdf.pages:
                # 1) Search tables
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []

                for table in tables:
                    for row in table or []:
                        if not row:
                            continue
                        # Check every cell for CNIC digits
                        for cell in row:
                            cell_text = (cell or "").strip()
                            if not cell_text:
                                continue
                            if cnic in "".join(ch for ch in cell_text if ch.isdigit()):
                                return {
                                    "row": " | ".join((c or "").strip() for c in row),
                                    "columns": [(c or "").strip() for c in row],
                                }

                # 2) Search full text (fallback)
                text = page.extract_text() or ""
                if cnic in "".join(ch for ch in text if ch.isdigit()):
                    # Provide a small snippet line that contains the CNIC
                    for line in text.split("\n"):
                        if cnic in "".join(ch for ch in line if ch.isdigit()):
                            return {
                                "row": line.strip(),
                                "columns": line.split(),
                            }
        return None

    except Exception as e:
        print(f"[Warn] search_in_pdf failed for {pdf_url}: {e}")
        return None


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search_cnic():
    try:
        cnic = (request.form.get("cnic") or "").strip()
        if not cnic:
            return render_template("index.html", error="Please enter CNIC.")

        if not cnic.isdigit():
            return render_template("index.html", error="CNIC must be digits only (no dashes).")

        print(f"Starting search for CNIC: {cnic}")
        
        lists = fetch_merit_lists()
        if not lists:
            print("No merit lists found")
            return render_template("results.html", cnic=cnic, results=[])

        print(f"Found {len(lists)} merit lists")
        results = []
        scanned = 0

        for entry in lists:
            if scanned >= MAX_PDFS:
                print(f"Reached MAX_PDFS limit ({MAX_PDFS})")
                break

            if not entry.get("file"):
                continue

            print(f"Scanning PDF {scanned + 1}: {entry['file']}")
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
                print(f"Found match in: {entry['title']}")
                if len(results) >= MAX_MATCHES:
                    print(f"Reached MAX_MATCHES limit ({MAX_MATCHES})")
                    break

        print(f"Search completed. Found {len(results)} matches")
        return render_template("results.html", cnic=cnic, results=results)

    except Exception as e:
        print(f"Critical error in search_cnic: {str(e)}")
        return render_template("index.html", error=f"Internal server error: {str(e)}")


# Debug/verification endpoints
@app.route("/all_links", methods=["GET"])
def all_links():
    data = fetch_merit_lists()
    return jsonify(data)


@app.route("/view_links", methods=["GET"])
def view_links():
    data = fetch_merit_lists()
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>All Merit List Links</title></head>
    <body>
        <h1>All Merit List Entries</h1>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr>
                <th>List No</th>
                <th>Title</th>
                <th>Campus</th>
                <th>Degree</th>
                <th>PDF Link</th>
            </tr>
            {% for d in data %}
            <tr>
                <td>{{ d.listno }}</td>
                <td>{{ d.title }}</td>
                <td>{{ d.campus }}</td>
                <td>{{ d.degree }}</td>
                <td>{% if d.file %}<a href="{{ d.file }}" target="_blank">PDF</a>{% else %}N/A{% endif %}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_content, data=data)


@app.route("/debug", methods=["GET"])
def debug():
    """Simple debug endpoint to test basic functionality"""
    try:
        # Test basic imports
        import flask, requests, bs4, pdfplumber
        return jsonify({
            "status": "ok",
            "imports": "successful",
            "max_pdfs": MAX_PDFS,
            "max_matches": MAX_MATCHES,
            "timeout": REQ_TIMEOUT
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
