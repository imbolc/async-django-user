import sys

sys.path.insert(0, "..")  # noqa

from starlette.responses import HTMLResponse
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from async_django_session.fastapi import get_session
from async_django_session.session import Session
from async_django_user.fastapi import get_user
from async_django_user.user import User
import async_django_session.asyncpg
import async_django_session.starlette
import async_django_user.asyncpg
import async_django_user.starlette
import asyncpg
import uvicorn

import cfg


app = FastAPI()
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


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html") as f:
        return f.read()


@app.get("/api/me")
async def me(
    session: Session = Depends(get_session), user: User = Depends(get_user)
):
    return {"user": user, "session": session}


class Credentials(BaseModel):
    username: str
    password: str


@app.post("/api/login")
async def login(credentials: Credentials, user: User = Depends(get_user)):
    if not await user.authenticate(**credentials.dict()):
        raise HTTPException(401, "Bad username or password")
    if not user["is_active"]:
        raise HTTPException(401, "User isn't active")
    user.login()
    return {}


@app.post("/api/logout")
async def logout(user: User = Depends(get_user)):
    user.logout()
    return {}


async def dep_a():
    print("> A")
    yield "dep_a"
    print("< A")


async def dep_b(dep_a=Depends(dep_a)):
    print("> B")
    yield f"dep_b({dep_a})"
    print("< B")


@app.get("/do")
async def do(dep_a=Depends(dep_a), dep_b=Depends(dep_b)):
    return locals()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=cfg.PORT, debug=cfg.DEBUG)
