from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "UAF Merit List Scraper Running!"

@app.route('/meritlists')
def meritlists():
    url = "https://web.uaf.edu.pk/Downloads/MeritListsView"
    headers = {"User-Agent": "Mozilla/5.0"}  # avoids simple blocks
    response = requests.get(url, headers=headers)
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

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
