"""
Email Sender for RCA Reports
Sends email with report attachments (requires SMTP configuration)
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime


def generate_report_email_body(snapshot_id, snapshot_name, conclusion, report_filename):
    """
    Generate HTML email body for RCA report

    Args:
        snapshot_id: Analysis snapshot ID
        snapshot_name: Human-readable name
        conclusion: Final conclusion text
        report_filename: Name of attached report file

    Returns:
        str: HTML email body
    """
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background-color: #0066cc; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            .footer {{ background-color: #f0f0f0; padding: 10px; font-size: 12px; color: #666; }}
            .conclusion {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #0066cc; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>TEP Root Cause Analysis Report</h1>
        </div>

        <div class="content">
            <h2>Analysis Complete</h2>

            <p><strong>Analysis ID:</strong> {snapshot_id}</p>
            <p><strong>Name:</strong> {snapshot_name}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h3>Final Conclusion</h3>
            <div class="conclusion">
                <p>{conclusion}</p>
            </div>

            <h3>Attached Report</h3>
            <p>Please find the complete RCA report attached: <strong>{report_filename}</strong></p>

            <p>The report includes:</p>
            <ul>
                <li>Feature-based analysis</li>
                <li>AI model analyses</li>
                <li>Interactive discussion with RAG assistant</li>
                <li>Final conclusion and recommendations</li>
            </ul>
        </div>

        <div class="footer">
            <p>This report was generated automatically by the TEP RCA System.</p>
            <p>For questions, contact: tep-rca-system@example.com</p>
        </div>
    </body>
    </html>
    """
    return html


def send_report_email(recipient, subject, body_html, attachments=None):
    """
    Send email with report attachment

    Args:
        recipient: Email recipient address
        subject: Email subject line
        body_html: HTML email body
        attachments: List of file paths to attach

    Returns:
        bool: True if email sent successfully, False otherwise

    Note:
        This requires SMTP server configuration.
        For production, configure SMTP settings in environment variables or config file.
    """
    try:
        # Check if SMTP is configured
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = os.environ.get('SMTP_PORT', 587)
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        smtp_from = os.environ.get('SMTP_FROM', 'tep-rca-system@example.com')

        if not all([smtp_server, smtp_username, smtp_password]):
            print("⚠️ SMTP not configured. Email not sent.")
            print("   To enable email sending, set environment variables:")
            print("   - SMTP_SERVER (e.g., smtp.gmail.com)")
            print("   - SMTP_PORT (default: 587)")
            print("   - SMTP_USERNAME")
            print("   - SMTP_PASSWORD")
            print("   - SMTP_FROM (optional)")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg['Subject'] = subject

        # Attach HTML body
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)

        # Attach files
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        file_data = f.read()
                        filename = os.path.basename(filepath)

                        attachment = MIMEApplication(file_data)
                        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(attachment)
                else:
                    print(f"⚠️ Attachment not found: {filepath}")

        # Send email
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        print(f"✅ Email sent to {recipient}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Test email generation (doesn't send)
    html_body = generate_report_email_body(
        snapshot_id=1729123456789,
        snapshot_name="Test Analysis",
        conclusion="Test conclusion for report",
        report_filename="RCA_Report_Test.md"
    )

    print("Generated email body:")
    print(html_body)

    print("\n" + "="*50)
    print("To test email sending, configure SMTP environment variables")
