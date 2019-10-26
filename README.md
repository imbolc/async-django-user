Async Django Session
====================

Using [django][] user with async frameworks like [aiohttp][], [starlette][], [fastapi][] etc.

    pip install async-django-user

API
---

### Backends

There's two ways of communicating to database available:

- through [databases][] - which is compatible with most of major RDBMS:
    ```python
    database = databases.Database(DB_URI)
    await database.connect()
    backend = async_django_session.databases.Backend(database, SECRET_KEY)
    ```
- or directly through [asyncpg][] (PostgreSQL only):
    ```python
    pool = await asyncpg.create_pool(DB_URI)
    backend = async_django_session.asyncpg.Backend(pool, SECRET_KEY)
    ```

### Session

To fetch session from db by its key there's `backend.get_session` method. If
`key` is `None` a new session will be created:
```python
session = backend.get_session(key)
```
It's lazy so the session data won't be actually fetched until you call its
`load` method. In caches the result, so it's inexpensive to call it multiple
times:
```python
await session.load()
```
You can combine them into a single line as the `load` method returns session
itself:
```python
session = await backend.get_session(key).load()
```
Session provides dict-interface to read / write data:
```python
session["foo"] = "bar"
print(session["foo"])
```
To sync session with database you should explicitly call its `save` method. It
won't make unnecessary db call if the session wasn't changed (the boolean value
it returns is intend to indicate if it was the case).
```python
saved = await session.save()
```
During saving of a new session a random key will be generated and available as
`session.key` parameter afterwords.

Frameworks integration
----------------------
There's built-in middlewares for a few frameworks to automatically load (using
session id from cookies) and save sessions.

### Aiohttp
After adding of [session middleware][aiohttp middleware]:
```python
session_middleware = async_django_session.aiohttp.middleware(
    async_django_session.databases.Backend(db, SECRET_KEY)
)
app = web.Application(middlewares=[session_middleware])
```
You can get requests session as:
```python
session = await request.get_session()
```
A full aiohttp example can be found [here][aiohttp example].

### Starlette
After adding of [session middleware][starlette middleware]:
```python
async_django_session.starlette.middleware(
    app, async_django_session.databases.Backend(db, SECRET))
)
```
Session of a current request is available as:
```python
session = await request.state.get_session()
```

A working starlette example is [here][starlette example].

### Fastapi
Perform starlette app initialization from above as fastapi based on it.
After that you can get session using dependency injection as:
```python
from async_django_session.fastapi import get_session
from async_django_session.session import Session

async def index(session: Session = Depends(get_session)):
    ...
```

A working fastapi example is [here][fastapi example].

Running examples
----------------
Running the [examples][] you can see different frameworks using the same session
data. To see session data open <http://localhost:8000/> after running of each
example.

Install requirements:

    cd examples
    pip install -r requirements.txt

Create database and tables:

    createdb async_django_session
    python django_app.py migrate

Run [aiohttp example][] which uses [databases backend][]:

    python aiohttp_app.py

Run [starlette example][] which uses [asyncpg backend][]:

    python starlette_app.py

Run [fastapi example][] which uses [asyncpg backend][]:

    python fastapi_app.py

Run [django example][]:

    python django_app.py runserver

[aiohttp]: https://github.com/aio-libs/aiohttp
[starlette]: https://github.com/encode/starlette
[fastapi]: https://github.com/tiangolo/fastapi
[asyncpg]: https://github.com/MagicStack/asyncpg
[databases]: https://github.com/encode/databases
[django]: https://github.com/django/django
[examples]: https://github.com/imbolc/async_django_session/tree/master/examples
[django example]: https://github.com/imbolc/async_django_session/tree/master/examples/django_app.py
[starlette example]: https://github.com/imbolc/async_django_session/tree/master/examples/starlette_app.py
[fastapi example]: https://github.com/imbolc/async_django_session/tree/master/examples/fastapi_app.py
[aiohttp example]: https://github.com/imbolc/async_django_session/tree/master/examples/aiohttp_app.py
[asyncpg backend]: https://github.com/imbolc/async_django_session/tree/master/async_django_session/asyncpg.py
[databases backend]: https://github.com/imbolc/async_django_session/tree/master/async_django_session/databases.py
[aiohttp middleware]: https://github.com/imbolc/async_django_session/tree/master/async_django_session/aiohttp.py
[starlette middleware]: https://github.com/imbolc/async_django_session/tree/master/async_django_session/starlette.py
