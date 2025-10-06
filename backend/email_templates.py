"""
FTV Email Templates - Consistent HTML Email Design

This module provides unified HTML email templates that match the FTV frontend design.
All email functions should use these templates for consistent branding and styling.
"""

def get_base_email_template(
    title: str,
    content: str,
    button_text: str = None,
    button_url: str = None,
    footer_text: str = None
) -> str:
    """
    Generate the base HTML email template matching FTV frontend design.
    
    Args:
        title: Email title/subject for header
        content: Main email content (HTML or plain text)
        button_text: Optional button text (e.g., "Bejelentkezés", "Jelszó visszaállítása")
        button_url: Optional button URL
        footer_text: Optional custom footer text
        
    Returns:
        Complete HTML email string
    """
    # Default footer if none provided
    if footer_text is None:
        footer_text = "Ez egy automatikus email, kérjük ne válaszoljon rá."
    
    # Optional button HTML
    button_html = ""
    if button_text and button_url:
        button_html = f"""
        <div style="text-align: center; margin: 40px 0;">
            <a href="{button_url}" 
               style="display: inline-block; 
                      padding: 16px 32px; 
                      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                      color: white !important; 
                      text-decoration: none; 
                      border-radius: 12px; 
                      font-weight: 700;
                      font-size: 16px;
                      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                      transition: all 0.2s ease;
                      letter-spacing: 0.5px;">
                {button_text}
            </a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="hu">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                margin: 0;
                padding: 20px 0;
            }}
            
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
                border-radius: 16px;
                overflow: hidden;
            }}
            
            .email-header {{
                background: linear-gradient(135deg, #0f1419 0%, #1a202c 50%, #2d3748 100%);
                color: #ffffff;
                padding: 50px 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .email-header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                           radial-gradient(circle at 70% 80%, rgba(37, 99, 235, 0.08) 0%, transparent 50%);
                pointer-events: none;
            }}
            
            .logo-section {{
                margin-bottom: 20px;
                position: relative;
                z-index: 1;
            }}
            
            .logo-text {{
                font-size: 48px;
                font-weight: 900;
                color: #ffffff;
                text-decoration: none;
                letter-spacing: 3px;
                display: inline-flex;
                align-items: center;
                gap: 12px;
            }}
            
            .logo-text::before {{
                content: '📺';
                font-size: 40px;
                color: #3b82f6;
                filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
            }}
            
            .platform-subtitle {{
                font-size: 14px;
                color: #94a3b8;
                margin-top: 8px;
                font-weight: 500;
                letter-spacing: 1px;
            }}
            
            .email-title {{
                font-size: 28px;
                font-weight: 700;
                margin-top: 30px;
                color: #ffffff;
                position: relative;
                z-index: 1;
            }}
            
            .email-content {{
                padding: 50px 40px;
                background-color: #ffffff;
                position: relative;
            }}
            
            .content-section {{
                margin-bottom: 25px;
            }}
            
            .content-section h2 {{
                color: #1e293b;
                font-size: 20px;
                font-weight: 700;
                margin-bottom: 16px;
                padding-bottom: 8px;
                border-bottom: 3px solid #3b82f6;
                position: relative;
            }}
            
            .content-section h2::after {{
                content: '';
                position: absolute;
                bottom: -3px;
                left: 0;
                width: 40px;
                height: 3px;
                background: linear-gradient(90deg, #3b82f6, #1d4ed8);
                border-radius: 2px;
            }}
            
            .content-section p {{
                margin-bottom: 16px;
                color: #475569;
                line-height: 1.7;
                font-size: 16px;
            }}
            
            .info-box {{
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                border: 1px solid #e2e8f0;
                border-left: 5px solid #3b82f6;
                padding: 24px;
                margin: 24px 0;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            }}
            
            .info-box h3 {{
                color: #1e293b;
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
            }}
            
            .info-box h3::before {{
                content: '📋';
                margin-right: 8px;
                font-size: 16px;
            }}
            
            .info-item {{
                margin-bottom: 12px;
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .info-item:last-child {{
                border-bottom: none;
                margin-bottom: 0;
            }}
            
            .info-item strong {{
                color: #374151;
                font-weight: 600;
                min-width: 120px;
            }}
            
            .highlight-box {{
                background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
                border: 1px solid #93c5fd;
                padding: 24px;
                margin: 24px 0;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
            }}
            
            .highlight-box h3 {{
                color: #1e40af;
                font-size: 20px;
                font-weight: 700;
                margin-bottom: 12px;
            }}
            
            .highlight-box p {{
                color: #1e40af;
                font-weight: 600;
                margin: 0;
            }}
            
            .warning-box {{
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                border: 1px solid #f59e0b;
                border-left: 5px solid #f59e0b;
                padding: 20px;
                margin: 24px 0;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
            }}
            
            .warning-box p {{
                color: #92400e;
                margin: 0;
                font-weight: 500;
            }}
            
            .success-box {{
                background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                border: 1px solid #10b981;
                border-left: 5px solid #10b981;
                padding: 20px;
                margin: 24px 0;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
            }}
            
            .success-box p {{
                color: #065f46;
                margin: 0;
                font-weight: 500;
            }}
            
            .email-footer {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #94a3b8;
                padding: 40px 30px;
                text-align: center;
            }}
            
            .footer-content {{
                font-size: 14px;
                line-height: 1.6;
            }}
            
            .footer-links {{
                margin-top: 20px;
            }}
            
            .footer-links a {{
                color: #3b82f6;
                text-decoration: none;
                margin: 0 15px;
                font-weight: 500;
                transition: color 0.2s ease;
            }}
            
            .footer-links a:hover {{
                color: #60a5fa;
                text-decoration: underline;
            }}
            
            .copyright {{
                margin-top: 24px;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #334155;
                padding-top: 20px;
            }}
            
            @media (max-width: 600px) {{
                .email-container {{
                    margin: 0;
                    box-shadow: none;
                }}
                
                .email-content {{
                    padding: 20px 15px;
                }}
                
                .email-header {{
                    padding: 20px 15px;
                }}
                
                .logo-text {{
                    font-size: 28px;
                }}
                
                .email-title {{
                    font-size: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <!-- Header -->
            <div class="email-header">
                <div class="logo-section">
                    <div class="logo-text">FTV</div>
                    <div class="platform-subtitle">Hiányzás Áttekintő Platform</div>
                </div>
                <div class="email-title">{title}</div>
            </div>
            
            <!-- Content -->
            <div class="email-content">
                {content}
                {button_html}
            </div>
            
            <!-- Footer -->
            <div class="email-footer">
                <div class="footer-content">
                    <p>{footer_text}</p>
                    
                    <div class="footer-links">
                        <a href="https://ftv.szlg.info">FTV Rendszer</a>
                        <a href="https://szlgbp.hu">Az Iskola honlapja</a>
                    </div>
                    
                    <div class="copyright">
                        © 2025 FTV - Minden jog fenntartva.
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def get_announcement_email_content(announcement, author_name: str) -> str:
    """
    Generate HTML content for announcement emails.
    
    Args:
        announcement: Announcement model instance
        author_name: Full name of the announcement author
        
    Returns:
        HTML content for announcement email
    """
    return f"""
    <div class="content-section">
        <h2>📢 Új közlemény érkezett</h2>
        <p>Kedves Kolléga!</p>
        <p>Új közleményt tettek közzé az FTV rendszerben.</p>
    </div>
    
    <div class="info-box">
        <h3>{announcement.title}</h3>
        <div class="info-item"><strong>Szerző:</strong> {author_name}</div>
        <div class="info-item"><strong>Dátum:</strong> {announcement.created_at.strftime('%Y. %m. %d. %H:%M')}</div>
    </div>
    
    <div class="content-section">
        <h2>Tartalom</h2>
        <p>{announcement.body}</p>
    </div>
    
    <div class="warning-box">
        <p><strong>Figyelem:</strong> A teljes közlemény és esetleges csatolmányok megtekintéséhez látogassa meg a FTV rendszert.</p>
    </div>
    """


def get_assignment_addition_email_content(forgatas, contact_person_name: str) -> str:
    """
    Generate HTML content for filming assignment addition emails.
    
    Args:
        forgatas: Forgatas model instance
        contact_person_name: Name of the contact person
        
    Returns:
        HTML content for assignment addition email
    """
    return f"""
    <div class="content-section">
        <h2>🎬 Új beosztás</h2>
        <p>Kedves Kolléga!</p>
        <p>Önt beosztották a következő forgatáshoz:</p>
    </div>
    
    <div class="highlight-box">
        <h3>{forgatas.name}</h3>
        <p><strong>Kérjük, készüljön fel a megadott időpontra!</strong></p>
    </div>
    
    <div class="info-box">
        <h3>Forgatás részletei</h3>
        <div class="info-item"><strong>Név:</strong> {forgatas.name}</div>
        <div class="info-item"><strong>Leírás:</strong> {forgatas.description or 'Nincs megadva'}</div>
        <div class="info-item"><strong>Dátum:</strong> {forgatas.date.strftime('%Y. %m. %d.')}</div>
        <div class="info-item"><strong>Időpont:</strong> {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}</div>
        <div class="info-item"><strong>Helyszín:</strong> {forgatas.location or 'Nincs megadva'}</div>
        <div class="info-item"><strong>Kapcsolattartó:</strong> {contact_person_name}</div>
    </div>
    
    <div class="content-section">
        <p>Kérjük, jegyezze fel a forgatás részleteit és készüljön fel a megadott időpontra!</p>
        <p>További információkért és részletekért látogassa meg a FTV rendszert.</p>
    </div>
    """


def get_assignment_removal_email_content(forgatas, contact_person_name: str) -> str:
    """
    Generate HTML content for filming assignment removal emails.
    
    Args:
        forgatas: Forgatas model instance
        contact_person_name: Name of the contact person
        
    Returns:
        HTML content for assignment removal email
    """
    return f"""
    <div class="content-section">
        <h2>🎬 Forgatási beosztás módosítás</h2>
        <p>Kedves Kolléga!</p>
        <p>Tájékoztatjuk, hogy a következő forgatásból törölték Önt:</p>
    </div>
    
    <div class="info-box">
        <h3>Törölt forgatás részletei</h3>
        <div class="info-item"><strong>Név:</strong> {forgatas.name}</div>
        <div class="info-item"><strong>Dátum:</strong> {forgatas.date.strftime('%Y. %m. %d.')}</div>
        <div class="info-item"><strong>Időpont:</strong> {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}</div>
        <div class="info-item"><strong>Helyszín:</strong> {forgatas.location or 'Nincs megadva'}</div>
        <div class="info-item"><strong>Kapcsolattartó:</strong> {contact_person_name}</div>
    </div>
    
    <div class="content-section">
        <p>Ez azt jelenti, hogy már nincs szüksége részt vennie ezen a forgatáson.</p>
        <p>Ha kérdése van a változással kapcsolatban, kérjük vegye fel a kapcsolatot a médiatanáraival!</p>
    </div>
    """


def get_password_reset_email_content(user_name: str, reset_url: str) -> str:
    """
    Generate HTML content for password reset emails.
    
    Args:
        user_name: User's full name or username
        reset_url: Password reset URL
        
    Returns:
        HTML content for password reset email
    """
    return f"""
    <div class="content-section">
        <h2>🔐 Jelszó visszaállítása</h2>
        <p>Kedves {user_name}!</p>
        <p>Jelszó visszaállítási kérelmet kaptunk az Ön FTV fiókjához.</p>
    </div>
    
    <div class="info-box">
        <h3>Jelszó visszaállítása</h3>
        <p>Amennyiben Ön kérte a jelszó visszaállítást, kattintson az alábbi gombra:</p>
    </div>
    
    <div class="warning-box">
        <p><strong>Fontos információk:</strong></p>
        <p>• Ez a link 1 órán belül lejár</p>
        <p>• A link biztonságosan kódolt (csak a szerver tudja dekódolni)</p>
        <p>• Ha nem Ön kérte a jelszó visszaállítást, hagyja figyelmen kívül ezt az emailt</p>
    </div>
    
    <div class="content-section">
        <p>Ha nem tudja használni a gombot, másolja be a következő linket a böngészőjébe:</p>
        <p style="word-break: break-all; color: #007bff;">{reset_url}</p>
    </div>
    """


def get_first_login_email_content(user_name: str, login_url: str) -> str:
    """
    Generate HTML content for first login emails.
    
    Args:
        user_name: User's full name or username
        login_url: First login URL with token
        
    Returns:
        HTML content for first login email
    """
    return f"""
    <div class="content-section">
        <h2>🎉 Üdvözöljük az FTV rendszerben!</h2>
        <p>Kedves {user_name}!</p>
        <p>Fiókját sikeresen létrehoztuk az FTV rendszerben. Most már hozzáférhet az összes funkcióhoz!</p>
    </div>
    
    <div class="highlight-box">
        <h3>Első bejelentkezés</h3>
        <p>Kattintson az alábbi gombra a biztonságos bejelentkezéshez és jelszó beállításához.</p>
    </div>
    
    <div class="info-box">
        <h3>Mit tehet a rendszerben?</h3>
        <div class="info-item">• Forgatások és események megtekintése</div>
        <div class="info-item">• Személyes profil kezelése</div>
        <div class="info-item">• Közlemények olvasása</div>
        <div class="info-item">• Beoszás és határidők követése</div>
    </div>
    
    <div class="warning-box">
        <p><strong>Első bejelentkezés után:</strong> Kérjük, állítson be egy erős, egyedi jelszót a fiókja biztonságának érdekében.</p>
    </div>
    """


def get_login_info_email_content(user_name: str, username: str, password: str) -> str:
    """
    Generate HTML content for login info emails (admin generated passwords).
    
    Args:
        user_name: User's full name or username
        username: Login username
        password: Generated password
        
    Returns:
        HTML content for login info email
    """
    return f"""
    <div class="content-section">
        <h2>🔐 Új bejelentkezési adatok</h2>
        <p>Kedves {user_name}!</p>
        <p>Új jelszót generáltunk az Ön FTV rendszerbeli fiókjához.</p>
    </div>
    
    <div class="highlight-box">
        <h3>Bejelentkezési adatok</h3>
        <div style="text-align: left; margin-top: 15px;">
            <div style="margin: 10px 0; font-size: 16px;">
                <strong>Felhasználónév:</strong> {username}
            </div>
            <div style="margin: 10px 0; font-size: 16px;">
                <strong>Új jelszó:</strong> 
                <span style="background-color: rgba(255,255,255,0.2); 
                             padding: 5px 10px; 
                             border-radius: 4px; 
                             font-family: 'Courier New', monospace; 
                             font-size: 18px; 
                             font-weight: bold;">
                    {password}
                </span>
            </div>
        </div>
    </div>
    
    <div class="warning-box">
        <p><strong>FONTOS BIZTONSÁGI TUDNIVALÓK:</strong></p>
        <p>• Kérjük, változtassa meg a jelszót első bejelentkezéskor</p>
        <p>• Használjon erős, egyedi jelszót</p>
        <p>• Ne ossza meg senkivel a bejelentkezési adatait</p>
        <p>• Tartsa biztonságban ezt az emailt</p>
    </div>
    
    <div class="content-section">
        <p>Ha kérdése van, vagy problémája adódna, kérjük vegye fel a kapcsolatot az adminisztrátorral.</p>
    </div>
    """


def get_forgatas_creation_email_content(forgatas, creator_name: str) -> str:
    """
    Generate HTML content for new Forgatás creation notification emails.
    
    Args:
        forgatas: Forgatas model instance
        creator_name: Full name of the person who created the Forgatás
        
    Returns:
        HTML content for Forgatás creation notification email
    """
    # Format forgatas type in Hungarian
    forgatas_type_display = {
        'kacsa': 'KaCsa',
        'rendes': 'Rendes',
        'rendezveny': 'Rendezvény',
        'egyeb': 'Egyéb'
    }.get(forgatas.forgTipus, forgatas.forgTipus)
    
    return f"""
    <div class="content-section">
        <h2>🎬 Új forgatás létrehozva</h2>
        <p>Kedves Médiatanár!</p>
        <p>Új forgatást hoztak létre az FTV rendszerben.</p>
    </div>
    
    <div class="highlight-box">
        <h3>{forgatas.name}</h3>
        <p><strong>Új forgatás érkezett a rendszerbe!</strong></p>
    </div>
    
    <div class="info-box">
        <h3>Forgatás részletei</h3>
        <div class="info-item"><strong>Név:</strong> {forgatas.name}</div>
        <div class="info-item"><strong>Leírás:</strong> {forgatas.description or 'Nincs megadva'}</div>
        <div class="info-item"><strong>Típus:</strong> {forgatas_type_display}</div>
        <div class="info-item"><strong>Dátum:</strong> {forgatas.date.strftime('%Y. %m. %d.')}</div>
        <div class="info-item"><strong>Időpont:</strong> {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}</div>
        <div class="info-item"><strong>Helyszín:</strong> {forgatas.location.name if forgatas.location else 'Nincs megadva'}</div>
        <div class="info-item"><strong>Kapcsolattartó:</strong> {forgatas.contactPerson.name if forgatas.contactPerson else 'Nincs megadva'}</div>
        <div class="info-item"><strong>Létrehozta:</strong> {creator_name}</div>
        <div class="info-item"><strong>Tanév:</strong> {forgatas.tanev if forgatas.tanev else 'Nincs megadva'}</div>
    </div>
    
    {f'''<div class="content-section">
        <h2>További megjegyzések</h2>
        <p>{forgatas.notes}</p>
    </div>''' if forgatas.notes else ''}
    
    <div class="content-section">
        <p>Kérjük, tekintse át az új forgatás részleteit és szükség esetén vegye fel a kapcsolatot a létrehozójával vagy a kapcsolattartóval.</p>
        <p>A teljes információk és a beosztások kezeléséhez látogassa meg a FTV rendszert.</p>
    </div>
    
    <div class="warning-box">
        <p><strong>Figyelem:</strong> Ez egy automatikus értesítés az új forgatás létrehozásáról. A forgatás részletei változhatnak a véglegesítésig.</p>
    </div>
    """


def send_html_emails_to_multiple_recipients(
    subject: str,
    html_content: str,
    plain_content: str,
    recipient_emails: list,
    from_email: str = None
) -> tuple[int, list]:
    """
    Send HTML emails to multiple recipients using individual send_mail calls.
    This replaces send_mass_mail to support HTML content.
    
    Args:
        subject: Email subject
        html_content: HTML email content
        plain_content: Plain text fallback content
        recipient_emails: List of email addresses
        from_email: Sender email (uses DEFAULT_FROM_EMAIL if None)
        
    Returns:
        Tuple of (successful_count, failed_emails)
    """
    from django.core.mail import send_mail
    from django.conf import settings
    import time
    
    print(f"[EMAIL_DEBUG] ========== EMAIL SENDING DEBUG START ==========")
    print(f"[EMAIL_DEBUG] Function: send_html_emails_to_multiple_recipients")
    print(f"[EMAIL_DEBUG] Recipients count: {len(recipient_emails)}")
    print(f"[EMAIL_DEBUG] Subject: {subject}")
    print(f"[EMAIL_DEBUG] Recipients: {recipient_emails}")
    
    # Debug email configuration
    print(f"[EMAIL_CONFIG] EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'NOT SET')}")
    print(f"[EMAIL_CONFIG] EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
    print(f"[EMAIL_CONFIG] EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
    print(f"[EMAIL_CONFIG] EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
    print(f"[EMAIL_CONFIG] EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
    print(f"[EMAIL_CONFIG] EMAIL_HOST_PASSWORD: {'SET' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET'}")
    print(f"[EMAIL_CONFIG] DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
    
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    print(f"[EMAIL_DEBUG] Using from_email: {from_email}")
    
    successful_count = 0
    failed_emails = []
    
    print(f"[EMAIL_DEBUG] Starting individual email sending...")
    
    for i, email_address in enumerate(recipient_emails):
        try:
            print(f"[EMAIL_DEBUG] ===== Sending email {i+1}/{len(recipient_emails)} =====")
            print(f"[EMAIL_DEBUG] Recipient: {email_address}")
            print(f"[EMAIL_DEBUG] From: {from_email}")
            print(f"[EMAIL_DEBUG] Subject: {subject}")
            print(f"[EMAIL_DEBUG] HTML content length: {len(html_content)} chars")
            print(f"[EMAIL_DEBUG] Plain content length: {len(plain_content)} chars")
            
            print(f"[EMAIL_DEBUG] Calling Django send_mail...")
            
            send_mail(
                subject=subject,
                message=plain_content,
                html_message=html_content,
                from_email=from_email,
                recipient_list=[email_address],
                fail_silently=False,
            )
            
            successful_count += 1
            print(f"[EMAIL_SUCCESS] ✅ Email sent successfully to {email_address}")
            
            # Small delay to prevent overwhelming SMTP server
            if i < len(recipient_emails) - 1:  # Don't delay after the last email
                print(f"[EMAIL_DEBUG] Waiting 0.1 seconds before next email...")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[EMAIL_ERROR] ❌ Failed to send email to {email_address}")
            print(f"[EMAIL_ERROR] Error type: {type(e).__name__}")
            print(f"[EMAIL_ERROR] Error message: {str(e)}")
            
            # Add specific debugging for common email errors
            error_str = str(e).lower()
            if "connection refused" in error_str:
                print(f"[EMAIL_ERROR] 🔧 DIAGNOSIS: SMTP server connection refused")
                print(f"[EMAIL_ERROR] - Check EMAIL_HOST and EMAIL_PORT settings")
                print(f"[EMAIL_ERROR] - Verify network connectivity to SMTP server")
            elif "authentication failed" in error_str or "invalid credentials" in error_str:
                print(f"[EMAIL_ERROR] 🔧 DIAGNOSIS: Authentication failed")
                print(f"[EMAIL_ERROR] - Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
                print(f"[EMAIL_ERROR] - For Gmail, ensure you're using an App Password")
            elif "tls" in error_str or "ssl" in error_str:
                print(f"[EMAIL_ERROR] 🔧 DIAGNOSIS: TLS/SSL connection issue")
                print(f"[EMAIL_ERROR] - Check EMAIL_USE_TLS setting")
                print(f"[EMAIL_ERROR] - Verify SMTP server supports TLS on this port")
            elif "timeout" in error_str:
                print(f"[EMAIL_ERROR] 🔧 DIAGNOSIS: Connection timeout")
                print(f"[EMAIL_ERROR] - Check network connectivity")
                print(f"[EMAIL_ERROR] - SMTP server may be temporarily unavailable")
            
            import traceback
            print(f"[EMAIL_ERROR] Full traceback:")
            print(traceback.format_exc())
            
            failed_emails.append(email_address)
    
    print(f"[EMAIL_SUMMARY] ========== EMAIL SENDING SUMMARY ==========")
    print(f"[EMAIL_SUMMARY] Total recipients: {len(recipient_emails)}")
    print(f"[EMAIL_SUMMARY] Successful: {successful_count}")
    print(f"[EMAIL_SUMMARY] Failed: {len(failed_emails)}")
    if failed_emails:
        print(f"[EMAIL_SUMMARY] Failed emails: {failed_emails}")
    print(f"[EMAIL_DEBUG] ========== EMAIL SENDING DEBUG END ==========")
    
    return successful_count, failed_emails