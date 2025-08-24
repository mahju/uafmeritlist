from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import re
import PyPDF2  # add this to your requirements.txt

app = Flask(__name__)

BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_merit_lists():
    response = requests.get(MERIT_LIST_PAGE, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = []

    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                file_link = cols[4].find("a")["href"] if cols[4].find("a") else ""
                if file_link and not file_link.startswith("http"):
                    file_link = BASE_URL + file_link
                data.append({
                    "listno": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "campus": cols[2].get_text(strip=True),
                    "degree": cols[3].get_text(strip=True),
                    "file": file_link
                })
    return data

def search_cnic_in_pdf(pdf_url, cnic_pattern):
    """Download PDF and search for CNIC pattern."""
    try:
        r = requests.get(pdf_url, headers=HEADERS)
        r.raise_for_status()
        reader = PyPDF2.PdfReader(BytesIO(r.content))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""
        if re.search(cnic_pattern, full_text):
            return True
    except Exception as e:
        print(f"Error reading PDF {pdf_url}: {e}")
    return False

@app.route("/")
def home():
    return "UAF Merit List Scraper Running!"

@app.route("/meritlists")
def meritlists():
    data = fetch_merit_lists()
    return jsonify(data)

@app.route("/search")
def search_cnic():
    cnic = request.args.get("cnic", "").strip()
    if not cnic:
        return jsonify({"error": "Provide CNIC as ?cnic=XXXXX"}), 400

    # CNIC pattern with optional dashes
    cnic_regex = re.compile(r"\b" + re.escape(cnic) + r"\b")
    results = []

    merit_lists = fetch_merit_lists()
    for m in merit_lists:
        if m["file"] and search_cnic_in_pdf(m["file"], cnic_regex):
            results.append(m)

    return jsonify({"cnic": cnic, "matches": results})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
