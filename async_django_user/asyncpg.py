from .base_backend import BaseBackend


class Backend(BaseBackend):
    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        super().__init__(*args, **kwargs)

    async def load(self, key, val):
        async with self.pool.acquire() as con:
            sql = f"SELECT * FROM auth_user WHERE {key} = $1"
            return await con.fetchrow(sql, val)

    async def save(self, key, value, expire_date):
        async with self.pool.acquire() as con:
            if key:
                return await self._update(con, key, value, expire_date)
            return await self._insert_new(con, value, expire_date)
