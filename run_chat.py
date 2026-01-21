import argparse
import asyncio
import json
import logging
import socket
import time
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import aiofiles
import anyio
import gui
from async_timeout import timeout
from environs import Env
from exceptiongroup import catch


env = Env()
env.read_env()


watchdog_logger = logging.getLogger('watchdog')


class InvalidTokenError(Exception):
    pass


async def handle_connection(
    host: str,
    read_port: int,
    write_port: int,
    user_token: str,
    messages_queue,
    sending_queue,
    status_updates_queue,
    history_queue,
    watchdog_queue,
    task_status=anyio.TASK_STATUS_IGNORED
):

    reconnect_count = 0

    task_status.started()

    while True:
        def handle_connection_error(exc_group):
            exc = exc_group.exceptions[0]
            watchdog_logger.warning(f'Соединение разорвано: {exc}')
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            return None

        try:
            with catch({ConnectionError: handle_connection_error}):
                _, writer_w, nickname = await authorise(host, write_port, user_token, watchdog_queue)
                status_updates_queue.put_nowait(gui.NicknameReceived(nickname))

                async with anyio.create_task_group() as tg:
                    tg.start_soon(read_chat, host, read_port, messages_queue, history_queue, status_updates_queue, watchdog_queue)
                    tg.start_soon(send_msgs, writer_w, sending_queue, status_updates_queue, watchdog_queue)
                    tg.start_soon(send_keepalive, writer_w, sending_queue)
                    tg.start_soon(watch_for_connection, watchdog_queue)
            
        except socket.gaierror as e:
            if e.errno == -3:
                watchdog_logger.warning('Нет интернета. Повтор через 5 сек...')
            elif e.errno == -2:
                watchdog_logger.error('Хост не найден. Проверьте настройки.')
                return
            else:
                watchdog_logger.error(f'Ошибка: {e}')
            await anyio.sleep(5)
            continue
            
        except InvalidTokenError:
            messagebox.showerror('Ошибка токена', 'Неверный токен.')
            return


async def send_keepalive(writer, sending_queue):
    while True:
        try:
            writer.write(b'\n\n')
            await writer.drain()
            
            await asyncio.sleep(5)
            
        except (OSError, ConnectionError):
            raise ConnectionError('Keep-alive failed')


async def authorise(host, port, user_token, watchdog_queue):
    reader, writer = await asyncio.open_connection(host, port)

    try:
        welcome = await reader.readline()
        
        writer.write(f'{user_token}\n'.encode('utf-8'))
        await writer.drain()
        
        auth_response = await reader.readline()
        auth_data = json.loads(auth_response.decode())
        
        if auth_data is None:
            writer.close()
            await writer.wait_closed()
            raise InvalidTokenError('Неверный токен авторизации')
        else:
            user_name = auth_data['nickname']
        
        watchdog_queue.put_nowait('Authorization done')
        print(f'Выполнена авторизация. Пользователь {user_name}.')
        return reader, writer, user_name

    except InvalidTokenError:
        raise
        
    except Exception as e:
        writer.close()
        await writer.wait_closed()
        raise


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

        async with aiofiles.open('register_info.json', 'w', encoding='utf-8') as f:
            await f.write(server_response.decode())

        print(f'Вы успешно зарегестрировались! Ваше имя: {user_info['nickname']}')
        print('Данные сохранены в файле "register_info.json"')
        print('Для отправки сообщения используйте команду: python3 write_chat.py --message "Ваше сообщение"')

    finally:
        writer.close()
        await writer.wait_closed()


async def load_history(filepath, messages_queue):
    if not Path(filepath).exists():
        return

    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        async for line in f:
            line = line.strip()
            if line:
                messages_queue.put_nowait(line)


async def read_chat(host, port, messages_queue, history_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host, port)
    
    
    try:
        
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)

        while True:
            messages = await reader.readline()

            if not messages:
                break
            
            decoded_message = messages.decode('utf-8').strip()
            if decoded_message:
                timestamp = datetime.now().strftime('%Y.%m.%d %H:%M:%S')
                messages_queue.put_nowait(f'[{timestamp}] {decoded_message}')
                history_queue.put_nowait(decoded_message)
                watchdog_queue.put_nowait('New message in chat')

    finally:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


async def send_msgs(writer, sending_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    try:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

        while True:
            msg = await sending_queue.get()
            writer.write(f'{msg}\n\n'.encode('utf-8'))
            await writer.drain()
            watchdog_queue.put_nowait('Message sent')

    except Exception as e:
        print(f'Ошибка отправки: {e}')

    finally:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


async def save_messages(filepath, history_queue):
    log_dir = Path(filepath).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            timestamp = datetime.now().strftime('%Y.%m.%d %H:%M:%S')

            msg = await history_queue.get()

            async with aiofiles.open(filepath, 'a', encoding='utf-8') as f:
                await f.write(f'[{timestamp}] {msg}\n')

    except Exception as e:
        print(f'Ошибка при сохранении сообщений: {e}')


async def watch_for_connection(watchdog_queue):
    last_activity_time = time.time()
    
    while True:
        try:
            async with timeout(3) as cm:
                msg = await watchdog_queue.get()
                last_activity_time = time.time()
                
                current = int(time.time())
                watchdog_logger.info(f'[{current}] Connection is alive. Source: {msg}')
                continue

        except asyncio.TimeoutError:
            if cm.expired:
                idle_time = time.time() - last_activity_time
                if idle_time > 3:
                    msg = f'No activity for {idle_time:.1f} seconds — connection lost'
                    watchdog_logger.error(f'[{int(time.time())}] {msg}')
                    raise ConnectionError(msg)


async def main():
    logging.basicConfig(level=logging.INFO)

    host = env.str('HOST', 'minechat.dvmn.org')
    port_read = env.int('READ_PORT', 5000)
    port_write = env.int('WRITE_PORT', 5050)
    log_path = env.str('LOGS', 'underground_chat.txt')

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    history_queue = asyncio.Queue() 
    watchdog_queue = asyncio.Queue() 

    try:
        with open('register_info.json', 'r') as f:
            user_info = json.load(f)
            user_token = user_info.get('account_hash')
            user_name = user_info.get('nickname')

    except FileNotFoundError:
        user_token = None
        user_name = None
    
    if user_token is None:
        print('Токен не указан.')
        return

    await load_history(log_path, messages_queue)

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
            tg.start_soon(save_messages, log_path, history_queue)
            tg.start_soon(
                handle_connection,
                host, port_read, port_write, user_token,
                messages_queue, sending_queue, status_updates_queue, history_queue, watchdog_queue
            )

    except* gui.TkAppClosed:
        print('Окно закрыто пользователем')
        pass

    except* (KeyboardInterrupt, asyncio.CancelledError):
        print('\nПрограмма прервана пользователем (CTRL + C)')



if __name__ == "__main__":
    anyio.run(main)