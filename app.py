#coding:utf-8

from sanic import Sanic
from sanic.response import text

app = Sanic()

@app.route("/")
async def test(request):
    return text('Hello World!')

@app.websocket('/ws')
async def ws(request, ws):
    while True:
        data = 'hello!'
        data = await ws.recv()
        print('Received: ' + data)
        await ws.send(data + ', welcome!')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
