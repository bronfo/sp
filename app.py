#coding:utf-8

import asyncio
from sanic import Sanic
from sanic import response
import utils

KEY = b'sjbauicixugdhoix'

app = Sanic()

@app.route("/")
async def test(request):
    return response.text('v5!')


async def from_target(arg, stm, transport):
    # from target to tunnel
    ws = arg['ws']
    print('connect ok')
    while True:
        data = await stm.read()
        if data:
            await ws.send(utils.make_chunk(data, KEY))
        else:
            if not arg['client_close']:
                await ws.send('close')
                print('target close')
            break
    
    print('from_target end')

async def transf(stm, ws, arg):
    target = await utils.socks_parse(stm.read,
        lambda data: ws.send(utils.make_chunk(data, KEY))
        )
    print('target=' + repr(target))
    if not target:
        await ws.send('close')
    else:
        try:
            pair = await asyncio.get_event_loop().create_connection(
                lambda: utils.MyTransfer(from_target, arg), *target)
        except Exception as e:
            print('connect ' + repr(target) + ' fail: ' + repr(e))
        else:
            # from tunnel to target
            transport = pair[0]
            arg['target_writer'] = transport
            while True:
                data = await stm.read()
                if data:
                    transport.write(data)
                else:
                    print('transf read break: ' + repr(data))
                    break
    
    print('transf end')

@app.websocket('/ws')
async def ws(request, ws):
    stm = utils.CryptedStream(KEY)
    # one client one time
    arg = {'ws': ws, 'client_close': False, 'target_writer': None}
    while True:
        try:
            data = await ws.recv()
        except Exception:
            print('disconnected')
        if not data:
            print('ws read break1: ' + repr(data))
            stm.feed(None)
            # todo target.close()
            break
        elif type(data) == bytes:
            stm.feed(data)
        elif data == 'connect':
            print(data)
            arg['client_close'] = False
            arg['target_writer'] = None
            asyncio.ensure_future(transf(stm, ws, arg))
        elif data == 'close':
            # get 'close' reply 'close'
            print('ws client want to close')
            arg['client_close'] = True
            stm.feed(None) #!!
            await ws.send('closed')
            if arg['target_writer']:
                arg['target_writer'].close()
        elif data == 'closed':
            print('ws read break2: ' + repr(data))
            stm.feed(None) #!!
    
    print('ws end')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
