import configparser
import json
import requests
import sys
import random
from difflib import SequenceMatcher
import logging

# для корректного переноса времени сообщений в json
from datetime import date, datetime
import asyncio

from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, DeletedMessagesHandler
from pyrogram.types import (
    ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply) 

from dotmap import DotMap

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

logging.basicConfig(level=logging.INFO, filename="tg_log.log",filemode="a", encoding='utf-8')

# Присваиваем значения внутренним переменным
api_id         = config['Telegram']['api_id']
api_hash       = config['Telegram']['api_hash']
api_bot        = config['Telegram']['api_bot']
username       = config['Telegram']['username']
usernamebot    = config['Telegram']['usernamebot']
chat_id        = int(config['Telegram']['chat_id'])
test_chat_id   = int(config['Telegram']['test_chat_id'])
login_tg_admin = config['Telegram']['login_tg_admin']
server_ip      = config['CRM']['server_ip']
server_port    = int(config['CRM']['server_port'])

if len(sys.argv) > 1:
    arg_bot = sys.argv[1]
    if arg_bot == '-bot':
        it_bot = True
else:
    it_bot = False

messeges_id = list()

async def similarity(a,b):
    seq = SequenceMatcher(a=a, b=b)
    return seq.ratio()

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
        logging.info(f'{datetime.now()} щас буду выполнять пост запрос...')
        response = requests.post(url, data=data)
        logging.info(f'{datetime.now()} выполнил пост запрос.')
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

async def send_moder_response(username, reply_to_message_id, it_test, text, id_message):
    try:
        data = {"username": username,
                "reply_to_message_id": reply_to_message_id,
                "it_test": it_test,
                "text": text,
                "id_message": id_message}

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

async def response_message(client, message):

        global messeges_id

        # Костыль на случай дублирования сообщения, был такой почему то
        if message.id in messeges_id:
            return
        else:
            messeges_id.append(message.id)
        
        guid = random.randint(0, 10)

        logging.info('-------------------------------------------')
        logging.info(f'гуид: {guid} | {datetime.now()} Получаю вопрос:')
        logging.info(message.text)

        succes = False

        if message.from_user == None or message.reply_to_message_id == None:
            return 'Вопрос не в блоке или вообще не вопрос'

        if (message.forwards == None and 
            message.outgoing == False):
            moder_response = await send_moder_response(message.from_user.username, message.reply_to_message_id, message.chat.id == test_chat_id, message.text, message.id)
            logging.info(f'гуид: {guid} | {moder_response}')
            succes = moder_response['succes']
        
        if succes:
            return 'Ответ модератора загружен'

        # Если это не пост
        # Если это тестовый канал и тег вопрос
        # Или если это основной канал, то без тега
        # И это не сообщение от канала
        if (message.forwards == None and 
            message.outgoing == False and
            ((message.text != None and '#вопрос' in message.text.lower() and message.chat.id == test_chat_id) or message.chat.id == chat_id)):
            
            logging.info(f'гуид: {guid} | {datetime.now()} получаю предыдущее сообщение...')
            category = await app.get_messages(message.chat.id, message.reply_to_message_id)
            logging.info(f'гуид: {guid} | {datetime.now()} получил предыдущее сообщение.')

            logging.info(f'гуид: {guid} | {datetime.now()} начинаю поиск категории. Ищу пока не упрусь в последнее сообщение...')
            while category.reply_to_message != None:

                logging.info(f'гуид: {guid} | {datetime.now()} ещё не последнее. Получаю следующее...')
                category = await app.get_messages(message.chat.id, category.reply_to_message_id)
                logging.info(f'гуид: {guid} | {datetime.now()} получил иду на следующий заход...')

            logging.info(f'гуид: {guid} | {datetime.now()} кончились сообщения.')

            reply_to_message_id = None

            logging.info(f'гуид: {guid} | {datetime.now()} если предыдущее сообщение не равно первому, то берем репли ту месседж из предыдущего. Для сохранения цепочки сообщений.')
            if message.reply_to_message_id != category.id:
                logging.info(f'гуид: {guid} | {datetime.now()} условие истинно. Получаем предудыщее сообщение...')
                answer = await app.get_messages(message.chat.id, message.reply_to_message_id)
                logging.info(f'гуид: {guid} | {datetime.now()} получили предудещее сообщение.')
                reply_to_message_id = answer.reply_to_message_id
                logging.info(f'гуид: {guid} | {datetime.now()} взяли из него репли ту месседж')

            logging.info(f'гуид: {guid} | {datetime.now()} получаем автора сообщения...')
            if message.from_user == None:
                logging.info(f'гуид: {guid} | {datetime.now()} нет автора.')
                id_question_author = None 
            else:
                logging.info(f'гуид: {guid} | {datetime.now()} есть автор. Берем его.')
                id_question_author = message.from_user.id  
            logging.info(f'гуид: {guid} | {datetime.now()} вызываем процедурку отправки запроса...') 
            response = await get_smart_response(message.text, 
                                        message.id, 
                                        category.id, 
                                        message.chat.id, 
                                        reply_to_message_id,
                                        id_question_author)
            logging.info(f'гуид: {guid} | {datetime.now()} Это вопрос требующий ответа!')

            if response['error']:
                logging.info(f'гуид: {guid} | {datetime.now()} {response["text"]}')

                return response["text"] 

