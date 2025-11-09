import time
def logging_middleware(app):
    async def middleware(scope, receive, send):
        start = time.time()
        await app(scope, receive, send)
        duration = time.time() - start
        print(f"Request took {duration}s")
    return middleware
