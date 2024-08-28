import configparser
import json
import requests
import sys
import random

# для корректного переноса времени сообщений в json
from datetime import date, datetime

import asyncio

from pyrogram import Client
from pyrogram.types import (
    ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply) 

import pandas as pd
import numpy as np

config = configparser.ConfigParser()
config.read("C:/Server/data/htdocs/fnscrm/crm/bot/config.ini")

# Присваиваем значения внутренним переменным
api_id           = config['Telegram']['api_id']
api_hash         = config['Telegram']['api_hash']
username         = "C:/Server/data/htdocs/fnscrm/programm/mysessionfns"#config['Telegram']['username']
username_func    = "C:/Server/data/htdocs/fnscrm/programm/mysessionfns"#config['Telegram']['usernamefunc']
api_bot          = config['Telegram']['api_bot']
usernamebot_func = config['Telegram']['usernamebotfunc']
chat_id          = int(config['Telegram']['chat_id'])
chanel_id          = int(config['Telegram']['chanel_id'])
test_chat_id     = int(config['Telegram']['test_chat_id'])
server_port = 443
server_ip = 'data-science-sladkiy-keks-molibden.ru'

messeges_id = []

if len(sys.argv) > 1:
    arg_bot = sys.argv[1]
    if arg_bot == '-bot':
        it_bot = True
else:
    it_bot = False

columns = ['ИД', 'Название']

async def get_chat_history_tg(limit):

    async with Client(username, api_id, api_hash) as app:
        
        list_messages = []
        async for message in app.get_chat_history(chat_id, limit=limit):
            list_messages.append(message)

        return list_messages
    
async def send_message(id_user = None, id_message = None, text_message = '', app=None):
    async with Client(username, api_id, api_hash) as app:
        if id_message == None:
            message = await app.send_message(id_user, text_message)
        else:
            message = await app.send_message(id_user, text_message, reply_to_message_id=id_message)

        return message.id

async def get_like_and_dislike(chat_id, list_messages):
    async with Client(username_func, api_id, api_hash) as app:

        list_messages_new = list_messages[:]

        for batch in range(int(round(len(list_messages)/200 + 0.5, 0))):
            start_index = batch * 200
            if start_index + 200 <= len(list_messages):
                end_index = start_index + 200
            else:
                end_index = len(list_messages)

            i = start_index
            l1 = await app.get_messages(chat_id, list_messages_new[start_index:end_index]) 
            for message in l1:
                reactions = None
                like = 0
                dislike = 0
                if message.reactions != None:
                    reactions = message.reactions.reactions
                    for reaction in reactions:
                        if reaction.emoji == '👍':
                            like = reaction.count
                        elif reaction.emoji == '👎':
                            dislike = reaction.count
                
                list_messages_new[i] = {'id_message_answer': list_messages_new[i], 'like': like, 'dislike': dislike}
                i += 1

        return list_messages_new
#         print(list_messages_new)

async def send_message_bot(id_user, id_message, it_test):
    
    text_message = 'Пожалуйста, оцените качество ответа специалиста.'

    async with Client(username_func, api_id, api_hash) as app:
        await app.send_message(id_user, text_message, reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Полностью удовлетворен 😊", callback_data=f"{it_test_number}_{id_message}_1")],
                [InlineKeyboardButton("Частично удовлетворен 😐", callback_data=f"{it_test_number}_{id_message}_2")],
                [InlineKeyboardButton("Не удовлетворен ☹️", callback_data=f"{it_test_number}_{id_message}_3")]
            ],
            ))
        print('Сообщение:', id_message)
        print('------------------------------------------')
    
async def get_chat_members_count():
    async with Client(username_func, api_id, api_hash) as app:
        count = await app.get_chat_members_count(chanel_id)

        return count
    
async def search_message(list_text_questions, get_user=False):
  
    async with Client(username, api_id, api_hash) as app:
        new_list_q_a_search = []
        for item in list_text_questions:
            
            dict_message = None

            str1 = ' '.join(item['question'][:100].split(' ')[:-1])
            if str1 == '':
                str1 = item['question']
                
            async for message in app.search_messages(chat_id, query=str1, limit=1000):

                if str(message.text).replace('\xa0', ' ').find(item['question']) == -1:
                    continue

                if dict_message == None:
                    dict_message = item.copy()
                    dict_message['id_message'] = message.id
                    dict_message['count'] = 1
                else:
                    dict_message['count'] += 1

                if get_user:
                    dict_message['user'] = message.from_user 

                # if message.reply_to_message_id != None:
                #     dict_message = item.copy()
                #     reply_message = await app.get_messages(chat_id, message.reply_to_message_id)

                #     dict_message['id_message'] = message.id
                    # if reply_message.reply_to_message_id != None:
                    #     dict_message['reply_to_message_id'] = message.reply_to_message_id

                    # if item['answer_text'] != '' and item['answer_text'] != None:
                    #     async for message_answer in app.search_messages(chat_id, query=' '.join(item['answer_text'][:100].split(' ')[:-1]), limit=100):
                            
                    #         if message_answer.text != item['answer_text']:
                    #             continue
                            
                    #         dict_message['id_message_answer'] = message_answer.id

            # if dict_message != None:
            #     new_list_q_a_search.append(dict_message)
        
    return dict_message

async def get_users():
    async with Client(username_func, api_id, api_hash) as app:
        user = await app.get_users('me')

        return user

