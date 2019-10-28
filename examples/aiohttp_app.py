import sys

sys.path.insert(0, "..")  # noqa

from aiohttp import web
from databases import Database
import async_django_session.aiohttp
import async_django_session.databases
import async_django_user.databases
import async_django_user.aiohttp
import ujson

import cfg

db = Database(cfg.DB_URI)


async def on_startup(app):
    await db.connect()


async def on_cleanup(app):
    await db.disconnect()


async def index(request):
    with open("index.html") as f:
        return web.Response(text=f.read(), content_type="text/html")


async def me(request):
    user = await request.get_user()
    session = await request.get_session()
    return web.json_response(
        {"user": user, "session": session}, dumps=ujson.dumps
    )


async def login(request):
    user = await request.get_user()
    credentials = await request.json()
    if not await user.authenticate(**credentials):
        return web.json_response(
            {"detail": "Bad username or password"}, status=401
        )
    if not user["is_active"]:
        return web.json_response({"detail": "User isn't active"}, status=401)
    user.login()
    return web.json_response({})


async def logout(request):
    user = await request.get_user()
    user.logout()
    return web.json_response({})


user_middleware = async_django_user.aiohttp.middleware(
    async_django_user.databases.Backend(db, cfg.SECRET_KEY)
)
session_middleware = async_django_session.aiohttp.middleware(
    async_django_session.databases.Backend(db, cfg.SECRET_KEY)
)

app = web.Application(middlewares=[session_middleware, user_middleware])
app.add_routes(
    [
        web.get("/", index),
        web.get("/api/me", me),
        web.post("/api/login", login),
        web.post("/api/logout", logout),
    ]
)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)


if __name__ == "__main__":
    web.run_app(app, port=cfg.PORT)
