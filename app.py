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


async def transf(transports):
    # from target to tunnel
    print('connect ok')
    ws = transports[1]
    stm = transports[2]
    while True:
        data = await stm.read()
        if data:
            await ws.send(utils.make_chunk(data, KEY))
        else:
            break
    
    print('transf end')

async def ws_proc(stm, ws):
    target = await utils.socks_parse(stm.read,
        lambda data: ws.send(utils.make_chunk(data, KEY))
        )
    print('target=' + repr(target))
    if not target:
        await ws.send(b'\x00\x00\x00\x00')
        await ws.send('close')
    else:
        try:
            transports = [stm, ws, None, None]
            pair = await asyncio.get_event_loop().create_connection(
                lambda: utils.MyTransfer(transf, utils.MyStream,
                transports), *target)
        except Exception as e:
            print('connect ' + repr(target) + ' fail: ' + repr(e))
        else:
            # from tunnel to target
            transport = transports[3]
            while True:
                data = await stm.read()
                print('from_tunnel: ' + repr(data))
                if data is None:
                    transport.close()
                    break
                elif data == 0:
                    transport.close()
                    # get 0 reply 0
                    await ws.send(b'\x00\x00\x00\x00')
                    break
                else:
                    #await ws.send(utils.make_chunk(data, KEY))
                    transport.write(data)
    
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
            stm.feed(None) #!!
            await ws.send(data)
            print('buf: ' + repr(stm._buf))
            print(data)
    
    print('ws end')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
