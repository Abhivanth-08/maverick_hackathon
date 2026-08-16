import io
import re
from typing import Tuple, List
from PIL import Image
import pypdf
import docx
from backend.app.privacy.presidio_service import PresidioService

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpg"
}

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

class ReportProcessorService:
    def __init__(self):
        self._presidio = None

    @property
    def presidio(self):
        if self._presidio is None:
            self._presidio = PresidioService.get_instance()
        return self._presidio

    def validate_file(self, filename: str, content_type: str, file_size: int) -> Tuple[bool, str]:
        if file_size > MAX_FILE_SIZE_BYTES:
            return False, f"File size ({round(file_size / (1024 * 1024), 1)}MB) exceeds maximum limit of 20MB."
        
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type '{ext}'. Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG."
        
        return True, "File valid"

    def extract_text(self, file_bytes: bytes, filename: str, content_type: str) -> Tuple[str, bool, str]:
        """
        Extracts raw text from uploaded document bytes.
        Returns (extracted_text, ocr_applied, document_type).
        """
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        ocr_applied = False
        text_content = ""

        if ext == "pdf" or "pdf" in content_type:
            text_content, ocr_applied = self._extract_from_pdf(file_bytes)
        elif ext == "docx" or "wordprocessingml" in content_type:
            text_content = self._extract_from_docx(file_bytes)
        elif ext in ["png", "jpg", "jpeg"] or "image" in content_type:
            text_content = self._extract_from_image(file_bytes)
            ocr_applied = True
        elif ext == "txt" or "text" in content_type:
            try:
                text_content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text_content = file_bytes.decode("latin-1", errors="ignore")
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        if not text_content or not text_content.strip():
            raise ValueError("Unable to extract text from this report. Document may be empty or corrupted.")

        doc_type = self._detect_document_type(text_content)
        return text_content.strip(), ocr_applied, doc_type

    def _extract_from_pdf(self, file_bytes: bytes) -> Tuple[str, bool]:
        ocr_applied = False
        text_lines = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_lines.append(f"--- Page {i + 1} ---\n" + page_text.strip())
        except Exception:
            pass

        full_text = "\n\n".join(text_lines)
        if len(full_text.strip()) < 50:
            # Fallback to OCR if PDF has scanned images / no selectable text
            ocr_text = self._try_ocr_pdf(file_bytes)
            if ocr_text and len(ocr_text.strip()) > 20:
                full_text = ocr_text
                ocr_applied = True

        return full_text, ocr_applied

    def _extract_from_docx(self, file_bytes: bytes) -> str:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_from_image(self, file_bytes: bytes) -> str:
        try:
            import pytesseract
            img = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            raise ValueError("Unable to perform OCR on image. Tesseract engine may be missing or file unreadable.")

    def _try_ocr_pdf(self, file_bytes: bytes) -> str:
        try:
            import pytesseract
            # If pdf2image or pillow rendering is available
            img = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img)
        except Exception:
            return ""

    def _detect_document_type(self, text: str) -> str:
        lower = text.lower()
        if "pathology" in lower or "histology" in lower or "biopsy" in lower:
            return "Pathology Report"
        if "discharge summary" in lower:
            return "Discharge Summary"
        if "laboratory" in lower or "lab report" in lower or "creatinine" in lower:
            return "Laboratory Report"
        if "oncology" in lower or "chemotherapy" in lower or "radiation" in lower:
            return "Oncology Report"
        if "radiology" in lower or "ct scan" in lower or "mri" in lower:
            return "Radiology Report"
        return "Clinical Report"

    def anonymize_for_ai(self, text: str) -> str:
        """Minimizes PII (SSNs, emails, phone numbers, names) prior to external AI processing."""
        redacted = text
        # Redact SSN
        redacted = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', redacted)
        # Redact Email
        redacted = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED EMAIL]', redacted)
        # Redact Phone
        redacted = re.sub(r'\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b', '[REDACTED PHONE]', redacted)
        
        is_avail, init_err = self.presidio.is_available()
        if not is_avail:
            raise RuntimeError(init_err or "PII anonymization service is unavailable. Install the configured spaCy model.")

        res = self.presidio.anonymize(redacted)
        return res.get("text", redacted)
