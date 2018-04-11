#coding:utf-8

import asyncio
import socket

class MyStream():
    def __init__(self):
        self._buf = b''
        self._want = 0
        
        self._closed = False
    
    def feed(self, data):
        if not data:
            self._closed = True
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
        if self._closed:
            return None
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
        print('chunk ' + repr(data)[:10])
        if not data:
            return None
        return data

class CryptedStream():
    def __init__(self, key):
        self._buf = b''
        self._want = 0
        
        self._len = -1
        self._chunk = b''
        self._key = key
        
        self._closed = False
    
    def parse_chunk(self):
        while True:
            if self._len == -1:
                if len(self._buf) >= 4:
                    # get length
                    self._len = int.from_bytes(self._buf[:4], 'big')
                    self._buf = self._buf[4:]
                    # to get chunk
                else:
                    # need more data for length
                    break
            if self._len > 0 and len(self._buf) >= self._len:
                # get chunk
                self._chunk += crypt_string(self._buf[:self._len], self._key, False)
                self._buf = self._buf[self._len:]
                self._len = -1
                # to get length
            else:
                # need more data for chunk
                break
    
    def feed(self, data):
        if not data:
            self._closed = True
            if self._want:
                self._want = 0
                self._future.set_result(None)
        else:
            self._buf += data
            self.parse_chunk()
            
            if self._len == 0:
                self._len = -1
                self._closed = True
                if self._want:
                    self._want = 0
                    self._future.set_result(0)
            
            if self._want:
                if self._want < 0:
                    r = self._chunk
                    self._chunk = b''
                    self._want = 0
                    self._future.set_result(r)
                elif len(self._chunk) >= self._want:
                    n = self._want
                    r = self._chunk[:n]
                    self._chunk = self._chunk[n:]
                    self._want = 0
                    self._future.set_result(r)
    
    async def read(self, n = -1):
        if n == 0:
            raise Exception('error argument')
        if n < 0 and len(self._chunk) > 0:
            # read all
            r = self._chunk
            self._chunk = b''
            return r
        if n > 0 and len(self._chunk) >= n:
            r = self._chunk[:n]
            self._chunk = self._chunk[n:]
            return r
        if self._closed:
            return None
        self._want = n
        self._future = asyncio.Future()
        r = await self._future
        return r

class MyTransfer(asyncio.Protocol):
    def __init__(self, transf_fn, arg):
        self._transf_fn = transf_fn
        self._arg = arg
    def connection_made(self, transport):
        self._stm = MyStream()
        self._transf_fn(self._stm, transport)
        #asyncio.ensure_future(self._transf_fn(self._arg, self._stm, transport))
        #asyncio.get_event_loop().create_task(self._transf_fn(self._arg, self._stm, transport))
    def data_received(self, data):
        self._stm.feed(data)
    def connection_lost(self, exc):
        self._stm.feed(None)


def make_chunk(data, key):
    data = crypt_string(data, key, True)
    return int.to_bytes(len(data), 4, 'big') + data

# read-function, write-function
async def socks_parse(readfn, writefn):
    # req1: ver|nmethods|methods
    header = await readfn(1)
    if header != b'\x05':
        return None
    data = await readfn(1)
    methods = await readfn(data[0])
    if b'\x00' not in methods:
        await writefn(b'\x05\xff')
        return None
    
    # JUST WRITE!
    await writefn(b'\x05\x00')
    
    # req2: VER|CMD|RSV|ATYP|ADDR|PORT
    header = await readfn(3)
    if header != b'\x05\x01\x00':
        await writefn(b'\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')
        return None
    header = await readfn(1)
    if header == b'\x01':
        data = await readfn(4)
        host = socket.inet_ntoa(data)
    elif header == b'\x03':
        data = await readfn(1)
        data += await readfn(data[0])
        host = data[1:]
    else:
        await writefn(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
        return None
    data += await readfn(2)
    port = int.from_bytes(data[-2:], 'big')
    await writefn(b'\x05\x00\x00' + header + data)
    return host, port


# bytes data
def crypt_string(data, key, encode=True):
    from itertools import cycle
    import base64
    # the python3
    izip = zip
    # to bytes
    #data = data.encode()
    if not encode:
        data = base64.b64decode(data)
    #xored = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in izip(data, cycle(key)))
    xored = b''.join(bytes([x ^ y]) for (x,y) in izip(data, cycle(key)))
    return base64.b64encode(xored) if encode else xored
