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


async def authorise(host, port, user_token):
    logging.info(f'Подключение к {host}:{port}')
    reader, writer = await asyncio.open_connection(host, port)

    try:
        welcome = await reader.readline()
        logging.debug(f'{welcome.decode()}')
        
        writer.write(f'{user_token}\n'.encode('utf-8'))
        await writer.drain()
        
        auth_response = await reader.readline()
        auth_data = json.loads(auth_response.decode())
        logging.debug(f'Авторизация: {auth_data}')
        
        if auth_data is None:
            print('Требуется регистрация.')
            writer.close()
            await writer.wait_closed()
            return None
        
        print('Вы успешно авторизовались.')
        return reader, writer
        
    except Exception as e:
        logging.error(f'Ошибка авторизации: {e}')
        writer.close()
        await writer.wait_closed()
        return None


async def submit_message(host, port, message, user_token):
    auth = await authorise(host, port, user_token)

    if auth is None:
        return

    reader, writer = auth

    try:
        logging.debug(f'Отправка сообщения: "{message}"')
        writer.write(f'{message}\n\n'.encode('utf-8'))
        await writer.drain()
        
        print('Сообщение отправлено!')
        
    except Exception as e:
        logging.error(f'Ошибка отправки сообщения: {e}')
    finally:
        writer.close()
        await writer.wait_closed()


async def register_user(host, port, name):
    reader, writer = await asyncio.open_connection(host, port)
    user_name = name.replace('\n', '\\n')

    try:
        await reader.readline()
        writer.write('\n'.encode('utf-8'))
        await writer.drain()

        await reader.readline()
        writer.write(f'{user_name}\n'.encode('utf-8'))
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
    user_name_default = env.str('USER_NAME', 'NewUser')

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
        '--logging',
        action='store_true',
        help='Включить логирование (по умолчанию: выключено)'
    )

    parser.add_argument(
        '--user-name',
        help='Имя для регистрации в чате.'
    )

    parser.add_argument(
        '--user-token', 
        help='Токен аккаунта (account_hash)'
    )

    args = parser.parse_args()

    setup_logging(args.logging)

    user_token = args.user_token

    if user_token is None:
        try:
            with open('register_info.json', 'r') as f:
                user_info = json.load(f)
                user_token = user_info.get('account_hash')
        except FileNotFoundError:
            user_token = None
            print('Зарегестрируйтесь командой: python3 write_chat.py --user-name "Ваше имя"')

    if user_token is None:
        name = args.user_name or user_name_default
        name = name.strip() or "Anonymous"
        user_token = asyncio.run(register_user(args.host, args.port, name))
        return

    if args.user_name is not None:
        name = args.user_name
        if not name:
            name = env.str('USER_NAME', 'NewUser')
        asyncio.run(register_user(args.host, args.port, name))
        return

    if args.message and user_token:
        asyncio.run(submit_message(args.host, args.port, args.message, user_token))
    elif not args.message:
        print('Для отправки сообщение используйте команду: python3 write_chat.py --message "Текст сообщения"')


if __name__ == "__main__":
    main()

