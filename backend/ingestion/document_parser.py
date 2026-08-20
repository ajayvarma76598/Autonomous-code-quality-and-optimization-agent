import logging
import os

logger = logging.getLogger(__name__)


class DocumentParser:
    def __init__(self):
        self.api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self.parser = None
        if self.api_key:
            try:
                from llama_parse import LlamaParse

                self.parser = LlamaParse(
                    api_key=self.api_key,
                    result_type="text",
                    tier="cost_effective",
                    verbose=False,
                    language="en",
                )
            except Exception as e:
                logger.warning(f"LlamaParse initialization skipped: {e}")

    def parse_document(self, file_path: str) -> str:
        """
        Parses a document (PDF, Image) using PyMuPDF and LlamaParse fallback,
        returning markdown text.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found at path: {file_path}")

        # 1. Primary: Use PyMuPDF (fitz) for fast, reliable local PDF text extraction
        if file_path.lower().endswith(".pdf"):
            try:
                logger.info(
                    f"[DocumentParser] Attempting PyMuPDF local extraction for {os.path.basename(file_path)}..."
                )
                import fitz

                doc = fitz.open(file_path)
                pages_text = []
                for i, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        pages_text.append(f"## Page {i + 1}\n\n{text.strip()}")
                extracted_text = "\n\n".join(pages_text)
                doc.close()
                if extracted_text.strip():
                    logger.info(
                        f"[DocumentParser] PyMuPDF successfully extracted {len(extracted_text)} chars from {os.path.basename(file_path)}"
                    )
                    return extracted_text
            except Exception as pdf_err:
                logger.warning(
                    f"[DocumentParser] PyMuPDF parsing failed for {file_path}: {pdf_err}"
                )

        # 2. Fallback: Use LlamaParse if PyMuPDF extracted no text
        if self.parser:
            try:
                logger.info(
                    f"[DocumentParser] Calling LlamaParse Cloud API fallback for {os.path.basename(file_path)}..."
                )
                documents = self.parser.load_data(file_path)
                parsed_parts = []
                for doc in documents:
                    if hasattr(doc, "text") and doc.text:
                        parsed_parts.append(str(doc.text))
                    elif isinstance(doc, dict) and "text" in doc:
                        parsed_parts.append(str(doc["text"]))
                    elif isinstance(doc, str):
                        parsed_parts.append(doc)
                extracted_llama = "\n\n".join(parsed_parts)
                logger.info(
                    f"[DocumentParser] LlamaParse extracted {len(extracted_llama)} chars from {os.path.basename(file_path)}"
                )
                return extracted_llama
            except Exception as e:
                logger.warning(
                    f"[DocumentParser] LlamaParse failed for {file_path}: {e}"
                )

        return ""


document_parser = DocumentParser()
