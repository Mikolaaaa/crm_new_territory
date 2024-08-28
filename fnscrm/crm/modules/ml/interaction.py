import requests
import configparser
from crm.models import Category, QuestionAnswerLog
from django.db.models import Count, Sum, Max

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id            = config['Telegram']['api_id']
api_hash          = config['Telegram']['api_hash']
username          = config['Telegram']['username']
username_func     = config['Telegram']['usernamefunc']
api_bot           = config['Telegram']['api_bot']
usernamebot_func  = config['Telegram']['usernamebotfunc']
chat_id           = int(config['Telegram']['chat_id'])
test_chat_id      = int(config['Telegram']['test_chat_id'])
server_ip         = config['CRM']['server_ip']
server_port_model = int(config['CRM']['server_port_model'])

def get_list_of_hints_ml(indexs: list[int]):

    url = f'http://{server_ip}:{server_port_model}/k-top-questions'
    data = {'indexs': indexs}
    try:
        response = requests.post(url, json=data)
    except:
        return {}
    
    if response.status_code != 200:
        return {}
    
    data_output = response.json()
    data_message = {}
    for index in data_output['indexs']:
        data_message[index] = QuestionAnswerLog.objects.filter(id__in=data_output['indexs'][index]).\
            values('answer_text').\
            annotate(count_questions=Count('question'), max_datetime_answer=Max('datetime'), question=Max('question')).\
            order_by('-count_questions')

    return data_message

def get_list_retarget_category_ml(indexs: list[dict]):

    url = f'http://{server_ip}:{server_port_model}/k-top-category'
    data = {'indexs': indexs}
    try:
        response = requests.post(url, json=data)
    except:
        return {}
    
    if response.status_code != 200:
        return {}
    
    data_output = response.json()
    data_message = {}
    for index in data_output['indexs']:
        data_message[index] = Category.objects.filter(id__in=data_output['indexs'][index])

    return data_message

def encode_question(question: str, 
                    id: int, 
                    id_category: int):

    url = f'http://{server_ip}:{server_port_model}/k-top-category'
    data = {"question": question, "id": id, "id_category": id_category}
    
    try:
        response = requests.post(url, json=data)
    except:
        return False

    return response.status_code != 200