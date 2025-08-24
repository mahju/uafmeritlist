from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    cnic = request.form.get("cnic", "").strip()
    if not cnic:
        return render_template("index.html", error="Please enter CNIC")

    # JSON سے data لیں
    url = "https://uafmeritlist-production.up.railway.app/view_links"
    resp = requests.get(url)
    data = resp.json()

    # پہلی PDF
    first_pdf_url = data[0]["url"]

    # فی الحال صرف link واپس بھیجیں، PDF read نہیں کریں گے
    results = [{
        "url": first_pdf_url,
        "row": f"Dummy search for CNIC {cnic} (PDF not scanned yet).",
        "list": data[0]["name"],
        "columns": []
    }]

    return render_template("results.html", results=results)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
