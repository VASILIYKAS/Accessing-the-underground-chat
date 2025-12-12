import asyncio

async def tcp_echo_client():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    try:
        while True:
            messages = await reader.read(1024)
            if not messages:
                break
            print(messages.decode('utf-8'), end='')
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(tcp_echo_client())