async def callback_data_message(client, message):

    logging.info('-------------------------------------------')
    logging.info(f'{datetime.now()} Возможно получил оценку на ответ')
    count = 0
    async for message_history in app.get_chat_history(message.from_user.id):
        logging.info(f'{datetime.now()} ищу предыдущее сообщение...')
        if count == 2:
            break

        message_link = message_history.text

        count += 1

    number_char_https = message_link.find('https')
    it_response = message_link.find('Пожалуйста, оцените качество ответа специалиста')
    if number_char_https != -1 and it_response != -1:
        logging.info(f'{datetime.now()} Да, это оценка, проверяю ответ')
        link = message_link[number_char_https:]
        link = link[:link.find('\n')]

        link_param = link.replace('https://t.me/c/', '').replace('?thread=', '/').split('/')
        
        text_message = 'Благодарим Вас за оценку!'
        await app.send_message(message.from_user.id, text_message)
        logging.info(f'{datetime.now()} Отправил сообщение с благодарностью!')

        it_test = f'-100{link_param[0]}' != str(chat_id)
        data = {'it_test': it_test, 'id_message': int(link_param[1]), 'score': int(message.text)}

        if int(server_port) == 443:
            http_pre = 'https'
        else:
            http_pre = 'http'
        response = requests.post(f'{http_pre}://{server_ip}:{server_port}/crm/api/update-score-answer', data=data)
        logging.info(f'{datetime.now()} Попытался дернуть апи')

async def response_message_test(client, message):
    
    logging.info('-------------------------------------------')
    logging.info(message.text)

async def delete_message(client, messages):

    logging.info('-------------------------------------------')
    logging.info(f'{datetime.now()} Кто-то удаляет сообщения:')
    
    list_messages = []
    for message in messages:
        logging.info(message.id)
        list_messages.append(message.id)

    data = {'list_messages': list_messages, 'chat_id': messages[0].chat.id}
    logging.info(data)

    if int(server_port) == 443:
            http_pre = 'https'
    else:
        http_pre = 'http'
    url = f'{http_pre}://{server_ip}:{server_port}/crm/api/delete-response'
    response = requests.post(url, data=data)
    if response.status_code == 200:
        logging.info(response.text)
    else:
        logging.info(f'Получил плохой ответ от сервера. {response.status_code}')


def load_messages():

    dict_add = {}
    arr_delete = []
    arr_score = []

    with open('load.log', encoding='utf-8') as f:
        
        arr_str = f.readlines()
        json_str = ''
        action = ''
        x = None
        
        for row in arr_str:
        
            if row[:len('INFO:root:message_obj')] == 'INFO:root:message_obj':
                json_str = '{'
                if row.find('add') != -1:
                    action = 'add'
                elif row.find('delete') != -1:
                    action = 'delete'
                elif row.find('score') != -1:
                    action = 'score'
            elif row[:4] == 'INFO' and json_str != '':
                x = eval(json_str)
                if action == 'add':
                    dict_add[x['id']] = x
                elif action == 'delete':
                    arr_delete.append(x)
                elif action == 'score':
                    arr_score.append(x)
                json_str = ''
            elif row[:4] != 'INFO' and json_str != '':
                json_str += row.replace('\n', ' ').replace('false', 'False').replace('true', 'True')

    for i in arr_delete:
        try:
            del dict_add[i['id']]
        except:
            pass

    count = 0
    print('Всего добавить нужно', len(dict_add))

    for i in dict_add:
        message = DotMap(dict_add[i])
        if message.forwards == DotMap():
            message.forwards = None
        if message.from_user == DotMap():
            message.from_user = None
        if message.text == DotMap():
            message.text = None
        if message.reply_to_message_id == DotMap():
            message.reply_to_message_id = None
        print(i)
        if i < 38643:
            continue
        asyncio.run(response_message(None, message=message))
        count += 1

    logging.info(f'Обработано предварительной загрузкой. {count}')

    open('load.log', 'w').close()

async def callback_message_load(client, message):

    global messeges_id
    messeges_id = list()

    text = message.text.replace('loadmessages:', '')
    if text.find(',') > -1:
        messages_list = [int(x) for x in text.split(',')]
    elif text.find(':') > -1:
        start_and_stop = text.split(':')
        messages_list = [i for i in range(int(start_and_stop[0]), int(start_and_stop[1]) + 1)]
    else:
        messages_list = [int(text)]

    messages = await app.get_messages(chat_id, messages_list)

    count_load_questions = 0
    count_load_answer = 0

    id_user_to_answer = message.from_user.id
    if message.from_user.is_self:
        id_user_to_answer = login_tg_admin

    if len(messages) > 50:
        await app.send_message(id_user_to_answer, f'Ого, это надолго...\nК загрузке {len(messages)} сообщений\nБудем ждать')

    for message_load in messages:
      
        response = await response_message(client, message=message_load)

        if response == 'Получен пустой ответ. Ответа нет в базе. Создана заявка.':
            count_load_questions += 1
        elif response == 'Ответ модератора загружен':
            count_load_answer += 1

    await app.send_message(id_user_to_answer, f'Загружено вопросов: {count_load_questions}\nЗагружено ответов: {count_load_answer}')
               

app = Client(username, api_id, api_hash, sleep_threshold=60)

app.add_handler(MessageHandler(response_message, filters.chat([chat_id, test_chat_id])), 0)
app.add_handler(MessageHandler(callback_data_message, filters.regex('^[1-4]$')), 1)
app.add_handler(DeletedMessagesHandler(delete_message, filters.chat([chat_id, test_chat_id])), 2)
app.add_handler(MessageHandler(callback_message_load, filters.regex('^loadmessages:*')), 3)

logging.info('======================================================')
logging.info(f'Тестовый канал: {test_chat_id}')
logging.info(f'Рабочий канал: {chat_id}')
logging.info(f'{datetime.now()}. Бот запущен... Подслушиваю чат.')
app.run()
logging.info(f'{datetime.now()}. Бот завершил работу.')

