"""Contract data extraction service using Claude AI.

STATUS: Structure ready, disabled until ANTHROPIC_API_KEY is configured.
"""

import io
import json

import anthropic
from pypdf import PdfReader

from app.core.config import settings

AI_ENABLED = bool(settings.ANTHROPIC_API_KEY)

EXTRACTION_PROMPT = """
Analiza el siguiente contrato laboral colombiano y extrae la información del empleado.
Responde ÚNICAMENTE con un JSON válido, sin texto adicional, sin backticks.

Campos a extraer:
{{
  "first_name": "",
  "middle_name": "",
  "last_name": "",
  "second_last_name": "",
  "document_type": "CC",
  "document_number": "",
  "birth_date": "YYYY-MM-DD o null",
  "gender": "M o F o null",
  "address": "",
  "city": "",
  "department": "",
  "email": "",
  "phone": "",
  "position": "",
  "area": "",
  "hire_date": "YYYY-MM-DD o null",
  "contract_type": "fixed_term o indefinite o work_contract",
  "base_salary": 0,
  "payment_frequency": "monthly o biweekly o weekly",
  "end_date": "YYYY-MM-DD o null",
  "work_schedule": "Completa o Medio tiempo",
  "weekly_hours": 48,
  "work_location": "",
  "modality": "Presencial o Remoto o Híbrido",
  "eps": "",
  "afp": "",
  "arl": "",
  "compensation_fund": "",
  "notes": ""
}}

Si un campo no está en el contrato, usa null o el valor por defecto indicado.
Para base_salary, extraer solo el número sin puntos ni comas.

CONTRATO:
{contract_text}
"""


async def extract_contract_data(pdf_text: str) -> dict:
    """Extracts employee data from a contract PDF text.

    If ANTHROPIC_API_KEY is not configured, returns a dict indicating that AI
    is not available so the frontend shows an empty form.
    """
    if not AI_ENABLED:
        return {
            "ai_available": False,
            "message": "Extracción AI no disponible. Complete el formulario manualmente.",
            "data": {},
        }

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(contract_text=pdf_text[:8000]),
                }
            ],
        )

        text = message.content[0].text.strip()
        data = json.loads(text)

        return {
            "ai_available": True,
            "data": data,
            "confidence": "high" if len(pdf_text) > 500 else "low",
        }
    except Exception as e:
        print(f"[ai] Error extracting data: {e}")
        return {
            "ai_available": True,
            "data": {},
            "error": str(e),
        }


async def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extracts plain text from a PDF using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception as e:
        print(f"[ai] Error extracting PDF text: {e}")
        return ""
