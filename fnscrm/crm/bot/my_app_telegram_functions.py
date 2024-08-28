import configparser
import json
import requests
import sys

# для корректного переноса времени сообщений в json
from datetime import date, datetime

import asyncio

from pyrogram import Client
from pyrogram.types import (
    ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply) 

import pandas as pd
import numpy as np

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id           = config['Telegram']['api_id']
api_hash         = config['Telegram']['api_hash']
username         = config['Telegram']['username']
username_func    = config['Telegram']['usernamefunc']
api_bot          = config['Telegram']['api_bot']
usernamebot_func = config['Telegram']['usernamebotfunc']
chat_id          = int(config['Telegram']['chat_id'])
chanel_id        = int(config['Telegram']['chanel_id'])
test_chat_id     = int(config['Telegram']['test_chat_id'])

if len(sys.argv) > 1:
    arg_bot = sys.argv[1]
    if arg_bot == '-bot':
        it_bot = True
else:
    it_bot = False

columns = ['ИД', 'Название']

async def send_message(id_user = None, id_message = None, text_message = '', app=None):
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        if id_message == None:
            message = await app.send_message(id_user, text_message)
        else:
            message = await app.send_message(id_user, text_message, reply_to_message_id=id_message)

        return message.id

async def get_like_and_dislike(chat_id, list_messages):
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:

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

async def send_message_bot(id_user, id_message, it_test):
    
    text_message = 'Пожалуйста, оцените качество ответа специалиста.'

    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
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
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        count = await app.get_chat_members_count(chanel_id)

        return count
    
async def search_message(list_text_questions):
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        new_list_q_a_search = []
        for item in list_text_questions:
            
            dict_message = None

            async for message in app.search_messages(chat_id, query=' '.join(item['question'][:100].split(' ')[:-1]), limit=100):
                
                if message.text != item['question']:
                    continue

                if message.reply_to_message_id != None:
                    dict_message = item.copy()
                    reply_message = await app.get_messages(chat_id, message.reply_to_message_id)

                    dict_message['id_message'] = message.id
                    if reply_message.reply_to_message_id != None:
                        dict_message['reply_to_message_id'] = message.reply_to_message_id

                    if item['answer_text'] != '' and item['answer_text'] != None:
                        async for message_answer in app.search_messages(chat_id, query=' '.join(item['answer_text'][:100].split(' ')[:-1]), limit=100):
                            
                            if message_answer.text != item['answer_text']:
                                continue
                            
                            dict_message['id_message_answer'] = message_answer.id

            if dict_message != None:
                new_list_q_a_search.append(dict_message)
        
    return new_list_q_a_search

async def get_users():
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        user = await app.get_users('me')

        return user

async def edit_message(id_user = None, id_message = None, text_message = '', app=None):
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        message = await app.edit_message_text(id_user, id_message, text_message)

async def get_last_id_message():
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        async for message in app.get_chat_history(chat_id, limit=1):
            return message.id
        
async def get_message(id_message):
    async with Client(username_func, api_id, api_hash, no_updates=True) as app:
        async for message in app.get_messages(chat_id, id_message):
            return message.id