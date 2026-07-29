import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    # Deployment can rotate Django SECRET_KEY only with a coordinated data-key
    # migration. A dedicated assessment key can replace this derivation later.
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_json(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _fernet().encrypt(payload).decode("ascii")


def decrypt_json(token):
    return json.loads(_fernet().decrypt(token.encode("ascii")).decode())
