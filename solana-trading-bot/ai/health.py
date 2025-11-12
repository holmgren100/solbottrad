from aiohttp import web

async def health_check():
    return web.Response(text='OK', status=200)

app = web.Application()
app.router.add_get('/health', health_check)