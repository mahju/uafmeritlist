from flask import Flask, jsonify, request, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

UAF_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# HTML page with CNIC input
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>UAF Merit List CNIC Search</title>
</head>
<body>
    <h2>Search Merit List by CNIC</h2>
    <input type="text" id="cnicInput" placeholder="Enter CNIC">
    <button onclick="searchCNIC()">Search</button>
    <pre id="results"></pre>

    <script>
        async function searchCNIC() {
            const cnic = document.getElementById('cnicInput').value;
            if (!cnic) {
                alert('Please enter CNIC!');
                return;
            }
            document.getElementById('results').innerText = 'Searching...';
            try {
                const response = await fetch(`/search?cnic=${cnic}`);
                const data = await response.json();
                document.getElementById('results').innerText = JSON.stringify(data, null, 2);
            } catch (err) {
                document.getElementById('results').innerText = 'Error fetching data';
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/meritlists')
def meritlists():
    response = requests.get(UAF_PAGE, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    data = []
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                data.append({
                    "listno": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "campus": cols[2].get_text(strip=True),
                    "degree": cols[3].get_text(strip=True),
                    "file": cols[4].find("a")["href"] if cols[4].find("a") else ""
                })
    return jsonify(data)

@app.route('/search')
def search():
    cnic = request.args.get("cnic")
    if not cnic:
        return jsonify({"error": "CNIC not provided"}), 400

    # Get all merit lists
    merit_lists = meritlists().json  # Call existing endpoint logic
    results = []

    for item in merit_lists:
        pdf_url = item["file"]
        # Fetch PDF and search CNIC - simplified as example
        # You would need a PDF parsing library to extract text
        # Here we just simulate a match if CNIC is in file URL
        if cnic in pdf_url:
            results.append(item)

    return jsonify({"cnic": cnic, "matches": results})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
