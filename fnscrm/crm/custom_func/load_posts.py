import pandas as pd
import numpy as np
from crm.models import Category, QuestionAnswerLog, TagsForFind, UserForPost
import configparser
import json
from django.utils import timezone
from django.db.models import Q
from django.utils.timezone import make_aware
import datetime
from django.contrib.auth.models import User

def load_posts_in_csv():

    config = configparser.ConfigParser()
    config.read("C:/Server/data/htdocs/fnscrm/crm/bot/config.ini")

    data = pd.read_csv(config['CRM']['path_file_post'], sep=';', index_col='id')

    count = 0

    for i in data.index:
        if Category.objects.filter(id_post=i).count() == 0:
            Category(name=data.loc[i, 'caption'], id_post=i).save()
            count += 1
    
    return count

def load_question_answer():
    
    config = configparser.ConfigParser()
    config.read("C:/Server/data/htdocs/fnscrm/crm/bot/config.ini")

    data = pd.read_csv(config['CRM']['path_file_question'], sep='&')

    date_question_column = None
    if 'Дата вопроса' in data.columns:
        date_question_column = 'Дата вопроса'

    date_answer_column = None
    if 'Дата ответа' in data.columns:
        date_answer_column = 'Дата ответа'

    count = 0
    count_false = 0
    count_update = 0

    for i in data.index:
        categorys = Category.objects.filter(Q(name__icontains=data.loc[i, 'Тема']+'.'))
        if len(categorys) == 1 and QuestionAnswerLog.objects.filter(Q(question=data.loc[i, 'Вопрос'])).count() == 0:

            if date_question_column == None:
                date_question = timezone.now()
            else:
                try:
                    date_question = make_aware(datetime.datetime.strptime(data.loc[i, date_question_column], '%Y-%m-%d %H:%M:%S'))
                except:
                    date_question = timezone.now()

            if date_answer_column == None:
                date_answer = timezone.now()
            else:
                if str(data.loc[i, date_answer_column]) == 'nan':
                    date_answer = None
                else:
                    try:
                        date_answer = make_aware(datetime.datetime.strptime(data.loc[i, date_answer_column], '%Y-%m-%d %H:%M:%S'))
                    except:
                        date_answer = timezone.now()

            try:
                it_finaly = data.loc[i, 'Ответ'] != np.nan
                QuestionAnswerLog(question=data.loc[i, 'Вопрос'],
                                answer_text=data.loc[i, 'Ответ'],
                                category=categorys[0],
                                it_finaly=it_finaly,
                                id_message=1,
                                datetime_question=date_question,
                                datetime=date_answer,
                                like=data.loc[i, 'Количество лайков'],
                                dislike=data.loc[i, 'Количество дизлайков']).save()
                count += 1
            except:
                count_false += 1

        elif len(categorys) == 1 and QuestionAnswerLog.objects.filter(Q(question=data.loc[i, 'Вопрос'])).count() == 1:
            question = QuestionAnswerLog.objects.filter(Q(question=data.loc[i, 'Вопрос']))[0]
            if data.loc[i, 'Ответ'] == np.nan or question.answer_text == 'nan':
                question.answer_text = None
                question.it_finaly = False
                question.save()
                count_update += 1
            else:
                question.datetime_question=date_question,
                question.datetime=date_answer,
                question.like=data.loc[i, 'Количество лайков'],
                question.dislike=data.loc[i, 'Количество дизлайков'],
                question.answer_text=data.loc[i, 'Ответ']    
                question.save()
                count_update += 1

        
    
    return count, count_false, count_update

def load_tags():
    
    config = configparser.ConfigParser()
    config.read("C:/Server/data/htdocs/fnscrm/crm/bot/config.ini")

    data = pd.read_csv(config['CRM']['path_file_tags'], sep=';')

    count = 0

    for i in data.index:
        categorys = Category.objects.filter(Q(name__icontains=data.loc[i, 'Тема']))
        tags = data.loc[i, 'Теги'].split('#')
        if len(categorys) == 1:
            for tag in set(tags):
                if TagsForFind.objects.filter(Q(name=tag)).count() == 0:
                    TagsForFind(name=tag, category=categorys[0]).save()
                count += 1
    
    return count

def create_users():

    config = configparser.ConfigParser()
    config.read("C:/Server/data/htdocs/fnscrm/crm/bot/config.ini")

    data = pd.read_csv(config['CRM']['path_file_users'], sep=';')

    count = 0

    for i in data.index:
        
        users = User.objects.filter(username=data.loc[i, 'Логин'])
        if len(users) == 0:
            user = User.objects.create_user(username=data.loc[i, 'Логин'], password=data.loc[i, 'Пароль'], last_name=data.loc[i, 'Модер'])
            categorys = Category.objects.filter(Q(name__icontains=(f'Тема № {data.loc[i, "Тема"]}.')))
            UserForPost.objects.create(user=user, category=categorys[0], it_moder=True)
            count += 1

        