"""File storage service over Supabase Storage.

Uses the official ``supabase-py`` library to upload/delete each company's logo
and employee documents in the configured bucket (``settings.SUPABASE_BUCKET``).
"""

from supabase import Client, create_client

from app.core.config import settings


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _extension_for(content_type: str) -> str:
    return "png" if "png" in (content_type or "").lower() else "jpg"


async def upload_logo(company_id: str, file_bytes: bytes, content_type: str) -> str:
    """Uploads the logo to the bucket and returns the public URL.

    Path: ``logos/{company_id}/logo.{extension}``. If the file already exists
    it is replaced (upsert).
    """
    supabase = get_supabase()
    extension = _extension_for(content_type)
    path = f"logos/{company_id}/logo.{extension}"

    # Upsert: replaces the file if it already exists.
    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)


async def delete_logo(company_id: str) -> None:
    supabase = get_supabase()
    paths = [f"logos/{company_id}/logo.png", f"logos/{company_id}/logo.jpg"]
    supabase.storage.from_(settings.SUPABASE_BUCKET).remove(paths)


async def upload_employee_photo(
    company_id: str, employee_id: str, file_bytes: bytes, content_type: str
) -> str:
    """Uploads the employee photo and returns the public URL.

    Path: ``employees/{company_id}/{employee_id}/photo.{extension}`` (upsert).
    """
    supabase = get_supabase()
    extension = _extension_for(content_type)
    path = f"employees/{company_id}/{employee_id}/photo.{extension}"

    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)


async def upload_employee_contract(
    company_id: str, employee_id: str, file_bytes: bytes
) -> str:
    """Uploads the employee contract PDF and returns the public URL.

    Path: ``employees/{company_id}/{employee_id}/contract.pdf`` (upsert).
    """
    supabase = get_supabase()
    path = f"employees/{company_id}/{employee_id}/contract.pdf"

    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
        path,
        file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)
