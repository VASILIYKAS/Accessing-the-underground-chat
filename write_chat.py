import argparse
import asyncio

from environs import Env


env = Env()
env.read_env()

 
async def write_chat(host, port, user_token, message):
    reader, writer = await asyncio.open_connection(host, port)

    try:
        writer.write(f"{user_token}\n".encode('utf-8'))
        await writer.drain()

        writer.write(f"{message}\n\n".encode('utf-8'))
        await writer.drain()

    finally:
        writer.close()
        await writer.wait_closed()


def main():
    host_default = env.str('HOST', 'minechat.dvmn.org')
    port_default = env.int('WRITE_PORT', 5050)
    user_token = env.str('USER_TOKEN')

    parser = argparse.ArgumentParser(description='Отправить сообщение в чат')

    parser.add_argument(
        '--host',
        default=host_default,
        help='Адрес чата.'
    )

    parser.add_argument(
        '--port',
        default=port_default,
        help='Порт чата.'
    )

    parser.add_argument(
        '--user-token',
        default=user_token,
        help='Токен для подключения к чату.'
    )

    parser.add_argument(
        '--message',
        help='Сообщение для отправки в чат.'
    )

    args = parser.parse_args()

    asyncio.run(write_chat(args.host, args.port, args.user_token, args.message))


if __name__ == "__main__":
    main()

