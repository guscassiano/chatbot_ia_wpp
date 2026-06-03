from fastapi import FastAPI, Request


app = FastAPI()

@app.post('/webhook')
async def webhook():
    data = await request.json()
    print(data)
    return { 'status': 'ok'}
