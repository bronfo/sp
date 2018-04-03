#coding:utf-8

import asyncio

class MyStream():
    def __init__(self):
        self._buf = b''
        self._want = 0
    
    def feed(self, data):
        #print(f'feed: {data} _want: {self._want}')
        if not data:
            if self._want:
                self._want = 0
                self._future.set_result(None)
        else:
            self._buf += data
            if self._want:
                if self._want < 0:
                    r = self._buf
                    self._buf = b''
                    self._want = 0
                    self._future.set_result(r)
                elif len(self._buf) >= self._want:
                    n = self._want
                    r = self._buf[:n]
                    self._buf = self._buf[n:]
                    self._want = 0
                    self._future.set_result(r)
    
    async def read(self, n = -1):
        if n == 0:
            raise Exception('error argument')
        if n < 0 and len(self._buf) > 0:
            # read all
            r = self._buf
            self._buf = b''
            return r
        if n > 0 and len(self._buf) >= n:
            r = self._buf[:n]
            self._buf = self._buf[n:]
            print(f'read_n {n}')
            return r
        self._want = n
        self._future = asyncio.Future()
        r = await self._future
        return r

# MyStream stm, asyncio.Transport transport
async def socks_parse(stm, transport):
    # req1: ver|nmethods|methods
    header = await stm.read(1)
    if header != b'\x05':
        return None, None
    data = await stm.read(1)
    methods = await stm.read(data[0])
    
    # JUST WRITE!
    transport.write(b'\x05\x00')
    
    # req2: VER|CMD|RSV|ATYP|ADDR|PORT
    header = await stm.read(3)
    if header != b'\x05\x01\x00':
        transport.write('\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')
        return None, None
    header = await stm.read(1)
    if header == b'\x01':
        data = await stm.read(4)
        host = data
    elif header == b'\x03':
        data = await stm.read(1)
        data += await stm.read(data[0])
        host = data[1:]
    else:
        transport.write('\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
        return None, None
    data += await stm.read(2)
    port = int.from_bytes(data[-2:], 'big')
    transport.write(b'\x05\x00\x00' + header + data)
    return host, port
