from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import PyPDF2

app = Flask(__name__)

BASE_URL = "https://uaf.edu.pk/pages/meritlists.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ------------------ FUNCTIONS ------------------ #
def fetch_merit_pdfs():
    """Fetch all merit list PDF links from UAF site."""
    try:
        r = requests.get(BASE_URL, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        pdf_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = "https://uaf.edu.pk/" + href.lstrip("/")
                pdf_links.append(href)
        return pdf_links
    except Exception as e:
        print("Error fetching merit list PDFs:", e)
        return []

def search_cnic_in_pdf(pdf_url, cnic):
    """Download PDF and search for CNIC as plain number."""
    try:
        r = requests.get(pdf_url, headers=HEADERS)
        r.raise_for_status()
        reader = PyPDF2.PdfReader(BytesIO(r.content))
        for page in reader.pages:
            text = page.extract_text() or ""
            if cnic in text.replace(" ", ""):
                return True
    except Exception as e:
        print(f"Error reading PDF {pdf_url}: {e}")
    return False

# ------------------ ROUTES ------------------ #
@app.route("/")
def home():
    return render_template_string("""
        <h2>UAF Merit List CNIC Search</h2>
        <form action="/search" method="post">
            Enter CNIC (without dashes): <input type="text" name="cnic" required>
            <input type="submit" value="Search">
        </form>
    """)

@app.route("/search", methods=["POST"])
def search():
    cnic = request.form.get("cnic", "").strip()
    if not cnic.isdigit():
        return "<h3>Invalid CNIC! Please enter numbers only.</h3><a href='/'>Back</a>"

    pdf_links = fetch_merit_pdfs()
    if not pdf_links:
        return "<h3>No merit list PDFs found!</h3>"

    results = []
    for pdf_url in pdf_links:
        if search_cnic_in_pdf(pdf_url, cnic):
            results.append(pdf_url)

    if results:
        result_html = "<h3>CNIC Found in the following lists:</h3><ul>"
        for url in results:
            result_html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
        result_html += "</ul>"
        return result_html
    else:
        return "<h3>No matches found.</h3><a href='/'>Back</a>"

@app.route("/links")
def show_links():
    """Show all fetched merit list PDF links."""
    try:
        pdf_links = fetch_merit_pdfs()
        if not pdf_links:
            return "<h3>No merit list links found!</h3>"
        links_html = "<h2>Fetched Merit List Links:</h2><ul>"
        for url in pdf_links:
            links_html += f'<li><a href="{url}" target="_blank">{url}</a></li>'
        links_html += "</ul>"
        return links_html
    except Exception as e:
        return f"<h3>Error fetching links: {e}</h3>"

# ------------------ MAIN ------------------ #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
