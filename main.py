import asyncio
import aiofiles
from datetime import datetime

 
async def read_chat():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    try:
        while True:
            messages = await reader.read(1024)
            if not messages:
                break
            
            decoded_message = messages.decode('utf-8')
            print(decoded_message, end='')

            timestamp = datetime.now().strftime("%Y.%m.%d %H:%M:%S")

            async with aiofiles.open("underground_chat.txt", "a", encoding='utf-8') as f:
                await f.write(f'[{timestamp}] {decoded_message}\n')

    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(read_chat())
