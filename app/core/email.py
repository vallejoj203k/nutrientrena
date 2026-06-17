import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAIL_FROM      = os.environ.get("MAIL_FROM", "onboarding@resend.dev")
APP_NAME       = os.environ.get("APP_NAME", "Nutrientrena")

GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def _send_gmail(to: str, subject: str, html: str) -> tuple[bool, str]:
    """Send via Gmail SMTP using an App Password. Returns (ok, error)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{APP_NAME} <{GMAIL_USER}>"
        msg["To"]      = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(GMAIL_USER, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_USER, [to], msg.as_string())

        print(f"EMAIL OK (Gmail): enviado a {to}")
        return True, ""
    except Exception as e:
        msg_err = str(e)
        print(f"EMAIL ERROR (Gmail) to {to}: {msg_err}")
        return False, msg_err


def _send_resend(to: str, subject: str, html: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    if not RESEND_API_KEY:
        msg = "RESEND_API_KEY no configurado"
        print(f"EMAIL ERROR: {msg}")
        return False, msg
    try:
        resend.api_key = RESEND_API_KEY
        r = resend.Emails.send({
            "from": f"{APP_NAME} <{MAIL_FROM}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        email_id = r.get("id") if isinstance(r, dict) else getattr(r, "id", str(r))
        print(f"EMAIL OK (Resend): enviado a {to} — id {email_id}")
        return True, ""
    except Exception as e:
        msg = str(e)
        print(f"EMAIL ERROR (Resend) to {to}: {msg}")
        return False, msg


def _send(to: str, subject: str, html: str) -> tuple[bool, str]:
    """Use Gmail if configured, otherwise fall back to Resend."""
    if GMAIL_USER and GMAIL_PASSWORD:
        return _send_gmail(to, subject, html)
    return _send_resend(to, subject, html)


def send_plan_email(
    to: str,
    client_name: str,
    diet: dict | None,
    routine: dict | None,
    coach_message: str = "",
    loom_link: str = "",
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
                    <td align="center" style="background:#F3EEFF;border-radius:8px;padding:12px;">
                      <div style="font-size:22px;font-weight:bold;color:#5B2D8E;">{int(diet.get('calories') or 0)}</div>
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
                      <div style="font-size:22px;font-weight:bold;color:#7C3AED;">{int(d.get('fats') or 0)}g</div>
                      <div style="font-size:11px;color:#6b7280;">Grasas</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""

        foods_rows = ""
        for food in diet.get("foods", []):
            aliments_html = ""
            for al in food.get("aliments", []):
                qty = f"{int(al['quantity'])}g" if al.get("quantity") else ""
                kcal = f" · {int(al['calories'])} kcal" if al.get("calories") else ""
                aliments_html += f"""
                <tr>
                  <td style="padding:3px 0 3px 16px;color:#6B7280;font-size:13px;">
                    &bull; {al.get('name','')}{' ' + qty if qty else ''}{kcal}
                  </td>
                </tr>"""
            foods_rows += f"""
            <tr>
              <td style="padding:8px 0 4px; border-top:1px solid #f0f0f0;">
                <span style="color:#111827;font-size:14px;font-weight:600;">🍽️ {food.get('name', '')}</span>
                <table width="100%" cellpadding="0" cellspacing="0">{aliments_html}</table>
              </td>
            </tr>"""

        diet_section = f"""
        <tr>
          <td style="padding:24px 0 8px;">
            <h3 style="margin:0 0 12px;color:#5B2D8E;font-size:16px;">🥗 Plan Alimenticio</h3>
            <p style="margin:0 0 8px;color:#111827;font-weight:600;font-size:15px;">{diet.get('title', '')}</p>
            <table width="100%" cellpadding="0" cellspacing="0">{macros}</table>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">{foods_rows}</table>
          </td>
        </tr>"""

    routine_section = ""
    if routine:
        days_rows = ""
        for day in routine.get("days", []):
            exercises = day.get("exercises", [])
            ex_html = ""
            for ex in exercises:
                parts = []
                if ex.get("series"):      parts.append(f"{ex['series']} series")
                if ex.get("repetitions"): parts.append(f"{ex['repetitions']} reps")
                if ex.get("break_time"):  parts.append(f"{ex['break_time']}s descanso")
                detail_str = " · ".join(parts)
                ex_html += f"""
                <tr>
                  <td style="padding:3px 0 3px 16px;color:#6B7280;font-size:13px;">
                    &bull; {ex.get('name','')}{' — ' + detail_str if detail_str else ''}
                  </td>
                </tr>"""
            desc = day.get('description','')
            if not exercises and desc:
                ex_html = f'<tr><td style="padding:3px 0 3px 16px;color:#6B7280;font-size:13px;">{desc}</td></tr>'
            days_rows += f"""
            <tr>
              <td style="padding:8px 0 4px;border-top:1px solid #f0f0f0;">
                <span style="color:#111827;font-size:14px;font-weight:600;">💪 {day.get('day_name', '')}</span>
                <table width="100%" cellpadding="0" cellspacing="0">{ex_html}</table>
              </td>
            </tr>"""

        routine_section = f"""
        <tr>
          <td style="padding:24px 0 8px;">
            <h3 style="margin:0 0 12px;color:#5B2D8E;font-size:16px;">🏋️ Plan de Entrenamiento</h3>
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
          <td style="background:#F3EEFF;border-left:4px solid #5B2D8E;padding:16px;border-radius:0 8px 8px 0;margin-bottom:16px;">
            <p style="margin:0 0 4px;font-size:12px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">Mensaje de tu coach</p>
            <p style="margin:0;color:#111827;font-size:15px;line-height:1.6;">{coach_message}</p>
          </td>
        </tr>"""

    loom_block = ""
    if loom_link:
        loom_block = f"""
        <tr>
          <td style="padding:20px 0 8px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#F3EEFF;border-radius:10px;padding:20px;text-align:center;">
                  <p style="margin:0 0 6px;font-size:12px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">Video explicativo de tu coach</p>
                  <p style="margin:0 0 14px;color:#374151;font-size:14px;line-height:1.5;">
                    Tu coach ha grabado un video para explicarte el plan en detalle.
                  </p>
                  <a href="{loom_link}"
                     style="background:#5B2D8E;color:#ffffff;padding:11px 28px;
                            border-radius:8px;text-decoration:none;font-size:14px;
                            font-weight:700;display:inline-block;">
                    🎬 Ver video
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f4f4; margin:0; padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 0;">
            <table width="600" style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
              <tr>
                <td style="background:#5B2D8E;padding:32px;text-align:center;">
                  <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:800;letter-spacing:.5px;">{APP_NAME}</h1>
                  <p style="color:#C084FC;margin:8px 0 0;font-size:14px;">Tu plan personalizado está listo</p>
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
                    {loom_block}
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
    return _send(to, f"Tu plan personalizado está listo — {APP_NAME}", html)