async def get_message_chat(chat_id, id):
    async with Client(username, api_id, api_hash) as app:

        return await app.get_messages(chat_id, id)
    

async def get_smart_response(message, 
                       id_message, 
                       reply_to_top_message_id, 
                       chat_id, 
                       reply_to_message_id,
                       id_question_author):
    try:
        data = {"message": message, 
                "id_message": id_message, 
                "id_category": reply_to_top_message_id, 
                "id_chat": chat_id,
                "id_question_author": id_question_author}
        if reply_to_message_id != None:
            data["reply_to_message_id"] = reply_to_message_id
        if int(server_port) == 443:
            http_pre = 'https'
        else:
            http_pre = 'http'
        url = f'{http_pre}://{server_ip}:{server_port}/crm/api/smart-response'
        print(f'{datetime.now()} щас буду выполнять пост запрос...')
        response = requests.post(url, data=data)
        print(f'{datetime.now()} выполнил пост запрос.')
        if response.status_code == 200:
            text_answer = json.loads(response.text)['answer']
            if text_answer != '':
                return {'text': json.loads(response.text)['answer'], 'error': False}
            else:
                return {'text': 'Получен пустой ответ. Ответа нет в базе. Создана заявка.', 'error': True}
        else:
            return {'text': f'Получил плохой ответ от сервера: {response.status_code}', 'error': True}
    except:
        return {'text': f'Упс, сервер не доступен!', 'error': True}

async def send_moder_response(username, reply_to_message_id, it_test, text):
    try:
        data = {"username": username,
                "reply_to_message_id": reply_to_message_id,
                "it_test": it_test,
                "text": text}
        
        if int(server_port) == 443:
            http_pre = 'https'
        else:
            http_pre = 'http'
        url = f'{http_pre}://{server_ip}:{server_port}/crm/api/send-moder-response'
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return {'succes': False, 'answer': response.text}
    except:
        return {'succes': False, 'answer': 'Непредвиденная ошибка'}

async def response_message(message):

    async with Client(username, api_id, api_hash) as app:
        guid = random.randint(0, 10)

        print('-------------------------------------------')
        print(f'гуид: {guid} | {datetime.now()} Получаю вопрос:')
        print(message.text)

        succes = False

        if message.from_user == None:
            # print(message)
            return

        if (message.forwards == None and 
            message.outgoing == False):
            moder_response = await send_moder_response(message.from_user.username, message.reply_to_message_id, message.chat.id == test_chat_id, message.text)
            print(guid, moder_response)
            succes = moder_response['succes']
        
        if succes:
            return

        # Если это не пост
        # Если это тестовый канал и тег вопрос
        # Или если это основной канал, то без тега
        # И это не сообщение от канала
        if (message.forwards == None and 
            message.outgoing == False and
            ((message.text != None and '#вопрос' in message.text.lower() and message.chat.id == test_chat_id) or message.chat.id == chat_id)):
            
            print(f'гуид: {guid} | {datetime.now()} получаю предыдущее сообщение...')
            category = await app.get_messages(message.chat.id, message.reply_to_message_id)
            print(f'гуид: {guid} | {datetime.now()} получил предыдущее сообщение.')

            print(f'гуид: {guid} | {datetime.now()} начинаю поиск категории. Ищу пока не упрусь в последнее сообщение...')
            while category.reply_to_message != None:

                print(f'гуид: {guid} | {datetime.now()} ещё не последнее. Получаю следующее...')
                category = await app.get_messages(message.chat.id, category.reply_to_message_id)
                print(f'гуид: {guid} | {datetime.now()} получил иду на следующий заход...')

            print(f'гуид: {guid} | {datetime.now()} кончились сообщения.')

            reply_to_message_id = None

            print(f'гуид: {guid} | {datetime.now()} если предыдущее сообщение не равно первому, то берем репли ту месседж из предыдущего. Для сохранения цепочки сообщений.')
            if message.reply_to_message_id != category.id:
                print(f'гуид: {guid} | {datetime.now()} условие истинно. Получаем предудыщее сообщение...')
                answer = await app.get_messages(message.chat.id, message.reply_to_message_id)
                print(f'гуид: {guid} | {datetime.now()} получили предудещее сообщение.')
                reply_to_message_id = answer.reply_to_message_id
                print(f'гуид: {guid} | {datetime.now()} взяли из него репли ту месседж')

            print(f'гуид: {guid} | {datetime.now()} получаем автора сообщения...')
            if message.from_user == None:
                print(f'гуид: {guid} | {datetime.now()} нет автора.')
                id_question_author = None 
            else:
                print(f'гуид: {guid} | {datetime.now()} есть автор. Берем его.')
                id_question_author = message.from_user.id  
            print(f'гуид: {guid} | {datetime.now()} вызываем процедурку отправки запроса...') 
            response = await get_smart_response(message.text, 
                                        message.id, 
                                        category.id, 
                                        message.chat.id, 
                                        reply_to_message_id,
                                        id_question_author)
            print(f'гуид: {guid} | {datetime.now()} Это вопрос требующий ответа!')

            if response['error']:
                print(f'гуид: {guid} | {datetime.now()} {response["text"]}')
    
# app = Client(usernamebot_func, api_id, api_hash)
# app.run(search_message())
# text = """1109005778"""
# l = [{'question': text, 'answer_text': ''}
#      ]
# print(asyncio.run(search_message(l)))
# # asyncio.run(send_message_bot('alvis_44', 123))
