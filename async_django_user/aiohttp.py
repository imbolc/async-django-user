from aiohttp import web


def middleware(backend):
    @web.middleware
    async def django_user(request, handler):
        session = await request.get_session()
        user = backend.get_user_from_session(session)
        request.get_user = user.load
        response = await handler(request)
        return response

    return django_user
