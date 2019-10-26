from starlette.requests import Request


async def get_user(request: Request):
    return await request.state.get_user()
