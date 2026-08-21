import traceback

try:
    from backend.app.main import app
except Exception as e:
    import urllib.parse
    error_details = traceback.format_exc()
    # Create a dummy ASGI app to return the error to the browser
    async def app(scope, receive, send):
        assert scope['type'] == 'http'
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [
                (b'content-type', b'text/plain'),
            ]
        })
        await send({
            'type': 'http.response.body',
            'body': f"FAILED TO IMPORT APP:\n{error_details}".encode('utf-8')
        })
