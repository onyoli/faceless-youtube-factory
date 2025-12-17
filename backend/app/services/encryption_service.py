"""
Encryption service for securing OAuth tokens.
Uses Fernet symmetric encryption.
"""
from cryptography.fernet import Fernet
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self):
        """Initialze with key from settings."""
        if not settings.token_encryption_key:
            # Fallback for dev only
            self.fernet = Fernet(Fernet.generate_key())
        else:
            self.fernet = Fernet(settings.token_encryption_key.encode())

    def encrypt(self, text: str) -> str:
        """Encrypt a string."""
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a token."""
        if not token:
            return ""
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception:
            return ""
    
# Singleton instance
encryption_service = EncryptionService()