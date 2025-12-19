import argparse
import asyncio
import json
import logging
import sys

from environs import Env


env = Env()
env.read_env()

 
def setup_logging(enable: bool):
    if enable:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.CRITICAL)


async def write_chat(host, port, user_token, message):
    logging.info(f'Подключение к {host}:{port}')

    reader, writer = await asyncio.open_connection(host, port)

    try:
        welcome = await reader.readline()
        welcome_message = welcome.decode('utf-8', errors='ignore')
        logging.debug(f'Приветствие от сервера: {welcome_message}')

        logging.debug(f'Отправка токена: {user_token}')
        writer.write(f'{user_token}\n'.encode('utf-8'))
        await writer.drain()

        token_response = await reader.readline()
        json_str = token_response.decode('utf-8').strip()
        logging.debug(f'Ответ сервера: {json_str}')

        if json.loads(json_str) is None:
            print(f'Токен: {user_token} не найден.')
            return

        writer.write(f'{message}\n\n'.encode('utf-8'))
        await writer.drain()

        logging.info(f'Сообщение: "{message}", успешно отправлено!')

    except Exception as e:
        logging.error(f'Ошибка при отправке: {e}')
        raise

    finally:
        writer.close()
        await writer.wait_closed()
        logging.info('Соединение закрыто')


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

    parser.add_argument(
        '--log',
        action='store_true',
        help='Включить логирование (по умолчанию: выключено)'
    )

    args = parser.parse_args()

    setup_logging(args.log)

    asyncio.run(write_chat(args.host, args.port, args.user_token, args.message))


if __name__ == "__main__":
    main()

