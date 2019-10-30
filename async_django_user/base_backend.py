from hashlib import sha1

from .user import User
from . import hashers


class BaseBackend:
    def __init__(
        self,
        secret,
        *,
        password_hashers=[
            hashers.PBKDF2PasswordHasher,
            hashers.PBKDF2SHA1PasswordHasher,
            hashers.Argon2PasswordHasher,
            hashers.BCryptSHA256PasswordHasher,
        ],
        session_backend_key="_auth_user_backend",
        session_backend_val="django.contrib.auth.backends.ModelBackend",
        session_hash_key="_auth_user_hash",
        session_hash_salt="django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash",  # noqa
        session_id_key="_auth_user_id",
        username_field="username",
        users_table="auth_user",
    ):
        self.secret = secret
        self.session_backend_key = session_backend_key
        self.session_backend_val = session_backend_val
        self.session_hash_key = session_hash_key
        self.session_id_key = session_id_key
        self.salted_secret = sha1(
            (session_hash_salt + secret).encode("utf-8")
        ).digest()
        self.hashers = [cls() for cls in password_hashers]
        self.hashers_by_algorithm = {h.algorithm: h for h in self.hashers}
        self.username_field = username_field
        self.users_table = users_table

    def get_user_from_session(self, session):
        return User.get_from_session(self, session)

    def get_hasher(self, algorithm="default"):
        if hasattr(algorithm, "algorithm"):
            return algorithm
        elif algorithm == "default":
            return self.hashers[0]
        else:
            return self.hashers_by_algorithm[algorithm]

    def identify_hasher(self, encoded):
        algorithm = encoded.split("$", 1)[0]
        return self.get_hasher(algorithm)

    def check_password(self, raw, encoded) -> bool:
        hasher = self.identify_hasher(encoded)
        return hasher.verify(raw, encoded)
