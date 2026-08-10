import re
import logging

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
IP_REGEX = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
KEY_REGEX = re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?')

class PIIService:
    def __init__(self):
        self.analyzer = None
        self.anonymizer = None
        
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.info("Microsoft Presidio initialized successfully.")
        except Exception:
            logger.debug("Presidio engines not installed. Using regex PII redaction fallback.")

    def anonymize_text(self, text: str) -> str:
        """
        Scans the text for PII entities (email, phone, crypto, ip, API keys) and redacts them.
        """
        if not text:
            return text
            
        if self.analyzer and self.anonymizer:
            try:
                results = self.analyzer.analyze(text=text, language='en')
                if results:
                    anonymized_result = self.anonymizer.anonymize(
                        text=text,
                        analyzer_results=results
                    )
                    return anonymized_result.text
            except Exception as e:
                logger.error(f"Failed during Presidio PII anonymization: {e}")
            
        # Regex Fallback
        scrubbed = EMAIL_REGEX.sub("<EMAIL_REDACTED>", text)
        scrubbed = IP_REGEX.sub("<IP_REDACTED>", scrubbed)
        scrubbed = KEY_REGEX.sub(r'\1: <SECRET_REDACTED>', scrubbed)
        return scrubbed

pii_service = PIIService()
