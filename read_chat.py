import aiofiles
import argparse
import asyncio

from datetime import datetime
from environs import Env
from pathlib import Path


env = Env()
env.read_env()

 
async def read_chat(host, port, log_path):
    reader, writer = await asyncio.open_connection(
        host, port)

    log_dir = Path(log_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            messages = await reader.read(1024)
            if not messages:
                break
            
            decoded_message = messages.decode('utf-8')
            print(decoded_message, end='')

            timestamp = datetime.now().strftime("%Y.%m.%d %H:%M:%S")

            async with aiofiles.open(log_path, "a", encoding='utf-8') as f:
                await f.write(f'[{timestamp}] {decoded_message}\n')

    finally:
        writer.close()
        await writer.wait_closed()


def main():
    host_default = env.str('HOST', 'minechat.dvmn.org')
    port_default = env.int('READ_PORT', 5000)
    log_path_default = env.str('LOGS', 'underground_chat.txt')

    parser = argparse.ArgumentParser(description='Подключение к чату')

    parser.add_argument(
        '--host',
        default=host_default,
        help='Адрес подключения к чату.'
    )

    parser.add_argument(
        '--port',
        default=port_default,
        help='Порт подключения к чату.'
    )

    parser.add_argument(
        '--log-path',
        default=log_path_default,
        help='Путь для сохранения файла с историей переписки.'
    )

    args = parser.parse_args()

    asyncio.run(read_chat(args.host, args.port, args.log_path))


if __name__ == "__main__":
    main()

