import sys

sys.path.insert(0, "..")  # noqa

from starlette.applications import Starlette
from starlette.responses import UJSONResponse, HTMLResponse
import async_django_session.asyncpg
import async_django_session.starlette
import async_django_user.asyncpg
import async_django_user.starlette
import asyncpg
import uvicorn

import cfg


app = Starlette()
app.debug = True


class DB:
    async def connect(self):
        global acquire
        self.pool = await asyncpg.create_pool(cfg.DB_URI)
        self.acquire = self.pool.acquire


db = DB()


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.pool.release()


async_django_user.starlette.middleware(
    app, async_django_user.asyncpg.Backend(db, cfg.SECRET_KEY)
)
async_django_session.starlette.middleware(
    app, async_django_session.asyncpg.Backend(db, cfg.SECRET_KEY)
)


@app.route("/")
async def index(request):
    with open("index.html") as f:
        return HTMLResponse(f.read())


@app.route("/api/me")
async def me(request):
    user = await request.state.get_user()
    session = await request.state.get_session()
    return UJSONResponse({"user": user, "session": session})


@app.route("/api/login", methods=["post"])
async def login(request):
    user = await request.state.get_user()
    credentials = await request.json()
    if not await user.authenticate(**credentials):
        return UJSONResponse({"detail": "Bad username or password"}, 401)
    if not user["is_active"]:
        return UJSONResponse({"detail": "User isn't active"}, 401)
    user.login()
    return UJSONResponse({})


@app.route("/api/logout", methods=["post"])
async def logout(request):
    user = await request.state.get_user()
    user.logout()
    return UJSONResponse({})


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=0)
    uvicorn.run(app, host="127.0.0.1", port=cfg.PORT, debug=cfg.DEBUG)
