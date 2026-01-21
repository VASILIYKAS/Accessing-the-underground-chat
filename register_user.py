import asyncio
import json
import tkinter as tk
from tkinter import messagebox

import aiofiles


entry = None
button = None
label = None
root = None


def register_user():
    username = entry.get().strip()
    
    if not username:
        messagebox.showwarning('Ошибка', 'Пожалуйста, введите имя!')
        return
    
    button.config(state='disabled')
    label.config(text='Регистрация...', fg='blue')
    
    asyncio.run(register_async(username))


async def register_async(username):
    try:
        reader, writer = await asyncio.open_connection('minechat.dvmn.org', 5050)
        
        try:
            await reader.readline()
            writer.write(b'\n')
            await writer.drain()
            await reader.readline()
            writer.write(f'{username}\n'.encode('utf-8'))
            await writer.drain()
            response = await reader.readline()
            user_data = json.loads(response.decode('utf-8'))
            
            async with aiofiles.open('register_info.json', 'w', encoding='utf-8') as f:
                await f.write(response.decode('utf-8'))
            
            label.config(text='Успешно!', fg='green')
            messagebox.showinfo('Регистрация успешна!', f'Вы зарегистрированы как {user_data['nickname']}!\nДанные сохранены в register_info.json')
            root.destroy()
            
        finally:
            writer.close()
            await writer.wait_closed()
            
    except Exception as e:
        label.config(text='Ошибка!', fg='red')
        messagebox.showerror('Ошибка', f'Не удалось зарегистрироваться:\n{str(e)}')
        button.config(state='normal')


def main():
    global entry, button, label, root

    root = tk.Tk()
    root.title('Регистрация пользователя')
    root.geometry('350x150')

    label = tk.Label(root, text='Введите имя:', font=('Arial', 10))
    label.pack(pady=10)

    entry = tk.Entry(root, width=30, font=('Arial', 10))
    entry.pack(pady=5)
    entry.focus()

    button = tk.Button(root, text='Зарегистрироваться', command=register_user, font=('Arial', 10))
    button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()