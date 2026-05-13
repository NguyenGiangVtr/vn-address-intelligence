import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.core.config import Config

logger = logging.getLogger("VNAI_EmailService")

def send_verification_email(to_email: str, code: str):
    """
    Sends a verification code to the specified email address.
    """
    if not Config.SMTP_USER or not Config.SMTP_PASS:
        logger.warning(f"SMTP not configured. Skipping email to {to_email}. Code: {code}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = f"[{code}] Mã xác thực đăng ký VN Address Intelligence"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px;">
                <h2 style="color: #2563eb;">Chào mừng bạn đến với VN Address Intelligence</h2>
                <p>Bạn đang thực hiện đăng ký tài khoản mới. Vui lòng sử dụng mã xác thực dưới đây để hoàn tất quy trình:</p>
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0;">
                    <span style="font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #1e40af;">{code}</span>
                </div>
                <p>Mã này sẽ hết hạn sau 10 phút. Nếu bạn không yêu cầu đăng ký này, vui lòng bỏ qua email này.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">Đây là email tự động, vui lòng không trả lời.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        # Envelope (MAIL FROM / RCPT TO) explicit so recipients match the registrant;
        # some servers otherwise only deliver to the authenticated mailbox.
        envelope_from = Config.SMTP_USER
        envelope_to = [to_email]

        # 465 = implicit TLS (SMTPS); 587 and most others = plain then STARTTLS
        if int(Config.SMTP_PORT) == 465:
            with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.login(Config.SMTP_USER, Config.SMTP_PASS)
                server.send_message(msg, from_addr=envelope_from, to_addrs=envelope_to)
        else:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASS)
                server.send_message(msg, from_addr=envelope_from, to_addrs=envelope_to)
        
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
