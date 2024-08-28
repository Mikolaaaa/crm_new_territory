import configparser
import json
import requests

# для корректного переноса времени сообщений в json
from datetime import date, datetime

import asyncio

import json

from pyrogram import Client

import pandas as pd
import numpy as np

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("crm/bot/config.ini")

# Присваиваем значения внутренним переменным
api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']

columns = ['ИД', 'Название']

app = Client(username, api_id, api_hash)

async def main():
    async with app:
        chat_list = []

        # async for dialog in app.get_dialogs():
        #     chat_list.append([dialog.chat.id, dialog.chat.title])


        # pd.DataFrame(chat_list, columns=columns).to_csv('chats1.csv')
        message_count = await app.get_chat_history_count('-1002234314592')
        print(message_count)

app.run(main())