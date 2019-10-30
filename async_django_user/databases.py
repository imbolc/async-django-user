from .base_backend import BaseBackend


class Backend(BaseBackend):
    def __init__(self, db, *args, **kwargs):
        self.db = db
        super().__init__(*args, **kwargs)

    async def load(self, key, val):
        sql = f"SELECT * FROM {self.users_table} WHERE {key} = :val"
        return await self.db.fetch_one(sql, {"val": val})

    async def update_by_id(self, id, **changes):
        return await self.db.execute(
            *update_by_id_sql(self.users_table, id, changes)
        )

    def insert(self, **fields):
        sql = insert_sql(self.users_table, fields)
        return self.db.fetch_one(sql, fields)


def update_by_id_sql(table: str, id: int, changes: dict) -> (str, list):
    """
    >>> update_by_id_sql('tbl', 1, {'foo': 2, 'bar': 3})
    ('UPDATE tbl SET foo=:foo, bar=:bar WHERE id=:id', {'id': 1, 'foo': 2, 'bar': 3})
    """  # noqa
    sets = ", ".join(f"{k}=:{k}" for k in changes.keys())
    sql = f"UPDATE {table} SET {sets} WHERE id=:id"
    values = {"id": id}
    values.update(changes)
    return sql, values


def insert_sql(table: str, fields: dict) -> str:
    """
    >>> insert_sql('tbl', {'foo': 1, 'bar': 2})
    'INSERT INTO tbl (foo, bar) VALUES (:foo, :bar) RETURNING id'
    """
    keys = ", ".join(fields.keys())
    vals = ", ".join(f":{k}" for k in fields.keys())
    return f"INSERT INTO {table} ({keys}) VALUES ({vals}) RETURNING id"
