import os
import urllib.request
import urllib.error
import json


RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "onboarding@resend.dev")
APP_NAME = os.environ.get("APP_NAME", "Nutrientrena")


def _send_resend(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        return False
    payload = json.dumps({
        "from": f"{APP_NAME} <{MAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False


def send_recover_password_email(to: str, name: str, token: str) -> bool:
    reset_link = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; margin:0; padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding: 40px 0;">
            <table width="600" style="background:#ffffff; border-radius:8px; overflow:hidden;">
              <tr>
                <td style="background:#16a34a; padding:32px; text-align:center;">
                  <h1 style="color:#ffffff; margin:0; font-size:24px;">{APP_NAME}</h1>
                </td>
              </tr>
              <tr>
                <td style="padding:40px 32px;">
                  <h2 style="color:#111827; margin:0 0 16px;">Hola, {name}</h2>
                  <p style="color:#6b7280; font-size:16px; line-height:1.6; margin:0 0 24px;">
                    Recibimos una solicitud para restablecer la contraseña de tu cuenta.
                    Haz clic en el botón de abajo para crear una nueva contraseña.
                  </p>
                  <div style="text-align:center; margin:32px 0;">
                    <a href="{reset_link}"
                       style="background:#16a34a; color:#ffffff; padding:14px 32px;
                              border-radius:6px; text-decoration:none; font-size:16px;
                              font-weight:bold; display:inline-block;">
                      Restablecer contraseña
                    </a>
                  </div>
                  <p style="color:#9ca3af; font-size:14px; margin:24px 0 0;">
                    Este enlace expira en 60 minutos. Si no solicitaste esto, ignora este correo.
                  </p>
                </td>
              </tr>
              <tr>
                <td style="background:#f9fafb; padding:24px 32px; text-align:center;">
                  <p style="color:#9ca3af; font-size:12px; margin:0;">
                    &copy; 2025 {APP_NAME}. Todos los derechos reservados.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    return _send_resend(to, f"Restablecer contraseña — {APP_NAME}", html)
