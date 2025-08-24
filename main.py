from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# --- Step 1: Fetch Merit List PDF Links with Context ---
def fetch_merit_pdfs():
    """Fetch all merit list PDF links with names from UAF page."""
    url = "https://web.uaf.edu.pk/Downloads/MeritListsView"
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        pdf_links = []

        table = soup.find("table")
        if not table:
            print("Merit list table not found on the page.")
            return pdf_links

        for row in table.find_all("tr")[1:]:  # skip header
            cols = row.find_all("td")
            link_tag = row.find("a", href=True)
            if link_tag:
                href = link_tag["href"]
                full_url = href if href.startswith("http") else "https://web.uaf.edu.pk" + href
                # Combine all columns' text as the list name/department
                name = " ".join(col.get_text(strip=True) for col in cols)
                pdf_links.append({"url": full_url, "name": name})

        return pdf_links
    except Exception as e:
        print("Error fetching merit list PDFs:", e)
        return []


# --- Step 2: Search CNIC in each PDF ---
def search_cnic_in_pdf(pdf_info, cnic):
    """Download PDF and search for CNIC. Return merit list name if found."""
    try:
        r = requests.get(pdf_info["url"], headers=HEADERS, timeout=30)
        r.raise_for_status()
        reader = PyPDF2.PdfReader(BytesIO(r.content))

        for page in reader.pages:
            text = page.extract_text() or ""
            # Normalize spacing for easier matching
            text = text.replace(" ", "").replace("\n", "")
            if cnic in text:
                return pdf_info["name"]
    except Exception as e:
        print(f"Error reading PDF {pdf_info['url']}: {e}")
    return None


# --- Flask Routes ---
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    cnic = request.form.get("cnic", "").strip()
    if not cnic:
        return render_template("index.html", error="Please enter CNIC.")

    try:
        pdfs = fetch_merit_pdfs()
        results = []

        for pdf_info in pdfs:
            found_in = search_cnic_in_pdf(pdf_info, cnic)
            if found_in:
                results.append({"list": found_in, "url": pdf_info["url"]})

        if not results:
            return render_template("index.html", error="No matches found for this CNIC.")

        return render_template("results.html", results=results, cnic=cnic)

    except Exception as e:
        import traceback
        print("ERROR:", e)
        traceback.print_exc()
        return f"<h2>Internal Error:</h2><pre>{e}</pre>", 500


