import asyncio
import websockets
import json
import os

rooms = {}


# =========================
# SAFE SEND
# =========================
async def safe_send(ws, data):
    try:
        await ws.send(json.dumps(data))
    except:
        pass


# =========================
# MAIN HANDLER
# =========================
async def handler(ws):

    room_id = None

    try:

        async for message in ws:

            print("📩 Received:", message)

            try:
                data = json.loads(message)
            except:
                continue

            # =========================
            # JOIN ROOM
            # =========================
            if data.get("type") == "join":

                room_id = data.get("room")

                if not room_id:
                    continue

                if room_id not in rooms:
                    rooms[room_id] = []

                # LIMIT TO 2 USERS
                if len(rooms[room_id]) >= 2:

                    await safe_send(ws, {
                        "type": "full"
                    })

                    continue

                rooms[room_id].append(ws)

                print(f"✅ User joined room: {room_id}")

                # WAITING
                if len(rooms[room_id]) == 1:

                    await safe_send(ws, {
                        "type": "waiting"
                    })

                # READY
                elif len(rooms[room_id]) == 2:

                    for client in rooms[room_id]:

                        await safe_send(client, {
                            "type": "ready"
                        })

            # =========================
            # CHAT MESSAGE
            # =========================
            elif data.get("type") == "chat":

                message_text = data.get("message")
                direction = data.get("direction", "en-fr")

                if not message_text:
                    continue

                # 🔥 SIMPLE TRANSLATION
                translated = message_text

                try:

                    # EN → FR
                    if direction == "en-fr":

                        translated = f"[FR] {message_text}"

                    # FR → EN
                    else:

                        translated = f"[EN] {message_text}"

                except Exception as e:
                    print("Translation failed:", e)

                # SEND TO OTHER USER
                if room_id in rooms:

                    for client in rooms[room_id]:

                        if client != ws:

                            await safe_send(client, {
                                "type": "chat",
                                "original": message_text,
                                "translated": translated
                            })

            # =========================
            # SIGNALING (WEBRTC)
            # =========================
            elif data.get("type") in [
                "offer",
                "answer",
                "ice",
                "call",
                "accept"
            ]:

                if room_id in rooms:

                    for client in rooms[room_id]:

                        if client != ws:
                            await safe_send(client, data)

            # =========================
            # LIVE TRANSLATED AUDIO
            # =========================
            elif data.get("type") == "translated_audio":

                if "audio" not in data:
                    continue

                if room_id in rooms:

                    for client in rooms[room_id]:

                        if client != ws:

                            await safe_send(client, {
                                "type": "translated_audio",
                                "audio": data["audio"]
                            })

    except Exception as e:

        print("❌ Client disconnected:", e)

    finally:

        # REMOVE USER
        if room_id in rooms and ws in rooms[room_id]:

            rooms[room_id].remove(ws)

            print(f"❌ User left room: {room_id}")

            # NOTIFY REMAINING USER
            for client in rooms[room_id]:

                await safe_send(client, {
                    "type": "waiting"
                })

            # DELETE EMPTY ROOM
            if len(rooms[room_id]) == 0:

                del rooms[room_id]

                print(f"🗑 Room deleted: {room_id}")


# =========================
# START SERVER
# =========================
PORT = int(os.environ.get("PORT", 10000))

start_server = websockets.serve(
    handler,
    "0.0.0.0",
    PORT
)

print(f"🚀 WebSocket server running on port {PORT}")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()