from .base_backend import BaseBackend


class Backend(BaseBackend):
    def __init__(self, pool, *args, **kwargs):
        self.pool = pool
        super().__init__(*args, **kwargs)

    async def find_one(self, **filters):
        sql, params = select_sql(self.users_table, filters)
        async with self.pool.acquire() as con:
            return await con.fetchrow(sql, *params)

    async def update_by_id(self, id, **changes):
        sql, params = update_by_id_sql(self.users_table, id, changes)
        async with self.pool.acquire() as con:
            return await con.execute(sql, *params)

    async def insert(self, **fields):
        sql, params = insert_sql(self.users_table, fields)
        async with self.pool.acquire() as con:
            return await con.fetchval(sql, *params)


def select_sql(table: str, filters: dict) -> (str, list):
    """
    >>> select_sql('tbl', {'foo': 1, 'bar': 2})
    ('SELECT * FROM tbl WHERE foo=$1 AND bar=$2', [1, 2])
    """
    where = " AND ".join(f"{k}=${i}" for i, k in enumerate(filters.keys(), 1))
    sql = f"SELECT * FROM {table} WHERE {where}"
    return sql, list(filters.values())


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
