"""In-process ASGI requests without a background event-loop portal."""
import asyncio
import httpx


class ASGIClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, url, **kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test') as client:
                task = asyncio.create_task(client.request(method, url, **kwargs))
                while not task.done():
                    await asyncio.sleep(0.001)
                return await task
        return asyncio.run(run())

    def __getattr__(self, method):
        return lambda url, **kwargs: self.request(method.upper(), url, **kwargs)
