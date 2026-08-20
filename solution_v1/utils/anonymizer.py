from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# Initialize engines
try:
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
except Exception as e:
    print(f"Failed to initialize Presidio: {e}")
    analyzer = None
    anonymizer = None

def redact_pii(text: str) -> str:
    """
    Redacts Personally Identifiable Information (PII) from the given text using Microsoft Presidio.
    If initialization fails, it returns the original text.
    """
    if analyzer is None or anonymizer is None:
        return text
    
    try:
        # Call analyzer to get results
        results = analyzer.analyze(text=text, entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "US_SSN"], language='en')
        
        # Analyzer results are passed to the AnonymizerEngine for redaction
        anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized_text.text
    except Exception as e:
        print(f"Redaction failed: {e}")
        return text
