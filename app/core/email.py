import os
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "onboarding@resend.dev")
APP_NAME = os.environ.get("APP_NAME", "Nutrientrena")


def _send_resend(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        print("EMAIL ERROR: RESEND_API_KEY no configurado")
        return False
    try:
        resend.api_key = RESEND_API_KEY
        r = resend.Emails.send({
            "from": f"{APP_NAME} <{MAIL_FROM}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        print(f"EMAIL OK: enviado a {to} — id {r.get('id')}")
        return True
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        return False


def send_plan_email(
    to: str,
    client_name: str,
    diet: dict | None,
    routine: dict | None,
    coach_message: str = "",
) -> bool:
    diet_section = ""
    if diet:
        macros = ""
        if diet.get("detail"):
            d = diet["detail"]
            macros = f"""
            <tr>
              <td style="padding:12px 0; border-bottom:1px solid #f0f0f0;">
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" style="background:#f0fdf4;border-radius:8px;padding:12px;">
                      <div style="font-size:22px;font-weight:bold;color:#16a34a;">{int(diet.get('calories') or 0)}</div>
                      <div style="font-size:11px;color:#6b7280;">kcal/día</div>
                    </td>
                    <td width="12"></td>
                    <td align="center" style="background:#eff6ff;border-radius:8px;padding:12px;">
                      <div style="font-size:22px;font-weight:bold;color:#2563eb;">{int(d.get('proteins') or 0)}g</div>
                      <div style="font-size:11px;color:#6b7280;">Proteínas</div>
                    </td>
                    <td width="12"></td>
                    <td align="center" style="background:#fefce8;border-radius:8px;padding:12px;">
                      <div style="font-size:22px;font-weight:bold;color:#d97706;">{int(d.get('carbs') or 0)}g</div>
                      <div style="font-size:11px;color:#6b7280;">Carbos</div>
                    </td>
                    <td width="12"></td>
                    <td align="center" style="background:#fdf4ff;border-radius:8px;padding:12px;">
                      <div style="font-size:22px;font-weight:bold;color:#9333ea;">{int(d.get('fats') or 0)}g</div>
                      <div style="font-size:11px;color:#6b7280;">Grasas</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""

        foods_rows = ""
        for food in diet.get("foods", []):
            foods_rows += f"""
            <tr>
              <td style="padding:8px 0; border-bottom:1px solid #f9fafb; color:#374151; font-size:14px;">
                🍽️ {food.get('name', '')}
              </td>
            </tr>"""

        diet_section = f"""
        <tr>
          <td style="padding:24px 0 8px;">
            <h3 style="margin:0 0 12px;color:#16a34a;font-size:16px;">🥗 Plan Alimenticio</h3>
            <p style="margin:0 0 8px;color:#111827;font-weight:600;font-size:15px;">{diet.get('title', '')}</p>
            <table width="100%" cellpadding="0" cellspacing="0">{macros}</table>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">{foods_rows}</table>
          </td>
        </tr>"""

    routine_section = ""
    if routine:
        days_rows = ""
        for day in routine.get("days", []):
            days_rows += f"""
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #f9fafb;color:#374151;font-size:14px;">
                💪 {day.get('day_name', '')}
                {"— " + day.get('description','') if day.get('description') else ''}
              </td>
            </tr>"""

        routine_section = f"""
        <tr>
          <td style="padding:24px 0 8px;">
            <h3 style="margin:0 0 12px;color:#16a34a;font-size:16px;">🏋️ Plan de Entrenamiento</h3>
            <p style="margin:0 0 8px;color:#111827;font-weight:600;font-size:15px;">
              {routine.get('name', '')}
              {"&nbsp;·&nbsp;" + str(routine.get('days_count','')) + " días/semana" if routine.get('days_count') else ""}
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">{days_rows}</table>
          </td>
        </tr>"""

    coach_block = ""
    if coach_message:
        coach_block = f"""
        <tr>
          <td style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px;border-radius:0 8px 8px 0;margin:16px 0;">
            <p style="margin:0 0 4px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Mensaje de tu coach</p>
            <p style="margin:0;color:#111827;font-size:15px;line-height:1.6;">{coach_message}</p>
          </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; margin:0; padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 0;">
            <table width="600" style="background:#ffffff;border-radius:8px;overflow:hidden;">
              <tr>
                <td style="background:#16a34a;padding:32px;text-align:center;">
                  <h1 style="color:#ffffff;margin:0;font-size:24px;">{APP_NAME}</h1>
                  <p style="color:#bbf7d0;margin:8px 0 0;font-size:14px;">Tu plan personalizado está listo</p>
                </td>
              </tr>
              <tr>
                <td style="padding:32px;">
                  <h2 style="color:#111827;margin:0 0 8px;">Hola, {client_name} 👋</h2>
                  <p style="color:#6b7280;font-size:15px;line-height:1.6;margin:0 0 24px;">
                    Tu coach ha preparado un plan personalizado para ayudarte a alcanzar tus objetivos.
                    A continuación encontrarás los detalles de tu programa.
                  </p>
                  <table width="100%" cellpadding="0" cellspacing="0">
                    {coach_block}
                    {diet_section}
                    {routine_section}
                  </table>
                  <div style="text-align:center;margin:32px 0 0;">
                    <p style="color:#6b7280;font-size:14px;margin:0;">
                      ¡Mucho ánimo! Estamos aquí para apoyarte en cada paso del camino. 💪
                    </p>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="background:#f9fafb;padding:24px 32px;text-align:center;">
                  <p style="color:#9ca3af;font-size:12px;margin:0;">
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
    return _send_resend(to, f"Tu plan personalizado está listo — {APP_NAME}", html)


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
                    Recibimos una solicitud para restablecer la contrasena de tu cuenta.
                    Haz clic en el boton de abajo para crear una nueva contrasena.
                  </p>
                  <div style="text-align:center; margin:32px 0;">
                    <a href="{reset_link}"
                       style="background:#16a34a; color:#ffffff; padding:14px 32px;
                              border-radius:6px; text-decoration:none; font-size:16px;
                              font-weight:bold; display:inline-block;">
                      Restablecer contrasena
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
    return _send_resend(to, f"Restablecer contrasena - {APP_NAME}", html)
