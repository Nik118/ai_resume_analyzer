import io
import pdfplumber
import docx

def parse_pdf(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def parse_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith('.pdf'):
        return parse_pdf(file_bytes)
    elif filename.lower().endswith('.docx'):
        return parse_docx(file_bytes)
    else:
        # Fallback to plain text decoding if it's text
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError(f"Unsupported file format for {filename}")
