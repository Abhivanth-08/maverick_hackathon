import unittest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import json
import urllib.error

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.session import Base
from backend.app.models import Trial, TrialCriterion, Patient, Organization, PatientLab
from backend.app.processors.trial_processor import TrialProcessor
from backend.app.services.clinicaltrials_api import ClinicalTrialsAPIService
from backend.app.matching.engine import MatchingEngine

class TestClinicalTrialsAPIV2(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite DB for tests
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def _sample_v2_study(self, nct_id="NCT12345678", title="Sample Breast Cancer Study"):
        return {
            "protocolSection": {
                "identificationModule": {
                    "nctId": nct_id,
                    "briefTitle": title,
                    "officialTitle": f"Official {title}"
                },
                "statusModule": {
                    "overallStatus": "RECRUITING",
                    "lastUpdatePostDateStruct": {"date": "2024-05-15"}
                },
                "designModule": {
                    "phases": ["PHASE2", "PHASE3"],
                    "studyType": "INTERVENTIONAL",
                    "enrollmentInfo": {"count": 250}
                },
                "conditionsModule": {
                    "conditions": ["Breast Cancer", "Neoplasms"]
                },
                "armsInterventionsModule": {
                    "interventions": [
                        {"name": "Trastuzumab", "type": "DRUG"},
                        {"name": "Chemotherapy", "type": "DRUG"}
                    ]
                },
                "eligibilityModule": {
                    "eligibilityCriteria": "Inclusion Criteria:\n- Female patients aged >= 18 years.\n- Serum creatinine < 1.5 mg/dL.\nExclusion Criteria:\n- Prior history of cardiac failure.",
                    "minimumAge": "18 Years",
                    "maximumAge": "75 Years",
                    "sex": "FEMALE",
                    "healthyVolunteers": False
                },
                "contactsLocationsModule": {
                    "locations": [
                        {"facility": "Memorial Hospital", "city": "New York", "state": "NY", "country": "United States"}
                    ]
                },
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {"name": "Oncology Research Foundation"}
                }
            }
        }

    def test_normalize_raw_v2_study(self):
        raw = self._sample_v2_study()
        processor = TrialProcessor(self.db)
        norm = processor.normalize(raw)

        self.assertEqual(norm["nct_id"], "NCT12345678")
        self.assertEqual(norm["title"], "Sample Breast Cancer Study")
        self.assertEqual(norm["official_title"], "Official Sample Breast Cancer Study")
        self.assertEqual(norm["status"], "RECRUITING")
        self.assertEqual(norm["phase"], "PHASE2, PHASE3")
        self.assertIn("Breast Cancer", norm["conditions"])
        self.assertIn("Trastuzumab", norm["interventions"])
        self.assertEqual(norm["min_age"], 18.0)
        self.assertEqual(norm["max_age"], 75.0)
        self.assertEqual(norm["sex"], "FEMALE")
        self.assertFalse(norm["healthy_volunteers"])
        self.assertEqual(norm["study_type"], "INTERVENTIONAL")
        self.assertEqual(norm["enrollment"], 250)
        self.assertEqual(norm["sponsor"], "Oncology Research Foundation")
        self.assertEqual(norm["last_update_date"], date(2024, 5, 15))

    def test_import_new_trial_insert(self):
        raw = self._sample_v2_study("NCT00000001", "New Trial")
        processor = TrialProcessor(self.db)
        stats = processor.import_records([raw])

        self.assertEqual(stats["inserted_count"], 1)
        self.assertEqual(stats["updated_count"], 0)
        self.assertEqual(stats["imported_count"], 1)

        trial = self.db.query(Trial).filter_by(nct_id="NCT00000001").first()
        self.assertIsNotNone(trial)
        self.assertEqual(trial.title, "New Trial")

        criteria = self.db.query(TrialCriterion).filter_by(trial_id=trial.id).all()
        self.assertGreater(len(criteria), 0)

    def test_update_existing_trial(self):
        processor = TrialProcessor(self.db)
        raw1 = self._sample_v2_study("NCT00000002", "Initial Title")
        processor.import_records([raw1])

        raw2 = self._sample_v2_study("NCT00000002", "Updated Title")
        stats = processor.import_records([raw2])

        self.assertEqual(stats["inserted_count"], 0)
        self.assertEqual(stats["updated_count"], 1)
        self.assertEqual(stats["imported_count"], 1)

        # Check only one trial exists with that NCT ID (duplicate prevention)
        trials = self.db.query(Trial).filter_by(nct_id="NCT00000002").all()
        self.assertEqual(len(trials), 1)
        self.assertEqual(trials[0].title, "Updated Title")

    def test_missing_optional_fields_handling(self):
        raw_sparse = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT_SPARSE",
                    "briefTitle": "Minimal Trial"
                }
            }
        }
        processor = TrialProcessor(self.db)
        stats = processor.import_records([raw_sparse])

        self.assertEqual(stats["imported_count"], 1)
        trial = self.db.query(Trial).filter_by(nct_id="NCT_SPARSE").first()
        self.assertIsNotNone(trial)
        self.assertEqual(trial.title, "Minimal Trial")
        self.assertIsNone(trial.status)
        self.assertIsNone(trial.phase)
        self.assertEqual(trial.conditions, [])
        self.assertEqual(trial.interventions, [])

    @patch("backend.app.services.clinicaltrials_api.ClinicalTrialsAPIService._make_request")
    def test_search_by_condition_and_term(self, mock_make_req):
        mock_make_req.return_value = {
            "studies": [self._sample_v2_study("NCT100", "Cond Trial")],
            "nextPageToken": None,
            "totalCount": 1
        }
        service = ClinicalTrialsAPIService(self.db)
        res = service.fetch_studies(condition="Breast Cancer", term="Trastuzumab", page_size=5)

        self.assertEqual(len(res["studies"]), 1)
        self.assertEqual(res["totalCount"], 1)

        # Verify URL constructed with condition & term
        call_url = mock_make_req.call_args[0][0]
        self.assertIn("query.cond=Breast+Cancer", call_url)
        self.assertIn("query.term=Trastuzumab", call_url)

    @patch("backend.app.services.clinicaltrials_api.ClinicalTrialsAPIService._make_request")
    def test_fetch_single_study_by_nct(self, mock_make_req):
        mock_make_req.return_value = self._sample_v2_study("NCT999", "Single Study")
        service = ClinicalTrialsAPIService(self.db)
        res = service.fetch_studies(nct_id="NCT999")

        self.assertEqual(len(res["studies"]), 1)
        call_url = mock_make_req.call_args[0][0]
        self.assertIn("/studies/NCT999", call_url)

    @patch("backend.app.services.clinicaltrials_api.ClinicalTrialsAPIService._make_request")
    def test_pagination_token_handling(self, mock_make_req):
        # Mock 2 pages of pagination
        mock_make_req.side_effect = [
            {
                "studies": [self._sample_v2_study("NCT_P1", "Page 1 Trial")],
                "nextPageToken": "TOKEN_PAGE_2"
            },
            {
                "studies": [self._sample_v2_study("NCT_P2", "Page 2 Trial")],
                "nextPageToken": None
            }
        ]

        service = ClinicalTrialsAPIService(self.db)
        stats = service.sync_trials(condition="Cancer", limit=2)

        self.assertEqual(stats["imported_count"], 2)
        self.assertEqual(stats["inserted_count"], 2)
        self.assertEqual(mock_make_req.call_count, 2)

        second_call_url = mock_make_req.call_args_list[1][0][0]
        self.assertIn("pageToken=TOKEN_PAGE_2", second_call_url)

    @patch("urllib.request.urlopen")
    def test_timeout_and_retry_logic(self, mock_urlopen):
        # Mock 2 failures followed by 1 success
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"studies": [], "nextPageToken": None}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        mock_urlopen.side_effect = [
            TimeoutError("Connection timed out"),
            urllib.error.URLError("Server unavailable"),
            mock_resp
        ]

        service = ClinicalTrialsAPIService(self.db)
        res = service.fetch_studies(condition="Test")
        self.assertEqual(res["studies"], [])
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("urllib.request.urlopen")
    def test_api_404_error_handling(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError("http://example.com", 404, "Not Found", {}, None)
        service = ClinicalTrialsAPIService(self.db)
        study = service.fetch_single_study("NCT_NONEXISTENT")
        self.assertIsNone(study)

    def test_matching_engine_compatibility_with_imported_trial(self):
        # 1. Import study into DB using processor
        raw = self._sample_v2_study("NCT_MATCH_1", "Breast Cancer Match Trial")
        processor = TrialProcessor(self.db)
        processor.import_records([raw])

        trial = self.db.query(Trial).filter_by(nct_id="NCT_MATCH_1").first()
        self.assertIsNotNone(trial)

        # 2. Setup organization and patient
        org = Organization(name="Match Org")
        self.db.add(org)
        self.db.flush()

        p = Patient(
            organization_id=org.id,
            external_patient_id="PAT_001",
            date_of_birth=date(1990, 1, 1),
            sex="Female"
        )
        self.db.add(p)
        self.db.flush()

        # Add Creatinine lab evidence
        self.db.add(PatientLab(
            organization_id=org.id,
            patient_id=p.id,
            test_name="Serum Creatinine",
            value_numeric=1.1,
            unit="mg/dL",
            observed_at=datetime.utcnow()
        ))
        self.db.commit()

        # 3. Screen patient against imported trial
        match = MatchingEngine(self.db).screen(p.id, trial.id, org.id)
        self.assertIsNotNone(match)
        self.assertIn(match.status, ("POTENTIAL_MATCH", "REQUIRES_REVIEW", "NOT_ELIGIBLE"))

if __name__ == "__main__":
    unittest.main()
