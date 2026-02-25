"""
OAuth2 provider configurations for cloud storage (OneDrive, Google Drive).
"""

CLOUD_OAUTH2_PROVIDERS = {
    "onedrive": {
        "display_name": "Microsoft OneDrive",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "Files.ReadWrite",
            "offline_access",
            "User.Read",
        ],
        "api_base": "https://graph.microsoft.com/v1.0",
        "connect_label": "Connect with Microsoft",
    },
    "google_drive": {
        "display_name": "Google Drive",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/drive.file",
        ],
        "api_base": "https://www.googleapis.com/drive/v3",
        "connect_label": "Connect with Google",
    },
}

# Email OAuth2 providers (for "Connect with Microsoft/Google" email login)
EMAIL_OAUTH2_PROVIDERS = {
    "gmail": {
        "display_name": "Google Gmail",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://mail.google.com/"],
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "connect_label": "Connect with Google",
    },
    "outlook": {
        "display_name": "Microsoft Outlook",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": [
            "https://outlook.office365.com/IMAP.AccessAsUser.All",
            "offline_access",
        ],
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "connect_label": "Connect with Microsoft",
    },
}
