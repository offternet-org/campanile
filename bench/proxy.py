# DEVELOPED BY CARROTSTUDIO software house
"""The control for the check itself: a go-between that flips one bit of the neighbour's first
answer (the 100th byte of its body) and says so. A check that let this through would be blind.
With "clean" it passes everything untouched: the go-between alone must not be what fails.

    proxy.py LISTEN_PORT TARGET_HOST TARGET_PORT [clean]
"""

import asyncio
import sys

AT = 100


async def forward(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()


async def corrupt(reader, writer):
    """The first answer is held until its 100th body byte is in, flipped, then sent on."""
    seen = b""
    try:
        while data := await reader.read(65536):
            seen += data
            end = seen.find(b"\r\n\r\n")
            if end >= 0 and len(seen) > end + 4 + AT:
                at = end + 4 + AT
                print(f"flipped body byte {AT}: {seen[at]:#04x} -> {seen[at] ^ 1:#04x}", flush=True)
                writer.write(seen[:at] + bytes([seen[at] ^ 1]) + seen[at + 1 :])
                await writer.drain()
                break
        else:
            writer.write(seen)  # an answer too short to touch goes through, and is reported
            print("answer too short, nothing flipped", flush=True)
            writer.close()
            return
        await forward(reader, writer)
    finally:
        writer.close()


async def handle(client_r, client_w):
    target_r, target_w = await asyncio.open_connection(sys.argv[2], int(sys.argv[3]))
    back = forward if sys.argv[4:] == ["clean"] else corrupt
    await asyncio.gather(forward(client_r, target_w), back(target_r, client_w))


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", int(sys.argv[1]))
    print("listening", flush=True)
    async with server:
        await server.serve_forever()


asyncio.run(main())
