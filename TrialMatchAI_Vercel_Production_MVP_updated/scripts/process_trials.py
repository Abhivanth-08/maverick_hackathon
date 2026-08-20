import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from backend.app.database.session import SessionLocal
from backend.app.processors.trial_processor import TrialProcessor
p=argparse.ArgumentParser(); p.add_argument('--input',required=True); a=p.parse_args()
db=SessionLocal()
try: print(f"Imported {TrialProcessor(db).import_file(a.input)} trial records")
finally: db.close()
