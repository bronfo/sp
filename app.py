#coding:utf-8

import sys
import asyncio
import utils

from sanic import Sanic
from sanic import response

import logging, os
logging.basicConfig(format='%(asctime)s %(filename)s %(lineno)s: %(message)s')
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

KEY = b'sjbauicixugdhoix'
ZERO = b'\x00\x00\x00\x00'

app = Sanic()

@app.route("/")
async def test(request):
    return response.text('hello 4')

class WsTunnel():
    def __init__(self, request, ws):
        self._request = request
        self._stm = utils.CryptedStream(KEY)
        self._ws = ws
        asyncio.ensure_future(self._feed())
    
    async def _feed(self):
        port = str(self._request.port)
        while True:
            try:
                data = await self._ws.recv()
                if type(data) == bytes:
                    self._stm.feed(data)
                else:
                    logger.debug(':%s unexpected data: [%s]' % (port, repr(data)))
                    break
            except Exception:
                logger.debug(':%s broken' % port)
                break

        self._stm.feed(2)
    
    def reset(self):
        self._stm.feed(0)
    
    async def serve(self):
        async def fromwsstm(wsstm, transport):
            while True:
                data = await wsstm.read()
                if type(data) == bytes:
                    logger.debug('wsstm read: ' + repr(data)[:10])
                    transport.write(data)
                elif data == 1 or data == 2: #peer reset or peer close
                    logger.debug('wsstm broken: ' + repr(data))
                    if transport:
                        transport.close()
                    break
        
        port = str(self._request.port)
        
        remote = await utils.socks_parse(self._stm.read,
            lambda data: self._ws.send(utils.make_chunk(data, KEY))
        )
        
        logger.debug('remote: ' + repr(remote))
        
        arg = {}
        pair = await asyncio.get_event_loop().create_connection(
                lambda: utils.MyTransfer(None, arg), *remote) if remote else None
        transport = pair[0] if pair else None
        
        task = asyncio.ensure_future(fromwsstm(self._stm, transport))
        
        if not pair:
            logger.debug('not pair')
            await self._ws.send(ZERO)
        else:
            remote_stm = arg['stm']
            logger.debug('remote_stm=' + repr(remote_stm))
            while True:
                data = await remote_stm.read()
                if data:
                    logger.debug('remote_stm data: ' + repr(data)[:10])
                    await self._ws.send(utils.make_chunk(data, KEY))
                else:
                    logger.debug('remote_stm broken & send-zero: ' + repr(data))
                    await self._ws.send(ZERO)
                    break
        await task
        logger.debug('serve exit')


@app.websocket('/ws')
async def ws(request, ws):
    tunnel = WsTunnel(request, ws)
    while True:
        await tunnel.serve()
        tunnel.reset()

if __name__ == "__main__":
    logger.debug('version 2')
    utils.init_loop()
    app.run(host="0.0.0.0", port=8080)
