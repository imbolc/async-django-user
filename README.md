Async Django Session
====================

Using [django][] user with async frameworks like [aiohttp][], [starlette][] etc.

    pip install async-django-session async-django-user

tl;dr
-----
Take a look at registration / authorization examples for
[aiohttp + databases][aiohttp example]
or [starlette + asyncpg][starlette example].

API
---

### Backends

There's two ways of communicating to database available:

- through [databases][] - which is compatible with most of major RDBMS:
    ```python
    database = databases.Database(DB_URI)
    await database.connect()
    backend = async_django_user.databases.Backend(database, SECRET_KEY)
    ```
- or directly through [asyncpg][] (PostgreSQL only):
    ```python
    pool = await asyncpg.create_pool(DB_URI)
    backend = async_django_user.asyncpg.Backend(pool, SECRET_KEY)
    ```

### User

To fetch an user from db by its id stored in [django session] there's
`backend.get_user_from_session` method:
```python
user = backend.get_user_from_session(session)
```
It's lazy so the user data won't be actually fetched until you call its
`load` method. It caches the result, so it's inexpensive to call it multiple
times:
```python
await user.load()
```

User provides dict interface to it's data (eg `user["username"]`) and a few
methods:
- `await user.authenticate(username, password)` - checks credentials and populates
  the user from database if they're valid
- `user.login()` - sets session variables logging the user in
- `user.logout()` - clears the session data
- `await user.set_password(password)` - sets a new password for the user
- `await user.save([fields])` - saves the whole user or a particular set of its
   fields
- `await register()` - saves a new user into db

Frameworks integration
----------------------
There's built-in middlewares for a few async frameworks to automatically load
user of the current request. Take a look at [examples][] folder for:
- [aiohttp example][] with [databases backend][]
- [starlette example][] with [asyncpg backend][]


Running examples
----------------
Running the [examples][] you can see different frameworks using the same session
and user data.

Install the requirements:

    cd examples
    pip install -r requirements.txt

Create database and tables:

    createdb async_django_session
    python django_app.py migrate

Create a user:

    python django_app.py createsuperuser

Run [aiohttp example][] which uses [databases backend][]:

    python aiohttp_app.py

Run [starlette example][] which uses [asyncpg backend][]:

    python starlette_app.py

Run [django example][]:

    python django_app.py runserver

[aiohttp]: https://github.com/aio-libs/aiohttp
[starlette]: https://github.com/encode/starlette
[asyncpg]: https://github.com/MagicStack/asyncpg
[databases]: https://github.com/encode/databases
[django]: https://github.com/django/django
[examples]: https://github.com/imbolc/async-django-user/tree/master/examples
[django example]: https://github.com/imbolc/async-django-user/tree/master/examples/django_app.py
[starlette example]: https://github.com/imbolc/async-django-user/tree/master/examples/starlette_app.py
[aiohttp example]: https://github.com/imbolc/async-django-user/tree/master/examples/aiohttp_app.py
[asyncpg backend]: https://github.com/imbolc/async-django-user/tree/master/async-django-user/asyncpg.py
[databases backend]: https://github.com/imbolc/async-django-user/tree/master/async-django-user/databases.py
[aiohttp middleware]: https://github.com/imbolc/async-django-user/tree/master/async-django-user/aiohttp.py
[starlette middleware]: https://github.com/imbolc/async-django-user/tree/master/async-django-user/starlette.py
