import aiofiles
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
        logging.debug(welcome_message)

        logging.debug(f'Отправка токена: {user_token}')
        writer.write(f'{user_token}\n'.encode('utf-8'))
        await writer.drain()

        token_response = await reader.readline()
        json_str = token_response.decode('utf-8').strip()
        logging.debug(f'Ответ сервера: {json_str}')

        if json.loads(json_str) is None:
            print(f'Токен: {user_hash} не найден.')
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


async def register_user(host, port, name):
    reader, writer = await asyncio.open_connection(host, port)

    try:
        await reader.readline()
        writer.write('\n'.encode('utf-8'))
        await writer.drain()

        await reader.readline()
        writer.write(f'{name}\n'.encode('utf-8'))
        await writer.drain()

        server_response = await reader.readline()
        user_info = json.loads(server_response.decode())

        async with aiofiles.open('register_info.json', "w", encoding='utf-8') as f:
            await f.write(server_response.decode())

        print(f'Вы успешно зарегестрировались! Ваше имя: {user_info['nickname']}')
        print('Данные сохранены в файле "register_info.json"')
        print('Для отправки сообщения используйте команду: python3 write_chat.py --message "Ваше сообщение"')

    finally:
        writer.close()
        await writer.wait_closed()


def main():
    host_default = env.str('HOST', 'minechat.dvmn.org')
    port_default = env.int('WRITE_PORT', 5050)
    user_name = env.str('USER_NAME', None)

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
        '--message',
        help='Сообщение для отправки в чат.'
    )

    parser.add_argument(
        '--log',
        action='store_true',
        help='Включить логирование (по умолчанию: выключено)'
    )

    parser.add_argument(
        '--user-name',
        default=user_name,
        help='Имя для регистрации в чате.'
    )
    
    args = parser.parse_args()

    try:
        with open('register_info.json', 'r') as f:
            user_hash = json.load(f)
        user_token = user_hash.get('account_hash')
    except FileNotFoundError:
        user_token = None

    setup_logging(args.log)

    if user_token is None:
        asyncio.run(register_user(args.host, args.port, args.user_name))
    else:
        asyncio.run(write_chat(args.host, args.port, user_token, args.message))


if __name__ == "__main__":
    main()

