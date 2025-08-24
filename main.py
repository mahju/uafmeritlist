from flask import Flask, jsonify, request, render_template_string
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import PyPDF2

app = Flask(__name__)

BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_merit_lists():
    """Fetch all merit list entries from the UAF merit list page."""
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

def search_cnic_in_pdf(pdf_url, cnic):
    """Download PDF and search for CNIC in column 3 of each row."""
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        reader = PyPDF2.PdfReader(BytesIO(r.content))
        for page in reader.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            for line in lines:
                cols = line.split()
                if len(cols) >= 3:
                    col3_digits = "".join(filter(str.isdigit, cols[2]))
                    if cnic == col3_digits:
                        return {
                            "merit_list_line": line.strip(),
                            "department": cols[1] if len(cols) > 1 else "",
                        }
    except Exception as e:
        print(f"[Warning] Skipping PDF {pdf_url} due to error: {e}")
    return None

@app.route("/")
def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UAF Merit List CNIC Search</title>
        <style>
            body { font-family: Arial; margin: 30px; }
            input[type=text] { width: 300px; padding: 5px; }
            input[type=submit] { padding: 5px 10px; }
            .result { margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>UAF Merit List CNIC Search</h1>
        <form action="/search" method="get">
            Enter CNIC (numbers only): <input type="text" name="cnic" required>
            <input type="submit" value="Search">
        </form>
        <div class="result">
            {% if results is defined %}
                {% if results %}
                    <h2>Matches for CNIC {{ cnic }}:</h2>
                    <ul>
                        {% for r in results %}
                            <li>
                                Merit List: {{ r.listno }}, Department: {{ r.department }},
                                <a href="{{ r.file }}" target="_blank">PDF</a>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p>No matches found for CNIC {{ cnic }}.</p>
                {% endif %}
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route("/search")
def search_cnic():
    cnic = request.args.get("cnic", "").strip()
    if not cnic or not cnic.isdigit():
        return "Please provide a valid CNIC as numbers only.", 400

    results = []
    for m in fetch_merit_lists():
        if m["file"]:
            found = search_cnic_in_pdf(m["file"], cnic)
            if found:
                results.append({
                    "listno": m["listno"],
                    "department": found["department"],
                    "file": m["file"]
                })

    html_content = home().data.decode("utf-8")
    return render_template_string(html_content, results=results, cnic=cnic)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
