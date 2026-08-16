import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database.session import SessionLocal
from backend.app.services.clinicaltrials_api import ClinicalTrialsAPIService

def main():
    parser = argparse.ArgumentParser(description="Fetch and sync live clinical trial data from ClinicalTrials.gov API.")
    parser.add_argument("--condition", type=str, default="Breast Cancer", help="Condition name to search (e.g., 'Breast Cancer', 'Oncology')")
    parser.add_argument("--term", type=str, default=None, help="General search term")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of studies to fetch (1-50)")
    parser.add_argument("--nct-id", type=str, default=None, help="Specific NCT ID to fetch (e.g. NCT01234567)")
    parser.add_argument("--api-key", type=str, default=None, help="Override API Key (otherwise uses CLINICALTRIALS_API_KEY from .env)")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = ClinicalTrialsAPIService(db, api_key=args.api_key)
        print(f"Connecting to ClinicalTrials.gov API (API key configured: {bool(service.api_key)})...")
        imported_count = service.sync_trials(
            condition=args.condition,
            term=args.term,
            limit=args.limit,
            nct_id=args.nct_id
        )
        print(f"Successfully imported/updated {imported_count} trial record(s) in the database.")
    except Exception as e:
        print(f"Error fetching clinical trials: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
