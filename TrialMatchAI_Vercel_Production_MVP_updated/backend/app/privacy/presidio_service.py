import logging
import spacy
from typing import Tuple, Optional

logger = logging.getLogger("trialmatch.presidio")

MODEL_NAME = "en_core_web_sm"

class PresidioService:
    _instance: Optional["PresidioService"] = None

    def __init__(self):
        self.enabled = False
        self.init_error = ""
        self.analyzer = None
        self.anonymizer = None
        self.spacy_model = MODEL_NAME

        try:
            if not spacy.util.is_package(MODEL_NAME):
                self.init_error = (
                    f"spaCy model '{MODEL_NAME}' is not installed. "
                    f"Install it with: python -m spacy download {MODEL_NAME}"
                )
                logger.error(f"Presidio initialization failed: {self.init_error}")
                return

            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": MODEL_NAME}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self.anonymizer = AnonymizerEngine()
            self.enabled = True
            logger.info(f"PresidioService initialized successfully with spaCy model '{MODEL_NAME}'.")
        except Exception as e:
            self.enabled = False
            self.init_error = f"Presidio initialization error: {str(e)}"
            logger.error(self.init_error)

    @classmethod
    def get_instance(cls) -> "PresidioService":
        if cls._instance is None:
            cls._instance = PresidioService()
        return cls._instance

    def is_available(self) -> Tuple[bool, str]:
        return self.enabled, self.init_error

    def anonymize(self, text: str) -> dict:
        if not self.enabled:
            raise RuntimeError(
                self.init_error or "PII anonymization service is unavailable. Install the configured spaCy model."
            )
        results = self.analyzer.analyze(text=text, language="en")
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        return {
            "text": anonymized.text,
            "entities": [
                {"type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
                for r in results
            ],
            "enabled": True,
        }
