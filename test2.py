import smtplib

def send_email(subject, body, to_email):
    # Define email parameters
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587  # Usually 587 for TLS, 465 for SSL, and 25 for non-secure connections
    SMTP_USER = "your-email@example.com"
    SMTP_PASSWORD = "your-password"

    # Construct the email content
    from_email = SMTP_USER
    email_text = f"From: {from_email}\nTo: {to_email}\nSubject: {subject}\n\n{body}"

    try:
        # Set up the SMTP client
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(from_email, to_email, email_text)
        server.close()
        
        print("Email sent!")
    except Exception as e:
        print(f"Error: {e}")

# Test sending an email
send_email("Test Subject", "This is the body of the email.", 'matthew.gundersen@goalzero.com')