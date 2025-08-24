from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
from urllib.parse import urljoin

app = Flask(__name__)

BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = f"{BASE_URL}/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Scrape merit list table
def fetch_meritlists():
    response = requests.get(MERIT_LIST_PAGE, headers=HEADERS)
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
                    file_link = urljoin(BASE_URL, file_link)
                data.append({
                    "listno": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "campus": cols[2].get_text(strip=True),
                    "degree": cols[3].get_text(strip=True),
                    "file": file_link
                })
    return data

@app.route('/')
def home():
    return "UAF Merit List Scraper Running!"

@app.route('/meritlists')
def meritlists():
    return jsonify(fetch_meritlists())

# New route: search by CNIC
@app.route('/search')
def search_cnic():
    cnic = request.args.get("cnic")
    if not cnic:
        return jsonify({"error": "Please provide CNIC as query parameter"}), 400

    results = []
    lists = fetch_meritlists()

    for item in lists:
        file_url = item.get("file")
        if not file_url:
            continue

        try:
            # Fetch PDF
            pdf_resp = requests.get(file_url, headers=HEADERS)
            pdf_resp.raise_for_status()

            # Read PDF text
            with pdfplumber.open(BytesIO(pdf_resp.content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and cnic in text:
                        results.append({
                            "listno": item.get("listno"),
                            "title": item.get("title"),
                            "campus": item.get("campus"),
                            "degree": item.get("degree"),
                            "file": file_url
                        })
                        break  # stop after first match in this PDF

        except Exception as e:
            # Skip if PDF fails
            continue

    return jsonify({"cnic": cnic, "matches": results})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
