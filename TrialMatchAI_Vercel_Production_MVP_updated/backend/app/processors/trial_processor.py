import csv
import json
import re
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models import Trial, TrialCriterion

class TrialProcessor:
    """Normalize downloaded or API-fetched ClinicalTrials.gov v2 records
    and safely upsert them into the database.
    """
    def __init__(self, db: Session):
        self.db = db

    def load_records(self, path: str) -> List[Dict[str, Any]]:
        p = Path(path)
        if p.suffix.lower() == ".csv":
            with p.open(newline="", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return data.get("studies", data.get("records", [data]))

    @staticmethod
    def _val(obj: Any, *keys: str) -> Any:
        if not isinstance(obj, dict):
            return None
        for k in keys:
            v = obj.get(k)
            if v not in (None, "", [], {}):
                return v
        return None

    @staticmethod
    def _parse_age(age_str: Optional[str]) -> Optional[float]:
        if not age_str or not isinstance(age_str, str):
            return None
        s = age_str.strip().lower()
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if not m:
            return None
        try:
            val = float(m.group(1))
            if "month" in s:
                val = val / 12.0
            elif "day" in s:
                val = val / 365.0
            return round(val, 2)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_date(dt_val: Any) -> Optional[date]:
        if not dt_val:
            return None
        if isinstance(dt_val, date):
            return dt_val
        if isinstance(dt_val, datetime):
            return dt_val.date()
        if isinstance(dt_val, dict):
            dt_val = dt_val.get("date")
        if not isinstance(dt_val, str):
            return None
        dt_str = dt_val.strip()
        for fmt in ("%Y-%m-%d", "%Y-%m", "%B %d, %Y", "%b %d, %Y", "%Y"):
            try:
                return datetime.strptime(dt_str, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_bool(val: Any) -> Optional[bool]:
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            v = val.strip().lower()
            if v in ("true", "yes", "y", "1"):
                return True
            if v in ("false", "no", "n", "0"):
                return False
        return None

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Maps ClinicalTrials.gov v2 raw JSON structure into clean dict for Trial model."""
        p = raw.get("protocolSection", raw)
        ident = p.get("identificationModule", {})
        status = p.get("statusModule", {})
        design = p.get("designModule", {})
        desc = p.get("descriptionModule", {})
        cond = p.get("conditionsModule", {})
        arms = p.get("armsInterventionsModule", {})
        elig = p.get("eligibilityModule", {})
        contacts = p.get("contactsLocationsModule", {})
        sponsors = p.get("sponsorCollaboratorsModule", {})

        nct = self._val(ident, "nctId", "NCTId") or raw.get("nct_id") or raw.get("NCTId")
        brief_title = self._val(ident, "briefTitle", "title") or "Untitled trial"
        official_title = self._val(ident, "officialTitle")

        phase_raw = self._val(design, "phases", "phase")
        if isinstance(phase_raw, list):
            phase = ", ".join(str(x) for x in phase_raw if x)
        else:
            phase = str(phase_raw) if phase_raw else None

        conditions = cond.get("conditions", [])
        if not isinstance(conditions, list):
            conditions = [str(conditions)] if conditions else []

        interventions_raw = arms.get("interventions", [])
        interventions = []
        if isinstance(interventions_raw, list):
            for x in interventions_raw:
                if isinstance(x, dict) and x.get("name"):
                    interventions.append(x.get("name"))
                elif isinstance(x, str):
                    interventions.append(x)
        elif isinstance(interventions_raw, str):
            interventions = [interventions_raw]

        elig_text = self._val(elig, "eligibilityCriteria", "criteria")
        min_age_str = self._val(elig, "minimumAge")
        max_age_str = self._val(elig, "maximumAge")
        sex = self._val(elig, "sex")
        healthy = self._parse_bool(self._val(elig, "healthyVolunteers"))

        study_type = self._val(design, "studyType")
        enrollment_info = design.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count") if isinstance(enrollment_info, dict) else None
        if enrollment is not None:
            try:
                enrollment = int(enrollment)
            except (ValueError, TypeError):
                enrollment = None

        locations_raw = contacts.get("locations", [])
        locations = []
        if isinstance(locations_raw, list):
            for loc in locations_raw:
                if isinstance(loc, dict):
                    loc_str = ", ".join(filter(None, [loc.get("facility"), loc.get("city"), loc.get("state"), loc.get("country")]))
                    if loc_str:
                        locations.append(loc_str)
                elif isinstance(loc, str):
                    locations.append(loc)

        sponsor = None
        lead_sponsor = sponsors.get("leadSponsor", {})
        if isinstance(lead_sponsor, dict):
            sponsor = lead_sponsor.get("name")

        last_update_val = self._val(status, "lastUpdatePostDateStruct", "lastUpdateSubmitDate", "last_update_date")

        return {
            "nct_id": nct,
            "title": brief_title,
            "official_title": official_title,
            "status": self._val(status, "overallStatus", "status"),
            "phase": phase,
            "conditions": conditions,
            "interventions": interventions,
            "min_age": self._parse_age(min_age_str),
            "max_age": self._parse_age(max_age_str),
            "sex": sex,
            "healthy_volunteers": healthy,
            "study_type": study_type,
            "enrollment": enrollment,
            "locations": locations,
            "sponsor": sponsor,
            "eligibility_text": elig_text,
            "last_update_date": self._parse_date(last_update_val),
        }

    def import_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Safely upserts a list of raw study records into the database.
        Returns a dictionary with inserted_count, updated_count, failed_count, and imported_count.
        """
        inserted = 0
        updated = 0
        failed = 0

        for raw in records:
            try:
                t = self.normalize(raw)
                if not t.get("nct_id"):
                    failed += 1
                    continue

                nct_id = t["nct_id"]
                trial = self.db.query(Trial).filter_by(nct_id=nct_id).one_or_none()
                if not trial:
                    trial = Trial(**t)
                    self.db.add(trial)
                    self.db.flush()
                    inserted += 1
                else:
                    for k, v in t.items():
                        setattr(trial, k, v)
                    updated += 1

                self._criteria(trial)
            except Exception as e:
                print(f"Error processing record {raw.get('nct_id', 'unknown')}: {e}")
                failed += 1

        try:
            self.db.commit()
        except Exception as e:
            err_msg = str(e)
            print(f"Error committing trial records transaction: {err_msg}")
            self.db.rollback()
            return {
                "status": "failed",
                "error_type": "database_schema_error" if "no such column" in err_msg.lower() else "database_error",
                "message": "Trial database schema is out of date. Run Alembic migrations." if "no such column" in err_msg.lower() else err_msg,
                "imported_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
                "failed_count": len(records)
            }

        return {
            "status": "success",
            "imported_count": inserted + updated,
            "inserted_count": inserted,
            "updated_count": updated,
            "failed_count": failed
        }

    def import_file(self, path: str) -> Dict[str, int]:
        return self.import_records(self.load_records(path))

    def _criteria(self, trial: Trial):
        text = trial.eligibility_text or ""
        if not text:
            return
        sections = {"INCLUSION": "", "EXCLUSION": ""}
        current = None
        for line in text.splitlines():
            upper = line.strip().upper()
            if "INCLUSION" in upper:
                current = "INCLUSION"
                continue
            if "EXCLUSION" in upper:
                current = "EXCLUSION"
                continue
            if current:
                sections[current] += line.strip() + " "
        existing = {c.criterion_text for c in self.db.query(TrialCriterion).filter_by(trial_id=trial.id).all()}
        for kind, body in sections.items():
            for sentence in [x.strip(" .-") for x in body.split(";") if x.strip(" .-")]:
                if sentence and sentence not in existing:
                    self.db.add(TrialCriterion(
                        trial_id=trial.id,
                        criterion_type=kind,
                        criterion_text=sentence,
                        category=self._category(sentence),
                        source_text=sentence,
                        confidence=0.6
                    ))

    @staticmethod
    def _category(text: str) -> str:
        t = text.lower()
        for key, cat in [("creatinine", "LAB"), ("hemoglobin", "LAB"), ("age", "AGE"), ("female", "SEX"), ("male", "SEX"), ("chemotherapy", "TREATMENT_HISTORY"), ("medication", "MEDICATION"), ("diagnos", "DIAGNOSIS"), ("pregnan", "PREGNANCY")]:
            if key in t:
                return cat
        return "OTHER"
