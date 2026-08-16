import urllib.request
import urllib.parse
import json
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.core.config import get_settings
from backend.app.processors.trial_processor import TrialProcessor

# Global in-memory cache for static metadata / enums
_METADATA_CACHE: Dict[str, Any] = {}

class ClinicalTrialsAPIService:
    """Service to interact with the official ClinicalTrials.gov API v2
    (https://clinicaltrials.gov/api/v2).

    Supports:
    - Search studies by condition, term, or NCT ID
    - Paginated batched ingestion via nextPageToken
    - Single study lookup (/studies/{nctId})
    - Metadata, search-areas, and enums lookup with caching
    - Data statistics endpoints
    - Memory-efficient batch upserting into database
    """

    def __init__(self, db: Session, api_key: Optional[str] = None):
        self.db = db
        settings = get_settings()
        self.api_key = api_key or settings.ct_api_key
        self.base_url = settings.clinicaltrials_api_base_url.rstrip("/")
        self.timeout = settings.clinicaltrials_api_timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "TrialMatchAI/1.0",
        }
        if self.api_key and self.api_key.strip():
            headers["X-API-KEY"] = self.api_key.strip()
        return headers

    def _make_request(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """Make HTTP GET request with timeout and exponential backoff retry
        for transient network failures or rate limits (HTTP 429 / 503).
        """
        headers = self._get_headers()
        req = urllib.request.Request(url, headers=headers)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw_body = resp.read().decode("utf-8")
                    return json.loads(raw_body)
            except urllib.error.HTTPError as e:
                # Permanent client errors (400, 401, 403, 404) should not be retried indefinitely
                if e.code in (400, 401, 403, 404):
                    print(f"ClinicalTrials API HTTP {e.code} for URL {url}")
                    raise e
                # Transient errors (429, 500, 502, 503, 504) -> retry
                last_error = e
                print(f"ClinicalTrials API HTTP {e.code} (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                # Network timeout, connection reset, etc. -> retry
                last_error = e
                print(f"ClinicalTrials API network error (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt)  # 1s, 2s, 4s backoff
                time.sleep(sleep_time)

        if last_error:
            raise last_error
        return {}

    def fetch_single_study(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """Fetch individual study by NCT ID via GET /studies/{nctId}."""
        clean_nct = nct_id.strip()
        url = f"{self.base_url}/studies/{urllib.parse.quote(clean_nct)}"
        try:
            data = self._make_request(url)
            return data
        except Exception as e:
            print(f"Error fetching study {nct_id}: {e}")
            return None

    def fetch_studies(
        self,
        condition: Optional[str] = None,
        term: Optional[str] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
        nct_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch raw study records from ClinicalTrials.gov v2 API /studies endpoint.
        Returns dictionary containing:
        - studies: List[dict]
        - nextPageToken: Optional[str]
        - totalCount: Optional[int]
        """
        if nct_id:
            study = self.fetch_single_study(nct_id)
            return {
                "studies": [study] if study else [],
                "nextPageToken": None,
                "totalCount": 1 if study else 0
            }

        params: Dict[str, Any] = {
            "pageSize": min(max(page_size, 1), 1000),
            "format": "json"
        }
        if condition and condition.strip():
            params["query.cond"] = condition.strip()
        if term and term.strip():
            params["query.term"] = term.strip()
        if page_token and page_token.strip():
            params["pageToken"] = page_token.strip()

        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/studies?{query_string}"

        try:
            data = self._make_request(url)
            studies = data.get("studies", [])
            next_page_token = data.get("nextPageToken")
            total_count = data.get("totalCount")
            return {
                "studies": studies,
                "nextPageToken": next_page_token,
                "totalCount": total_count
            }
        except Exception as e:
            print(f"Error fetching studies from ClinicalTrials.gov API: {e}")
            return {"studies": [], "nextPageToken": None, "totalCount": 0}

    def sync_trials(
        self,
        condition: Optional[str] = "Breast Cancer",
        term: Optional[str] = None,
        limit: int = 10,
        nct_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch studies from ClinicalTrials.gov v2 API using pagination
        and incrementally upsert them into the database without loading all
        records into RAM at once.
        """
        processor = TrialProcessor(self.db)

        if nct_id:
            study = self.fetch_single_study(nct_id)
            if not study:
                return {
                    "status": "success",
                    "source": "ClinicalTrials.gov",
                    "api_version": "v2",
                    "imported_count": 0,
                    "total": 0,
                    "inserted_count": 0,
                    "updated_count": 0,
                    "failed_count": 1,
                    "failed_nct_ids": [nct_id],
                    "errors": [f"Study {nct_id} not found"],
                    "api_key_configured": bool(self.api_key)
                }
            res = processor.import_records([study])
            res["source"] = "ClinicalTrials.gov"
            res["api_version"] = "v2"
            res["total"] = res.get("imported_count", 0)
            res["failed_nct_ids"] = []
            res["errors"] = []
            res["api_key_configured"] = bool(self.api_key)
            return res

        total_inserted = 0
        total_updated = 0
        total_failed = 0
        next_page_token = None

        target_limit = min(max(limit, 1), 10000)
        # Fetch in batches of up to 50 (or target_limit if smaller)
        batch_size = min(target_limit, 50)

        while (total_inserted + total_updated) < target_limit:
            remaining = target_limit - (total_inserted + total_updated)
            current_batch_size = min(batch_size, remaining)

            resp = self.fetch_studies(
                condition=condition,
                term=term,
                page_size=current_batch_size,
                page_token=next_page_token
            )

            raw_studies = resp.get("studies", [])
            if not raw_studies:
                break

            batch_res = processor.import_records(raw_studies)
            if batch_res.get("status") == "failed":
                batch_res["source"] = "ClinicalTrials.gov"
                batch_res["api_version"] = "v2"
                batch_res["requested"] = target_limit
                batch_res["fetched"] = len(raw_studies)
                batch_res["inserted"] = 0
                batch_res["updated"] = 0
                batch_res["failed"] = len(raw_studies)
                batch_res["api_key_configured"] = bool(self.api_key)
                return batch_res

            total_inserted += batch_res.get("inserted_count", 0)
            total_updated += batch_res.get("updated_count", 0)
            total_failed += batch_res.get("failed_count", 0)

            next_page_token = resp.get("nextPageToken")
            if not next_page_token:
                break

        return {
            "status": "success",
            "source": "ClinicalTrials.gov",
            "api_version": "v2",
            "imported_count": total_inserted + total_updated,
            "total": total_inserted + total_updated,
            "inserted_count": total_inserted,
            "updated_count": total_updated,
            "failed_count": total_failed,
            "failed_nct_ids": [],
            "errors": [],
            "api_key_configured": bool(self.api_key)
        }

    # Metadata and Enums endpoints (cached in memory)
    def get_metadata(self) -> Dict[str, Any]:
        """GET /studies/metadata"""
        if "metadata" not in _METADATA_CACHE:
            url = f"{self.base_url}/studies/metadata"
            _METADATA_CACHE["metadata"] = self._make_request(url)
        return _METADATA_CACHE["metadata"]

    def get_search_areas(self) -> List[Dict[str, Any]]:
        """GET /studies/search-areas"""
        if "search_areas" not in _METADATA_CACHE:
            url = f"{self.base_url}/studies/search-areas"
            _METADATA_CACHE["search_areas"] = self._make_request(url)
        return _METADATA_CACHE["search_areas"]

    def get_enums(self) -> List[Dict[str, Any]]:
        """GET /studies/enums"""
        if "enums" not in _METADATA_CACHE:
            url = f"{self.base_url}/studies/enums"
            _METADATA_CACHE["enums"] = self._make_request(url)
        return _METADATA_CACHE["enums"]

    # Statistics endpoints
    def get_stats_size(self) -> Dict[str, Any]:
        """GET /stats/size"""
        url = f"{self.base_url}/stats/size"
        return self._make_request(url)

    def get_stats_field_values(self, field: str) -> Dict[str, Any]:
        """GET /stats/field/values"""
        url = f"{self.base_url}/stats/field/values?field={urllib.parse.quote(field)}"
        return self._make_request(url)

    def get_stats_field_sizes(self) -> Dict[str, Any]:
        """GET /stats/field/sizes"""
        url = f"{self.base_url}/stats/field/sizes"
        return self._make_request(url)
