import hmac
from hashlib import sha1
import logging

from .utils import now_utc


log = logging.getLogger(__name__)


class User(dict):
    _loaded = False
    session = {}

    def __init__(self, backend):
        self.backend = backend

    @classmethod
    def get_by_id(cls, backend, id):
        user = cls(backend)
        user["id"] = id
        return user

    @classmethod
    def get_from_session(cls, backend, session):
        user = cls(backend)
        user.session = session
        if backend.session_id_key in session:
            user["id"] = int(session[backend.session_id_key])
        return user

    async def load(self):
        if not self._loaded:
            await self.reload()
        return self

    async def reload(self):
        log.debug("Load user from db")
        self._loaded = True
        id = self.get("id")
        if not id:
            log.debug("It's a new user without an id")
            return
        row = await self.backend.find_one(id=id)
        if not row:
            log.debug("User not found in db")
            return
        self.clear()
        self.update(**dict(row))
        return self

    def save(self, fields: list = None):
        assert "id" in self
        data = {k: self[k] for k in fields} if fields else self
        return self.backend.update_by_id(self["id"], **data)

    async def create(self):
        """It doesn't catch any exception the database layer can throw"""
        assert self.backend.username_field in self
        assert "password" in self
        self.setdefault("date_joined", now_utc())
        self.setdefault("is_superuser", False)
        self.setdefault("is_staff", False)
        self.setdefault("is_active", True)
        self["id"] = await self.backend.insert(**self)

    async def authenticate(self, username: str, password: str):
        """
        It checks credentials and populates the user if they're valid.
        It doesn't check if the user is active.
        """
        self._loaded = True
        data = await self.backend.find_one(
            **{self.backend.username_field: username})
        if not data:
            log.debug("User not found in db")
            return
        log.debug("User found: %s", data["id"])
        if not self.backend.check_password(password, data["password"]):
            log.debug("Wrong password")
            return
        self.clear()
        self.update(**dict(data))
        await self.backend.update_by_id(self["id"], last_login=now_utc())
        return self

    def login(self):
        """Saves the user's id in the session"""
        backend = self.backend
        self.session[backend.session_id_key] = self["id"]
        self.session[backend.session_backend_key] = backend.session_backend_val
        self.session[backend.session_hash_key] = self._get_session_hash(
            self["password"]
        )

    def logout(self):
        self.clear()
        self.session.pop(self.backend.session_backend_key, None)
        self.session.pop(self.backend.session_hash_key, None)
        self.session.pop(self.backend.session_id_key, None)

    def _get_session_hash(self, password):
        return hmac.new(
            self.backend.salted_secret,
            msg=password.encode("utf-8"),
            digestmod=sha1,
        ).hexdigest()

    def set_password(self, raw_password):
        self["password"] = self.make_password(raw_password)

    def make_password(self, password, salt=None, hasher="default"):
        hasher = self.backend.get_hasher(hasher)
        salt = salt or hasher.salt()
        return hasher.encode(password, salt)
