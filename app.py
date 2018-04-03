#coding:utf-8

import asyncio
from sanic import Sanic
from sanic import response
from utils import MyStream

app = Sanic()

@app.route("/")
async def test(request):
    return response.text('v3!')

async def ws_stm(stm, ws):
    while True:
        chunk = await stm.read_chunk()
        if chunk is None:
            break
        elif chunk == 0:
            # get 0 reply 0
            await ws.send(b'\x00\x00\x00\x00')
        else:
            print(b'chunk: ' + chunk)
            await ws.send(int.to_bytes(len(chunk), 4, 'big') + chunk)

@app.websocket('/ws')
async def ws(request, ws):
    stm = MyStream()
    asyncio.ensure_future(ws_stm(stm, ws))
    while True:
        try:
            data = await ws.recv()
        except Exception:
            print('disconnected')
            stm.feed(None)
            break
        if not data:
            stm.feed(None)
            break
        elif type(data) == bytes:
            stm.feed(data)
        elif data == 'connect':
            print(data)
        elif data == 'close':
            # get 'close' reply 'close'
            await ws.send(data)
            print(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
