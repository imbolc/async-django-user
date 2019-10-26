import hmac
from hashlib import sha1
import logging


log = logging.getLogger(__name__)


class User(dict):
    def __init__(self, backend, session):
        self.backend = backend
        self.session = session
        self._loaded = False

    async def load(self):
        if not self._loaded:
            await self.reload()
        return self

    async def reload(self):
        log.debug("Load user from db")
        self.clear()
        self._loaded = True
        id = self.session.get(self.backend.session_id_key)
        if not id:
            log.debug("No user id in session")
            return
        row = await self.backend.load("id", int(id))
        if not row:
            log.debug("User not found in db")
            return
        if not row["is_active"]:
            log.debug("User isn't active")
            return
        self.update(**dict(row))
        return self

    async def authenticate(self, username: str, password: str) -> bool:
        """It checks credentials and populates the user if they're valid"""
        self.clear()
        self._loaded = True
        row = await self.backend.load(self.backend.username_field, username)
        if not row:
            log.debug("User not found in db")
            return
        log.debug("User found: %s", row["id"])
        if self.backend.check_password(password, row["password"]):
            log.debug("Wrong password")
            return
        self.update(**dict(row))
        await self.backend.update_last_login(self["id"])
        return self

    def login(self):
        """Saves the user's id in the session"""
        assert self._loaded
        backend = self.backend
        self.session[backend.session_id_key] = self["id"]
        self.session[backend.session_backend_key] = backend.session_backend_val
        self.session[backend.session_hash_key] = self._get_session_hash(
            self["password"]
        )

    def logout(self):
        self.clear()
        self.session.pop(self.backend.session_backend_key)
        self.session.pop(self.backend.session_hash_key)
        self.session.pop(self.backend.session_id_key)

    def _get_session_hash(self, password):
        return hmac.new(
            self.backend.salted_secret,
            msg=password.encode("utf-8"),
            digestmod=sha1,
        ).hexdigest()

    def set_password(self, raw_password):
        self["password"] = self.make_password(raw_password)
        self._password = raw_password

    def make_password(self, password, salt=None, hasher="default"):
        hasher = self.backend.get_hasher(hasher)
        salt = salt or hasher.salt()
        return hasher.encode(password, salt)
