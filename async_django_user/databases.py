from .base_backend import BaseBackend
from .utils import now_utc


class Backend(BaseBackend):
    def __init__(self, db, *args, **kwargs):
        self.db = db
        super().__init__(*args, **kwargs)

    async def load(self, key, val):
        sql = f"SELECT * FROM auth_user WHERE {key} = :val"
        return await self.db.fetch_one(sql, {"val": val})

    async def update_last_login(self, user_id):
        sql = "UPDATE auth_user SET last_login = :now WHERE id = :id"
        await self.db.execute(sql, {"now": now_utc(), "id": user_id})
