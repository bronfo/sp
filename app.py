#coding:utf-8

import asyncio
from sanic import Sanic
from sanic import response
from utils import MyStream

app = Sanic()

@app.route("/")
async def test(request):
    return response.text('v2!')

@app.websocket('/ws')
async def ws(request, ws):
    stm = MyStream()
    while True:
        try:
            data = await ws.recv()
        except Exception:
            print('e===========')
            break
        if not data:
            break
        elif type(data) == bytes:
            print(data)
            stm.feed(data)
            #test
            await ws.send(data)
        elif data == 'connect':
            print(data)
        elif data == 'close':
            await ws.send(data)
            print(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
