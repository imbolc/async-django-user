from .base_backend import BaseBackend
from .utils import now_utc


class Backend(BaseBackend):
    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        super().__init__(*args, **kwargs)

    async def load(self, key, val):
        async with self.pool.acquire() as con:
            sql = f"SELECT * FROM auth_user WHERE {key} = $1"
            return await con.fetchrow(sql, val)

    async def update_last_login(self, user_id):
        async with self.pool.acquire() as con:
            sql = f"UPDATE auth_user SET last_login = $1 WHERE id = $2"
            await con.execute(sql, now_utc(), user_id)
