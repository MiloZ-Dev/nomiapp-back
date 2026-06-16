"""Email sending service with Resend.

Sending must never block the business flow: if ``RESEND_API_KEY`` is not
configured or the send fails, the functions return ``False`` instead of
raising. User-facing content (HTML body, subjects) stays in Spanish.
"""

import base64

import resend

from app.core.config import settings


def init_resend() -> None:
    resend.api_key = settings.RESEND_API_KEY


async def send_pay_stub(
    employee_email: str,
    employee_name: str,
    company_name: str,
    period_start: str,
    period_end: str,
    pdf_bytes: bytes,
    net_pay: str,
) -> bool:
    """Sends the pay stub to the employee by email.

    Returns ``True`` on success, ``False`` on failure (must not block closing
    the payroll).
    """
    if not settings.RESEND_API_KEY:
        return False

    try:
        init_resend()

        filename = f"desprendible_{period_start}.pdf"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Inter, Arial, sans-serif; background: #f9fafb; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.07); }}
                .header {{ background: #4F46E5; padding: 32px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .header p {{ color: #C7D2FE; margin: 8px 0 0; font-size: 14px; }}
                .body {{ padding: 32px; }}
                .greeting {{ font-size: 16px; color: #111827; margin-bottom: 16px; }}
                .info-box {{ background: #F3F4F6; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .info-box p {{ margin: 4px 0; color: #374151; font-size: 14px; }}
                .neto {{ background: #ECFDF5; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
                .neto .label {{ color: #065F46; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
                .neto .value {{ color: #065F46; font-size: 32px; font-weight: 700; margin-top: 4px; }}
                .footer {{ background: #F9FAFB; padding: 24px; text-align: center; border-top: 1px solid #E5E7EB; }}
                .footer p {{ color: #9CA3AF; font-size: 12px; margin: 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>NomiApp</h1>
                    <p>Desprendible de Pago</p>
                </div>
                <div class="body">
                    <p class="greeting">Hola <strong>{employee_name}</strong>,</p>
                    <p style="color: #6B7280; font-size: 14px;">
                        Adjunto encontrarás tu desprendible de pago correspondiente al período:
                    </p>
                    <div class="info-box">
                        <p><strong>Empresa:</strong> {company_name}</p>
                        <p><strong>Período:</strong> {period_start} – {period_end}</p>
                    </div>
                    <div class="neto">
                        <div class="label">Neto a pagar</div>
                        <div class="value">{net_pay}</div>
                    </div>
                    <p style="color: #6B7280; font-size: 13px;">
                        El documento PDF adjunto contiene el detalle completo de
                        devengados y deducciones. Consérvalo como comprobante de pago.
                    </p>
                </div>
                <div class="footer">
                    <p>Este correo fue generado automáticamente por NomiApp</p>
                    <p>© 2026 NomiApp · Gestión de nómina inteligente</p>
                </div>
            </div>
        </body>
        </html>
        """

        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [employee_email],
            "subject": f"Desprendible de pago - {company_name} - {period_start}",
            "html": html_content,
            "attachments": [
                {
                    "filename": filename,
                    "content": list(base64.b64encode(pdf_bytes)),
                }
            ],
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[email] Error sending to {employee_email}: {e}")
        return False


async def send_welcome_email(
    admin_email: str,
    company_name: str,
    temporary_password: str,
) -> bool:
    """Sends a welcome email to the admin of a newly created company with their
    access credentials."""
    if not settings.RESEND_API_KEY:
        return False

    try:
        init_resend()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Inter, Arial, sans-serif; background: #f9fafb; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.07); }}
                .header {{ background: #4F46E5; padding: 32px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .header p {{ color: #C7D2FE; margin: 8px 0 0; font-size: 14px; }}
                .body {{ padding: 32px; }}
                .creds {{ background: #EEF2FF; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #4F46E5; }}
                .creds p {{ margin: 6px 0; color: #3730A3; font-size: 14px; }}
                .creds code {{ background: #C7D2FE; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 15px; }}
                .warning {{ background: #FFFBEB; border-radius: 8px; padding: 16px; margin: 20px 0; border-left: 4px solid #D97706; }}
                .warning p {{ margin: 0; color: #92400E; font-size: 13px; }}
                .footer {{ background: #F9FAFB; padding: 24px; text-align: center; border-top: 1px solid #E5E7EB; }}
                .footer p {{ color: #9CA3AF; font-size: 12px; margin: 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>NomiApp</h1>
                    <p>Bienvenido a tu plataforma de nómina</p>
                </div>
                <div class="body">
                    <p style="color: #111827; font-size: 16px;">
                        La empresa <strong>{company_name}</strong> ha sido registrada exitosamente en NomiApp.
                    </p>
                    <p style="color: #6B7280; font-size: 14px;">
                        A continuación encontrarás tus credenciales de acceso:
                    </p>
                    <div class="creds">
                        <p><strong>Usuario:</strong> <code>{admin_email}</code></p>
                        <p><strong>Contraseña temporal:</strong> <code>{temporary_password}</code></p>
                    </div>
                    <div class="warning">
                        <p>⚠️ <strong>Importante:</strong> Por seguridad, cambia tu contraseña
                        después de iniciar sesión por primera vez.</p>
                    </div>
                    <p style="color: #6B7280; font-size: 14px;">
                        Accede a tu plataforma en: <a href="https://nomiapp.co" style="color: #4F46E5;">nomiapp.co</a>
                    </p>
                </div>
                <div class="footer">
                    <p>Este correo fue generado automáticamente por NomiApp</p>
                    <p>© 2026 NomiApp · Gestión de nómina inteligente</p>
                </div>
            </div>
        </body>
        </html>
        """

        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [admin_email],
            "subject": f"Bienvenido a NomiApp - {company_name}",
            "html": html_content,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[email] Error sending welcome email: {e}")
        return False
