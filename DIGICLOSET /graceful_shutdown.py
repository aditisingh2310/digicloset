# config/resilience/graceful_shutdown.py
import signal, sys, asyncio

def setup_graceful_shutdown(server):
    loop = asyncio.get_event_loop()

    def shutdown():
        print("Received termination signal, shutting down gracefully...")
        loop.create_task(close_server(server))

    def handle_exception(loop, context):
        print(f"Unhandled exception: {context}")
        sys.exit(1)

    loop.set_exception_handler(handle_exception)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

async def close_server(server):
    await server.shutdown()
    print("Server closed successfully.")