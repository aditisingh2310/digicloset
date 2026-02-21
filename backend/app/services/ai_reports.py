import csv
from pathlib import Path

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def generate_catalog_report(products: list) -> Path:
    path = REPORT_DIR / "catalog_report.csv"

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Product ID", "Score", "Issues"])

        for p in products:
            writer.writerow([
                p["id"],
                p.get("score", 0),
                ", ".join(p.get("issues", []))
            ])

    return path
