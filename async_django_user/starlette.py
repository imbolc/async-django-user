def middleware(app, backend):
    @app.middleware("http")
    async def django_user(request, call_next):
        session = await request.state.get_session()
        user = backend.get_user_from_session(session)
        request.state.get_user = user.load
        response = await call_next(request)
        return response
