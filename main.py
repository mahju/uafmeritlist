from flask import Flask, render_template, request
import requests
import pdfplumber

app = Flask(__name__)

# CNIC Search Route
@app.route("/search", methods=["POST"])
def search():
    cnic = request.form.get("cnic", "").strip()
    if not cnic:
        return render_template("index.html", error="Please enter CNIC")

    # JSON list of merit list links
    url = "https://uafmeritlist-production.up.railway.app/view_links"
    resp = requests.get(url)
    data = resp.json()

    # صرف پہلی PDF link لیں
    first_pdf_url = data[0]["url"]

    results = []

    try:
        pdf_resp = requests.get(first_pdf_url)
        with open("temp.pdf", "wb") as f:
            f.write(pdf_resp.content)

        with pdfplumber.open("temp.pdf") as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and cnic in text:
                    results.append({
                        "url": first_pdf_url,
                        "page": page_num + 1,
                        "row": text[:500]
                    })

    except Exception as e:
        return render_template("index.html", error=f"Error reading PDF: {str(e)}")

    return render_template("results.html", results=results)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
