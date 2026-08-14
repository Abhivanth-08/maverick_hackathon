from models.criteria import StructuredCriteria, CriterionNode
from models.patient import Patient, PatientFact
from models.evidence import EvaluationTrace
from datetime import datetime

def evaluate_criterion(criterion: CriterionNode, patient: Patient) -> EvaluationTrace:
    status = "UNKNOWN"
    eval_result = False
    evidence = None
    message = "No matching evidence found."
    
    if criterion.concept.lower() == "age":
        if patient.birthDate:
            age = (datetime.now().date() - patient.birthDate).days / 365.25
            evidence = PatientFact(id="age", resource_type="Demographics", code="age", display="Age", value=age, source="Patient Profile")
            try:
                c_val = float(criterion.value)
                if criterion.operator == ">=": eval_result = age >= c_val
                elif criterion.operator == "<=": eval_result = age <= c_val
                elif criterion.operator == ">": eval_result = age > c_val
                elif criterion.operator == "<": eval_result = age < c_val
                elif criterion.operator == "==": eval_result = age == c_val
                status = "PASS" if eval_result else "FAIL"
                message = f"Age {age:.1f} evaluated against {criterion.operator} {c_val}"
            except:
                message = "Invalid age target value."
        else:
            message = "Patient age not available."
    else:
        for fact in patient.facts:
            if criterion.concept.lower() in fact.display.lower() or str(criterion.value).lower() in fact.display.lower():
                evidence = fact
                if criterion.operator == "exists":
                    eval_result = True
                elif criterion.operator == "not_exists":
                    eval_result = False
                elif criterion.operator in [">=", "<=", ">", "<", "=="] and fact.value is not None:
                    try:
                        f_val = float(fact.value)
                        c_val = float(criterion.value)
                        if criterion.operator == ">=": eval_result = f_val >= c_val
                        elif criterion.operator == "<=": eval_result = f_val <= c_val
                        elif criterion.operator == ">": eval_result = f_val > c_val
                        elif criterion.operator == "<": eval_result = f_val < c_val
                        elif criterion.operator == "==": eval_result = f_val == c_val
                    except:
                        eval_result = False
                
                status = "PASS" if eval_result else "FAIL"
                message = f"Found evidence: {fact.display} = {fact.value} {fact.unit}"
                break
        
        if not evidence and criterion.operator == "not_exists":
            eval_result = True
            status = "PASS"
            message = "No evidence found, passing 'not_exists' criteria."
            
    if criterion.type == "exclusion":
        if status == "PASS":
            status = "FAIL"
        elif status == "FAIL":
            status = "PASS"
            
    return EvaluationTrace(
        criterion_id=criterion.id,
        criterion_type=criterion.type,
        concept=criterion.concept,
        operator=criterion.operator,
        target_value=criterion.value,
        patient_value=evidence.value if evidence else None,
        evidence_source=evidence,
        evaluation_result=eval_result,
        status=status,
        message=message
    )

def evaluate_patient(criteria: StructuredCriteria, patient: Patient):
    traces = []
    for inc in criteria.inclusion:
        traces.append(evaluate_criterion(inc, patient))
    for exc in criteria.exclusion:
        traces.append(evaluate_criterion(exc, patient))
        
    passed = sum(1 for t in traces if t.status == "PASS")
    failed = sum(1 for t in traces if t.status == "FAIL")
    unknown = sum(1 for t in traces if t.status == "UNKNOWN")
    
    if failed > 0: overall = "NOT ELIGIBLE"
    elif unknown > 0: overall = "NEEDS REVIEW"
    else: overall = "POTENTIALLY ELIGIBLE"
        
    return {
        "overall": overall,
        "traces": traces,
        "passed": passed,
        "failed": failed,
        "unknown": unknown
    }