def send_recover_password_email(to: str, name: str, token: str) -> bool:
    reset_link = f"{os.environ.get('FRONTEND_URL', 'https://nutrientrena-production.up.railway.app/app')}/reset-password.html?token={token}"
    body = f"""
    <p style="color:#6B7280;font-size:15px;line-height:1.7;margin:0 0 20px;">
      Hola <strong>{name}</strong>,<br><br>
      Recibimos una solicitud para restablecer la contraseña de tu cuenta.
      Haz clic en el botón de abajo para crear una nueva contraseña.
    </p>
    <div style="text-align:center;margin:32px 0;">
      <a href="{reset_link}"
         style="background:#5B2D8E;color:#ffffff;padding:14px 36px;
                border-radius:8px;text-decoration:none;font-size:15px;
                font-weight:700;display:inline-block;letter-spacing:.3px;">
        Restablecer contraseña
      </a>
    </div>
    <p style="color:#9CA3AF;font-size:13px;margin:24px 0 0;text-align:center;">
      Este enlace expira en 60 minutos.<br>
      Si no solicitaste esto, puedes ignorar este correo.
    </p>"""
    html = _base_notification_html("🔐 Restablecer contraseña", body)
    ok, _ = _send(to, f"Restablecer contraseña — {APP_NAME}", html)
    return ok


# ── Notification emails ────────────────────────────────────────────────────────

def _base_notification_html(title: str, body_html: str) -> str:
    """Shared wrapper for all internal notification emails."""
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 0;">
      <table width="560" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        <tr>
          <td style="background:#5B2D8E;padding:28px 32px;">
            <h1 style="color:#fff;margin:0;font-size:20px;font-weight:800;letter-spacing:.5px;">
              {APP_NAME}
            </h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="color:#111827;margin:0 0 16px;font-size:18px;">{title}</h2>
            {body_html}
          </td>
        </tr>
        <tr>
          <td style="background:#F9FAFB;padding:16px 32px;text-align:center;">
            <p style="color:#9CA3AF;font-size:11px;margin:0;">&copy; 2025 {APP_NAME}</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def notify_coach_form_submitted(
    coach_email: str,
    coach_name: str,
    client_name: str,
    client_email: str,
) -> bool:
    """Notify coach when a client submits their intake form."""
    body = f"""
    <p style="color:#6B7280;font-size:15px;line-height:1.7;margin:0 0 20px;">
      Hola <strong>{coach_name}</strong>,<br><br>
      Tu cliente <strong>{client_name}</strong> ({client_email}) acaba de enviar
      su formulario de onboarding.
    </p>
    <div style="background:#F0EBF8;border-left:4px solid #5B2D8E;padding:16px;border-radius:0 8px 8px 0;margin-bottom:24px;">
      <p style="margin:0;color:#5B2D8E;font-weight:600;font-size:14px;">
        ✅ Estado actualizado → Formulario recibido
      </p>
      <p style="margin:8px 0 0;color:#6B7280;font-size:13px;">
        Ya puedes revisar sus respuestas y comenzar a preparar el plan.
      </p>
    </div>
    <p style="color:#9CA3AF;font-size:13px;margin:0;">
      Este es un aviso automático de {APP_NAME}.
    </p>"""
    html = _base_notification_html(
        "📋 Formulario recibido de un cliente",
        body,
    )
    ok, _ = _send(
        coach_email,
        f"{client_name} envió su formulario — {APP_NAME}",
        html,
    )
    return ok


