import websockets, asyncio
async def test():
    try:
        async with websockets.connect('ws://localhost:8000/api/v1/escalation/ws') as ws:
            print('Connected!')
    except Exception as e:
        print(f"Exception: {e}")
asyncio.get_event_loop().run_until_complete(test())
