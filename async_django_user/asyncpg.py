from .base_backend import BaseBackend


class Backend(BaseBackend):
    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        super().__init__(*args, **kwargs)

    async def load(self, key, val):
        sql = f"SELECT * FROM {self.users_table} WHERE {key} = $1"
        async with self.pool.acquire() as con:
            return await con.fetchrow(sql, val)

    async def update_by_id(self, id, **changes):
        print("UP", id, changes)
        sql, params = update_by_id_sql(self.users_table, id, changes)
        async with self.pool.acquire() as con:
            return await con.execute(sql, *params)

    async def insert(self, **fields):
        sql, params = insert_sql(self.users_table, fields)
        async with self.pool.acquire() as con:
            return await con.fetchval(sql, *params)


def update_by_id_sql(table: str, id: int, changes: dict) -> (str, list):
    """
    >>> update_by_id_sql('tbl', 1, {'foo': 2, 'bar': 3})
    ('UPDATE tbl SET foo=$2, bar=$3 WHERE id=$1', [1, 2, 3])
    """
    sets = ", ".join(f"{k}=${i}" for i, k in enumerate(changes.keys(), 2))
    sql = f"UPDATE {table} SET {sets} WHERE id=$1"
    return sql, [id] + list(changes.values())


def insert_sql(table: str, fields: dict) -> (str, list):
    """
    >>> insert_sql('tbl', {'foo': 'bar', 'id': 1})
    ('INSERT INTO tbl (foo, id) VALUES ($1, $2) RETURNING id', ['bar', 1])
    """
    keys = ", ".join(fields.keys())
    placeholders = ", ".join(f"${i}" for i in range(1, len(fields) + 1))
    sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders}) RETURNING id"
    return sql, list(fields.values())