def send_form_link_email(
    to: str,
    client_name: str,
    form_link: str,
    coach_name: str = "",
) -> bool:
    """Send the public intake form link to a new client."""
    greeting = f"Hola <strong>{client_name}</strong>," if client_name else "Hola,"
    coach_line = f"Tu coach <strong>{coach_name}</strong> te ha enviado" if coach_name else "Te han enviado"
    body = f"""
    <p style="color:#6B7280;font-size:15px;line-height:1.7;margin:0 0 20px;">
      {greeting}<br><br>
      {coach_line} un formulario de evaluación inicial. Por favor, complétalo
      para que podamos preparar tu plan personalizado.
    </p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{form_link}"
         style="display:inline-block;padding:14px 32px;background:#5B2D8E;color:#fff;
                text-decoration:none;border-radius:10px;font-weight:700;font-size:15px;
                letter-spacing:.3px;">
        Completar formulario →
      </a>
    </div>
    <p style="color:#9CA3AF;font-size:13px;margin:0;text-align:center;">
      Este enlace es personal. No lo compartas con nadie.
    </p>"""
    html = _base_notification_html("📋 Completa tu formulario de evaluación", body)
    ok, _ = _send(to, f"Tu formulario de evaluación — {APP_NAME}", html)
    return ok


def notify_coach_checkin(
    coach_email: str,
    coach_name: str,
    client_name: str,
    checkin_date: str,
    weight: float | None,
) -> bool:
    """Notify coach when a client registers a weekly check-in."""
    weight_line = (
        f'<p style="color:#374151;font-size:15px;margin:8px 0 0;">⚖️ Peso registrado: <strong>{weight} kg</strong></p>'
        if weight else ""
    )
    body = f"""
    <p style="color:#6B7280;font-size:15px;line-height:1.7;margin:0 0 20px;">
      Hola <strong>{coach_name}</strong>,<br><br>
      Tu cliente <strong>{client_name}</strong> ha registrado su check-in semanal.
    </p>
    <div style="background:#F0EBF8;border-left:4px solid #5B2D8E;padding:16px;border-radius:0 8px 8px 0;margin-bottom:24px;">
      <p style="color:#5B2D8E;font-weight:600;font-size:14px;margin:0;">
        📅 Fecha: {checkin_date}
      </p>
      {weight_line}
    </div>
    <p style="color:#9CA3AF;font-size:13px;margin:0;">
      Entra a la plataforma para revisar su progreso y dejar tus notas.
    </p>"""
    html = _base_notification_html(
        f"📊 Nuevo check-in de {client_name}",
        body,
    )
    ok, _ = _send(
        coach_email,
        f"Nuevo check-in de {client_name} — {APP_NAME}",
        html,
    )
    return ok


def notify_client_coach_notes(
    client_email: str,
    client_name: str,
    coach_name: str,
    notes: str,
) -> bool:
    """Notify client when coach leaves notes on their check-in."""
    body = f"""
    <p style="color:#6B7280;font-size:15px;line-height:1.7;margin:0 0 20px;">
      Hola <strong>{client_name}</strong>,<br><br>
      Tu coach <strong>{coach_name}</strong> ha dejado comentarios en tu último check-in.
    </p>
    <div style="background:#F0EBF8;border-left:4px solid #5B2D8E;padding:20px;border-radius:0 8px 8px 0;margin-bottom:24px;">
      <p style="margin:0 0 6px;font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">
        Mensaje de tu coach
      </p>
      <p style="margin:0;color:#111827;font-size:15px;line-height:1.7;">{notes}</p>
    </div>
    <p style="color:#9CA3AF;font-size:13px;margin:0;">
      Sigue así, ¡vas por buen camino! 💪
    </p>"""
    html = _base_notification_html(
        "💬 Tu coach te ha dejado un mensaje",
        body,
    )
    ok, _ = _send(
        client_email,
        f"Mensaje de tu coach {coach_name} — {APP_NAME}",
        html,
    )
    return ok
