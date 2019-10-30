import sys

sys.path.insert(0, "..")  # noqa

from functools import partial

from aiohttp import web
from databases import Database
import async_django_session.aiohttp
import async_django_session.databases
import async_django_user.databases
import async_django_user.aiohttp
import ujson

import cfg

db = Database(cfg.DB_URI)
jsonify = partial(web.json_response, dumps=ujson.dumps)


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
    return jsonify({"user": user, "session": session})


async def login(request):
    user = await request.get_user()
    credentials = await request.json()
    if not await user.authenticate(**credentials):
        return jsonify({"message": "Bad username or password"}, status=400)
    if not user["is_active"]:
        return jsonify({"message": "User isn't active"}, status=400)
    user.login()
    return web.json_response({})


async def logout(request):
    user = await request.get_user()
    user.logout()
    return jsonify({})


async def register(request):
    data = await request.json()
    user = await request.get_user()
    if user:
        return jsonify({"message": "Log out first"}, status=400)
    user.update(
        {
            "email": "",
            "username": data["username"],
            "first_name": "",
            "last_name": "",
        }
    )
    user.set_password(data["password"])
    try:
        await user.create()
    except Exception:
        return jsonify(
            {"message": "The username is already in use"}, status=400
        )
    user.login()
    return jsonify({})


async def change_password(request):
    data = await request.json()
    user = await request.get_user()
    if not user:
        return jsonify({"message": "Log in first"}, status=400)
    user.set_password(data["password"])
    await user.save(["password"])
    user.logout()
    return jsonify({})


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
        web.post("/api/register", register),
        web.post("/api/change-password", change_password),
    ]
)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)


if __name__ == "__main__":
    web.run_app(app, port=cfg.PORT)
