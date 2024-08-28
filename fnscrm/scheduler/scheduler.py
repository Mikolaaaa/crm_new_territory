from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from django_apscheduler.models import DjangoJobExecution
import sys
from crm.bot.my_app_telegram_functions import get_chat_members_count, get_like_and_dislike, send_message
import asyncio
from crm.models import СhatMembersCount, QuestionAnswerLog, UserForPost
from django.db.models import Q
import configparser
import json
from datetime import timedelta
import datetime
from django.db.models import Count

# Считываем учетные данные
config = configparser.ConfigParser()
config.read("config.ini")

# Присваиваем значения внутренним переменным
api_id       = config['Telegram']['api_id']
api_hash     = config['Telegram']['api_hash']
api_bot      = config['Telegram']['api_bot']
username     = config['Telegram']['username']
usernamebot  = config['Telegram']['usernamebot']
chat_id      = int(config['Telegram']['chat_id'])
test_chat_id = int(config['Telegram']['test_chat_id'])
server_ip    = config['CRM']['server_ip']
server_port  = config['CRM']['server_port']

def update_chat_members_count():
    
    count = asyncio.run(get_chat_members_count())
        
    СhatMembersCount.objects.create(datetime_of_the_cut=timezone.now(), count=count)

def update_like_and_dislike_posts():
    
    q_where = Q()
    q_where.add(~Q(id_message_answer=None), Q.AND)
    q_where.add(~Q(id_message=0), Q.AND) # Актуальные вопросы
    q_where.add(~Q(id_message=1), Q.AND) # Первоначальная загрузка, которые без id
    
    # Соберем реакции по боевому каналу
    q_where_chat = Q(q_where)
    q_where_chat.add(Q(it_test=False), Q.AND)
    list_id_messages = QuestionAnswerLog.objects.filter(q_where_chat).values_list('id_message_answer', flat=True)
    
    if len(list_id_messages) != 0:
        list_id_messages = asyncio.run(get_like_and_dislike(chat_id, list_id_messages))
        
        for message in list_id_messages:
            try:
                message_object = QuestionAnswerLog.objects.get(Q(id_message_answer=message['id_message_answer']) & Q(it_test=False))
                message_object.like = message['like']
                message_object.dislike = message['dislike']
                message_object.save()
            except:
                mes = message

    # Соберем реакции по тестовому каналу
    q_where_test_chat = Q(q_where)
    q_where_test_chat.add(Q(it_test=True), Q.AND)
    list_id_messages = QuestionAnswerLog.objects.filter(q_where_test_chat).values_list('id_message_answer', flat=True)
    
    if len(list_id_messages) != 0:
        list_id_messages = asyncio.run(get_like_and_dislike(test_chat_id, list_id_messages))
        
        for message in list_id_messages:
            message_object = QuestionAnswerLog.objects.get(Q(id_message_answer=message['id_message_answer']) & Q(it_test=True))
            message_object.like = message['like']
            message_object.dislike = message['dislike']
            message_object.save()

def sending_overdue_messages():
    
    # Получим все сообщения без ответа
    all_not_answer_messages = QuestionAnswerLog.objects.filter(Q(it_test=False) & \
                                                            Q(answer_text=None) & \
                                                            Q(datetime=None))
    
    # Подсчитаем количество всех сообщений без ответа
    not_answer_messages = all_not_answer_messages.values('category__name', 'category').\
                                                annotate(count_questions=Count('question')).\
                                                order_by('category__id_post')
    
    # Подсчиатем количество переадресаций без согласования
    retarget_messages = all_not_answer_messages.filter(~Q(retarget_category=None)).\
                                                    values('category').\
                                                    annotate(count_questions=Count('question'))
    
    # Подсчитаем количетво просрочки
    overdue_messages = all_not_answer_messages.filter(Q(retarget_category=None) & \
                                                      Q(datetime_question__lte=(timezone.now() - datetime.timedelta(days=2)))).\
                                                    values('category').\
                                                    annotate(count_questions=Count('question'))

    for message in not_answer_messages:
        
        if message['count_questions'] == 0:
            continue

        # Сформируем текст сообщения
        text_message = f"""По теме: "{message["category__name"]}" 
Количество неотвеченных вопросов: {message["count_questions"]}"""
        
        if not overdue_messages.get(message['category']) is None:
            text_message += f"""\nКоличество просроченных вопросов: {overdue_messages.get(message['category'])["count_questions"]}"""
        
        if not retarget_messages.get(message['category']) is None:
            text_message += f"""\nКоличество несогласованных переадресаций: {retarget_messages.get(message['category'])["count_questions"]}"""

        text_message += '\nСсылки на сообщения:'

        for question in all_not_answer_messages:
            link_category = str(chat_id)
            link_post = str(question.category.id_post)
            link_category = link_category.replace('-100', '')
            text_message += f'\nhttps://t.me/c/{link_category}/{question.id_message_answer}?thread={link_post}'
        
        users_for_post = UserForPost.objects.filter(Q(category=message['category']), ~Q(user__first_name=''))

        for user_for_post in users_for_post:
            asyncio.run(send_message(user_for_post.user.first_name, text_message=text_message))

def start():
    scheduler = BackgroundScheduler()
    ds = DjangoJobStore()
    scheduler.add_jobstore(ds, "default")
    job1_it = False
    job2_it = False
    job3_it = False
    for i in ds.get_all_jobs():
        if i.id == 'update_chat_members_count':
            job1_it = True
        if i.id == 'update_like_and_dislike_posts':
            job2_it = True
        if i.id == 'sending_overdue_messages':
            job3_it = True

    if not job1_it:
        scheduler.add_job(update_chat_members_count, 'cron', hour=23, name='test', jobstore='default', id='update_chat_members_count')
    
    if not job2_it:
        scheduler.add_job(update_like_and_dislike_posts, 'cron', hour=23, minute=15, name='test', jobstore='default', id='update_like_and_dislike_posts')
    
    if not job3_it:
        scheduler.add_job(sending_overdue_messages, 'cron', day_of_week='1,3', hour=9, name='test', jobstore='default', id='sending_overdue_messages')

    register_events(scheduler)
    scheduler.start()
    print("Scheduler started...", file=sys.stdout)