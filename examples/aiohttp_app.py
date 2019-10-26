import sys

sys.path.insert(0, "..")  # noqa

from aiohttp import web
from databases import Database
import async_django_session.aiohttp
import async_django_session.databases

import cfg

db = Database(cfg.DB_URI)


async def on_startup(app):
    await db.connect()


async def on_cleanup(app):
    await db.disconnect()


async def index(request):
    session = await request.get_session()
    framework = "aiohttp"
    session[framework] = session.get(framework, 0) + 1
    return web.json_response({"framework": framework, "session": session})


session_middleware = async_django_session.aiohttp.middleware(
    async_django_session.databases.Backend(db, cfg.SECRET_KEY)
)

app = web.Application(middlewares=[session_middleware])
app.add_routes([web.get("/", index)])
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)


if __name__ == "__main__":
    web.run_app(app, port=cfg.PORT)
