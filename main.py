import requests
import fitz  # PyMuPDF
from flask import Flask, render_template, request

app = Flask(__name__)

# 🎯 API Link
json_url = "https://uafmeritlist-production.up.railway.app/view_links"

def get_first_pdf():
    try:
        response = requests.get(json_url, timeout=15)
        pdf_files = response.json()  # یہ list ہونی چاہیے

        if pdf_files and isinstance(pdf_files, list):
            # صرف پہلی PDF واپس کریں
            return pdf_files[0]["url"]
        else:
            return None
    except Exception as e:
        print("⚠️ JSON fetch error:", e)
        return None

def search_cnic_in_pdf(cnic, pdf_url):
    results = []
    try:
        # PDF ڈاؤنلوڈ کریں
        response = requests.get(pdf_url, timeout=30)
        with open("temp.pdf", "wb") as f:
            f.write(response.content)

        # PDF read کریں
        doc = fitz.open("temp.pdf")
        for page_num in range(len(doc)):
            text = doc[page_num].get_text("text")
            if cnic in text:
                results.append({
                    "url": pdf_url,
                    "page": page_num + 1,
                    "row": text[:500]  # ⚡ صرف 500 chars تاکہ بہت بڑا text نہ ہو
                })
                break
    except Exception as e:
        print("⚠️ Error in PDF search:", e)
    return results

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    cnic = request.form.get("cnic", "").strip()
    if not cnic:
        return render_template("index.html", error="⚠️ Please enter CNIC")

    pdf_url = get_first_pdf()
    if not pdf_url:
        return render_template("index.html", error="⚠️ No PDF found in JSON")

    results = search_cnic_in_pdf(cnic, pdf_url)

    if not results:
        return render_template("results.html", results=[], error="❌ No match found")

    return render_template("results.html", results=results)


if __name__ == "__main__":
    app.run(debug=True)
