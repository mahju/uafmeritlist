@app.route("/search", methods=["POST"])
def search_cnic():
    try:
        cnic = (request.form.get("cnic") or "").strip()
        if not cnic:
            return render_template("index.html", error="Please enter CNIC.")

        if not cnic.isdigit():
            return render_template("index.html", error="CNIC must be digits only (no dashes).")

        logger.info(f"Starting search for CNIC: {cnic}")
        
        # Test if we can fetch merit lists
        lists = fetch_merit_lists()
        logger.info(f"Fetched {len(lists)} merit lists")
        
        if not lists:
            return render_template("results.html", cnic=cnic, results=[])

        results = []
        scanned = 0

        for entry in lists:
            if scanned >= MAX_PDFS:
                logger.info(f"Reached MAX_PDFS limit ({MAX_PDFS})")
                break

            if not entry.get("file"):
                continue

            logger.info(f"Scanning PDF {scanned + 1}: {entry['file']}")
            
            # Test PDF processing
            match = search_in_pdf(entry["file"], cnic)
            scanned += 1

            if match:
                results.append({
                    "list": entry["title"],
                    "url": entry["file"],
                    "row": match.get("row", ""),
                    "columns": match.get("columns", []),
                    "listno": entry.get("listno", ""),
                    "campus": entry.get("campus", ""),
                    "degree": entry.get("degree", ""),
                })
                logger.info(f"Found match in: {entry['title']}")
                if len(results) >= MAX_MATCHES:
                    break

        logger.info(f"Search completed. Found {len(results)} matches")
        return render_template("results.html", cnic=cnic, results=results)

    except Exception as e:
        logger.error(f"Critical error in search_cnic: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("index.html", error=f"Internal server error: {str(e)}")
