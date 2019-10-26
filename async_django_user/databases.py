from .utils import new_session_key
from .base_backend import BaseBackend


class Backend(BaseBackend):
    def __init__(self, db, *args, **kwargs):
        self.db = db
        super().__init__(*args, **kwargs)

    async def load(self, key):
        sql = "SELECT * FROM django_session WHERE session_key = :key"
        return await (self.db.fetch_one(sql, {"key": key}))

    async def save(self, key, value, expire_date):
        if key:
            return await (self._update(key, value, expire_date))
        else:
            return await (self._insert_new(value, expire_date))

    async def _insert_new(self, value, expire_date):
        sql = """
            INSERT INTO django_session (
                session_key,
                session_data,
                expire_date,
            ) VALUES (:key, :value, :expire_date)
        """
        while True:
            key = new_session_key()
            try:
                await self.db.execute(
                    sql,
                    {"key": key, "value": value, "expire_date": expire_date},
                )
            except Exception:
                continue
            break
        return key

    async def _update(self, key, value, expire_date):
        sql = """
            UPDATE django_session
            SET session_data = :value, expire_date = :expire_date
            WHERE session_key = :key
        """
        await self.db.fetch_one(
            sql, {"key": key, "value": value, "expire_date": expire_date}
        )
        return key
