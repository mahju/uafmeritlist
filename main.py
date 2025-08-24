from flask import Flask, jsonify, request, render_template, render_template_string, Response
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pdfplumber

app = Flask(__name__)

BASE_URL = "https://web.uaf.edu.pk"
MERIT_LIST_PAGE = "https://web.uaf.edu.pk/Downloads/MeritListsView"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_merit_lists():
    """Fetch all merit list entries from the UAF merit list page."""
    try:
        response = requests.get(MERIT_LIST_PAGE, headers=HEADERS, timeout=15)
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
                        file_link = BASE_URL.rstrip("/") + "/" + file_link.lstrip("/")

                    data.append({
                        "listno": cols[0].get_text(strip=True),
                        "title": cols[1].get_text(strip=True),
                        "campus": cols[2].get_text(strip=True),
                        "degree": cols[3].get_text(strip=True),
                        "file": file_link
                    })
        return data
    except Exception as e:
        print(f"[Error] Fetching merit lists failed: {e}")
        return []


def search_cnic_in_pdf(pdf_url, cnic):
    """Search CNIC in PDF tables AND full text using pdfplumber."""
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            for page in pdf.pages:
                # 1️⃣ Search in tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            for cell in row:
                                digits = "".join(filter(str.isdigit, cell or ""))
                                if cnic in digits:
                                    return True
                # 2️⃣ Search in full text
                text = page.extract_text() or ""
                digits_text = "".join(filter(str.isdigit, text))
                if cnic in digits_text:
                    return True
    except Exception as e:
        print(f"[Warning] Skipping PDF {pdf_url} due to error: {e}")
    return False


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search_cnic():
    cnic = request.form.get("cnic", "").strip()
    if not cnic:
        return render_template("index.html", error="Please enter CNIC.")

    def generate():
        yield "<html><body>"
        yield f"<h1>Searching for CNIC: {cnic}</h1>"
        yield "<ul>"

        merit_lists = fetch_merit_lists()
        for m in merit_lists:
            if m["file"] and search_cnic_in_pdf(m["file"], cnic):
                yield f'<li>✅ Found in: <b>{m["title"]}</b> — <a href="{m["file"]}" target="_blank">PDF</a></li>'

        yield "</ul>"
        yield '<a href="/">🔙 Back to Search</a>'
        yield "</body></html>"

    return Response(generate(), mimetype='text/html')


@app.route("/all_links")
def all_links():
    data = fetch_merit_lists()
    if not data:
        return jsonify({"error": "No merit lists found."})
    return jsonify(data)


@app.route("/view_links")
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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

