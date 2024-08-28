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

from tqdm import tqdm

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id       = config['Telegram']['api_id']
api_hash     = config['Telegram']['api_hash']
username     = config['Telegram']['username']
api_bot      = config['Telegram']['api_bot']
chat_id      = config['Telegram']['chat_id']
test_chat_id = config['Telegram']['test_chat_id']
only_post = True

columns = ['Дата ответа',
           'Ответ',
           'ИД ответа',
           'ИД вопроса',
           'Вопрос',
           'Дата вопроса',
           'ИД категории',
           'Текст категории',
           'Лайк',
           'Дизлайк']

app = Client(username, api_id, api_hash)

async def main(chat):
    async with app:
        message_list = []
        message_full_list = []
        message_post_list = []
        dict_message_question = {}
        print('Получение количества сообщений...')
        message_count = await app.get_chat_history_count(chat)
        print('Получение сообщений:')
        message_count = tqdm(total=message_count)
        async for message in app.get_chat_history(chat): 
            message_count.update(1)
            reactions = None
            if message.reactions != None:
                reactions = message.reactions.reactions
            

            user_id = None
            if message.from_user != None:
                user_id = message.from_user.id

            dict_message_question[message.id] = {'text': message.text, 
                                                 'date': message.date,
                                                 'id': message.id,
                                                 'reply_to_message_id': message.reply_to_message_id,
                                                 'reactions':reactions,
                                                 'reply_to_top_message_id': message.reply_to_top_message_id,
                                                 'outgoing': message.outgoing,
                                                 'user_id': user_id,
                                                 'caption': message.caption}
            message_full_list.append(dict_message_question[message.id])
            
            if message.caption != None:
                message_post_list.append(dict_message_question[message.id])

        message_count.close()
        pd.DataFrame(message_full_list).to_excel(f'history_full_{chat}.xlsx')
        pd.DataFrame(message_post_list).to_excel(f'history_post_{chat}.xlsx')

        print('Финальная обработка сообщений')
        for message in tqdm(message_full_list):
            if message['reply_to_top_message_id'] == None or not (message['outgoing'] or message['user_id'] == None):
                continue

            reactions = {}
            like = 0
            dislike = 0
            if message['reactions'] != None:
                for react in message['reactions']:
                    reactions[react.emoji] = react.count
                    if react.emoji == '👍':
                        like = react.count
                    elif react.emoji == '👎':
                        dislike = react.count

            # Если исходного сообщения нет, возможно оно было удалено
            # Игнорируем такое сообщение
            try:
                reply_message = dict_message_question[message['reply_to_message_id']]
                reply_top_message = dict_message_question[message['reply_to_top_message_id']]
            except:
                continue
            message_list.append([message['date'], 
                                message['text'], 
                                message['id'],
                                message['reply_to_message_id'],
                                reply_message['text'],
                                reply_message['date'],
                                message['reply_to_top_message_id'],
                                reply_top_message['caption'],
                                like,
                                dislike])
        pd.DataFrame(message_list, columns=columns).to_excel(f'history_{chat}.xlsx')
        

app.run(main(test_chat_id))