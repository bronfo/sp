#coding:utf-8

import asyncio
from sanic import Sanic
from sanic import response
import utils

KEY = b'sjbauicixugdhoix'

app = Sanic()

@app.route("/")
async def test(request):
    return response.text('v4!')

async def ws_proc(stm, ws):
    target = await utils.socks_parse(stm.read,
        lambda data: ws.send(utils.make_chunk(data, KEY))
        )
    print('target=' + repr(target))
    if not target:
        await ws.send(b'\x00\x00\x00\x00')
        await ws.send('close')
    else:
        while True:
            data = await stm.read()
            if data is None:
                break
            elif data == 0:
                # get 0 reply 0
                await ws.send(b'\x00\x00\x00\x00')
                break
            else:
                await ws.send(utils.make_chunk(data, KEY))
    
    print('ws_proc end')

@app.websocket('/ws')
async def ws(request, ws):
    stm = utils.CryptedStream(KEY)
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
            asyncio.ensure_future(ws_proc(stm, ws))
        elif data == 'close':
            # get 'close' reply 'close'
            await ws.send(data)
            print(data)
    
    print('ws end')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
