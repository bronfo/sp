#coding:utf-8

import asyncio

class MyStream():
    def __init__(self):
        self._buf = b''
        self._want = 0
    
    def feed(self, data):
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
            return r
        self._want = n
        self._future = asyncio.Future()
        r = await self._future
        return r
    
    async def read_chunk(self):
        len = await self.read(4)
        print('len1 ' + repr(len))
        if not len:
            return None
        len = int.from_bytes(len, 'big')
        print('len2 ' + repr(len))
        if not len:
            return len # 0 or None
        data = await self.read(len)
        print('chunk ' + repr(data))
        if not data:
            return None
        return data

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


def crypt_string(data, key, encode=True):
    from itertools import cycle
    import base64
    # the python3
    izip = zip
    # to bytes
    data = data.encode()
    if not encode:
        data = base64.decodestring(data)
    #xored = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in izip(data, cycle(key)))
    xored = b''.join(bytes([x ^ y]) for (x,y) in izip(data, cycle(key)))
    if encode:
        xored = base64.encodestring(xored)
        return xored.decode().strip()
    return xored.decode()
