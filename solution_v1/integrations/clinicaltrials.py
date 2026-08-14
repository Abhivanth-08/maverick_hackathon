import requests
from utils.config import CLINICALTRIALS_API_BASE
from models.trial import Trial

def search_trials(condition: str = None, keyword: str = None):
    url = f"{CLINICALTRIALS_API_BASE}/studies"
    params = {"pageSize": 10}
    if condition:
        params["query.cond"] = condition
    if keyword:
        params["query.term"] = keyword
        
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        trials = []
        for study in data.get('studies', []):
            protocol = study.get('protocolSection', {})
            id_module = protocol.get('identificationModule', {})
            status_module = protocol.get('statusModule', {})
            cond_module = protocol.get('conditionsModule', {})
            eligibility_module = protocol.get('eligibilityModule', {})
            interv_module = protocol.get('armsInterventionsModule', {})
            
            nct_id = id_module.get('nctId', 'Unknown')
            title = id_module.get('briefTitle', 'Unknown')
            status = status_module.get('overallStatus', 'Unknown')
            cond = ", ".join(cond_module.get('conditions', ['Unknown']))
            interv = ", ".join([i.get('name', '') for i in interv_module.get('interventions', [])]) if interv_module else 'Unknown'
            phase = ", ".join(status_module.get('phases', ['Unknown']))
            eligibility_text = eligibility_module.get('eligibilityCriteria', 'Not available')
            
            trials.append(Trial(
                nct_id=nct_id, title=title, condition=cond, intervention=interv,
                status=status, phase=phase, study_type="Interventional", location="Various",
                eligibility_criteria_text=eligibility_text
            ))
        return trials
    except Exception as e:
        print(f"Error fetching trials: {e}")
        return []