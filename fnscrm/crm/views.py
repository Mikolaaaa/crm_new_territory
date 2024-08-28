from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views import generic
from .models import *
from django.contrib.auth import get_user_model
from .filters import *
from django.db.models import Count, Sum, Max
import random
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
from django.urls import reverse
from .forms import *
from django.utils import timezone
from crm.custom_func.load_posts import load_posts_in_csv, load_question_answer, load_tags, create_users
from crm.bot.my_app_telegram_functions import send_message, get_like_and_dislike, send_message_bot, get_chat_members_count, search_message, edit_message
from django.db import transaction
from django.db.models import Q
import csv
from django.http import FileResponse
import uuid
from django.db import connection
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from crm.modules.ml.interaction import get_list_of_hints_ml, get_list_retarget_category_ml, encode_question

import pandas as pd

from webpush import send_user_notification

import asyncio
import json
import configparser
import re
import os
from difflib import SequenceMatcher
import requests

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

@login_required
def experience_base(request):
    return render(
        request,
        'experience_base.html',
    )

@login_required
def statistic_base(request):
    return render(
        request,
        'statistic_base.html',
    )

class LogMessagesListView(generic.ListView):
    model = QuestionAnswerLog
    template_name = 'log_messages.html'
    context_object_name = 'data_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        # В первую очередь получаем базовую реализацию контекста
        context = super(LogMessagesListView, self).get_context_data(**kwargs)
        context['data_filter'] = LogMessagesFilter(self.request.GET, queryset = self.get_queryset())
        context['user_categories'] = [item.category.id for item in UserForPost.objects.filter(user=self.request.user)]
        context['finaly']=len(self.get_queryset().filter(Q(it_finaly=True) & ~Q(id_message=0)))
        context['test']=len(self.get_queryset().filter(it_test=True))
        context['actual']=len(self.get_queryset().filter(id_message=0))
        context['inner']=len(self.get_queryset().filter(it_interim=True))
        context['not_answer']=len(self.get_queryset().filter(Q(answer_text=None) & Q(datetime=None)))
        context['spam']=len(self.get_queryset().filter(Q(answer_text=None) & ~Q(datetime=None)))
        if context['data_filter'].data.get('category') and context['data_filter'].data['category'] != '':
            context['question_not_answer'] = QuestionAnswerLog.objects.filter(Q(category_id=int(context['data_filter'].data['category'])) & Q(answer_text=None) & Q(datetime=None) & Q(it_test=False))
        else:
            context['question_not_answer'] = None

        return context

    def get_queryset(self):
        queryset = super().get_queryset().filter(~Q(id_message=0) & Q(it_test=False)  & Q(it_last_message_in_dialog=True))
        return LogMessagesFilter(self.request.GET, queryset=queryset).qs

    def post(self, request, *args, **kwargs):
        question_answer = QuestionAnswerLog.objects.get(id=kwargs['pk'])
        
        if request.POST.get('answer_new_hand'):
            question_answer.answer_text = request.POST.get('answer_new_hand')
            if question_answer.datetime == None:
                question_answer.datetime = timezone.now()

            if request.POST['action'] == 'it_edit_answer' and \
                not question_answer.id_message_answer is None:
                if question_answer.it_test:
                    chat_id_send = test_chat_id
                else:
                    chat_id_send = chat_id
                asyncio.run(edit_message(chat_id_send, question_answer.id_message_answer, question_answer.answer_text))

        # Если ответ выбран то отметим этот вопрос как спам и запишем его как ответ и поставим дату
        if request.POST.get('answer_new') and request.POST['answer_new'] != '':
            answer_new = QuestionAnswerLog.objects.get(id=int(request.POST['answer_new']))
            answer_new.datetime = timezone.now()
            try:
                answer_new.save()
                question_answer.datetime = timezone.now()
                question_answer.answer_text = answer_new.question

                # Если есть предыдущее сообщение, делаем его не последним
                if question_answer.reply_to_message_id != None:
                    last_question = QuestionAnswerLog.objects.get(id_message=question_answer.reply_to_message_id)
                    last_question.it_last_message_in_dialog = False
                    last_question.it_finaly = False
                    last_question.it_interim = True
                    last_question.save()
            except:
                return HttpResponseRedirect(request.POST['url_filters'])

        if request.POST['action'] == 'it_finaly':
            question_answer.it_finaly = True
            question_answer.it_interim = False
        elif request.POST['action'] == 'it_interim':
            question_answer.it_finaly = False
            question_answer.it_interim = True
        elif request.POST['action'] == 'it_spam':
            question_answer.datetime = timezone.now()
            question_answer.answer_text = None
        elif request.POST['action'] == 'it_question':
            question_answer.datetime = None
        try:
            question_answer.save()
        except:
            pass

        return HttpResponseRedirect(request.POST['url_filters'])    

class StatisticListView(generic.ListView):
    model = QuestionAnswer
    template_name = 'statistic_base.html'

    def get_queryset(self):
        
        # Сформируем общий фильтр для специалистов
        q_specialist = Q(it_test=False)
        q_specialist.add(~Q(id_message=0), Q.AND)
        q_specialist.add(Q(it_last_message_in_dialog=True), Q.AND)
        q_specialist.add(~Q(specialist=None), Q.AND)
        q_specialist.add(~Q(answer_text=None), Q.AND)

        data_specialist_all = QuestionAnswerLog.objects.filter(q_specialist).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question'), sum_like=Sum('like'), sum_dislike=Sum('dislike')).order_by('specialist__last_name')

        q_specialist_1 = Q(q_specialist)
        q_specialist_1.add(Q(score_answer=1), Q.AND)
        data_specialist_1 = QuestionAnswerLog.objects.filter(q_specialist_1).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question')).order_by('specialist__last_name')

        q_specialist_2 = Q(q_specialist)
        q_specialist_2.add(Q(score_answer=2), Q.AND)
        data_specialist_2 = QuestionAnswerLog.objects.filter(q_specialist_2).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question')).order_by('specialist__last_name')

        q_specialist_3 = Q(q_specialist)
        q_specialist_3.add(Q(score_answer=3), Q.AND)
        data_specialist_3 = QuestionAnswerLog.objects.filter(q_specialist_3).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question')).order_by('specialist__last_name')

        # Добавим условие для финальных ответов
        q_specialist_finaly = Q(q_specialist)
        q_specialist_finaly.add(Q(it_finaly=True), Q.AND)

        data_specialist = QuestionAnswerLog.objects.filter(q_specialist_finaly).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question')).order_by('specialist__last_name')

         # Добавим условие для промежуточных ответов
        q_specialist = Q(it_test=False)
        q_specialist.add(~Q(id_message=0), Q.AND)
        q_specialist.add(Q(it_interim=True), Q.AND)
        q_specialist.add(Q(it_last_message_in_dialog=True), Q.AND)
        q_specialist.add(~Q(specialist=None), Q.AND)
        q_specialist.add(~Q(answer_text=None), Q.AND)

        data_specialist_answer = QuestionAnswerLog.objects.filter(q_specialist).values('specialist__last_name', 'specialist__first_name', 'specialist').annotate(count_questions=Count('question')).order_by('specialist__last_name')
        
        dict_arg_spec = {'count_questions': data_specialist_all.aggregate(Sum('count_questions'))['count_questions__sum'],
                         'sum_like': data_specialist_all.aggregate(Sum('sum_like'))['sum_like__sum'],
                         'sum_dislike': data_specialist_all.aggregate(Sum('sum_dislike'))['sum_dislike__sum'],
                         'count_questions_finaly': 0,
                         'count_questions_answer_no_last': 0,
                         'count_score_1': 0,
                         'count_score_2': 0,
                         'count_score_3': 0}

        data_specialist_list = []
        for i in data_specialist_all:
            try:
                count_questions_finaly = data_specialist.get(specialist=i['specialist'])['count_questions']
            except:
                count_questions_finaly = 0            
            i['count_questions_finaly'] = count_questions_finaly
            dict_arg_spec['count_questions_finaly'] += count_questions_finaly

            try:
                count_score_1 = data_specialist_1.get(specialist=i['specialist'])['count_questions']
            except:
                count_score_1 = 0            
            i['count_score_1'] = count_score_1
            dict_arg_spec['count_score_1'] += count_score_1

            try:
                count_score_2 = data_specialist_2.get(specialist=i['specialist'])['count_questions']
            except:
                count_score_2 = 0            
            i['count_score_2'] = count_score_2
            dict_arg_spec['count_score_2'] += count_score_2

            try:
                count_score_3 = data_specialist_3.get(specialist=i['specialist'])['count_questions']
            except:
                count_score_3 = 0            
            i['count_score_3'] = count_score_3
            dict_arg_spec['count_score_3'] += count_score_3

            try:
                count_questions_answer_no_last = data_specialist_answer.get(specialist=i['specialist'])['count_questions']
            except:
                count_questions_answer_no_last = 0            
            i['count_questions_answer_no_last'] = count_questions_answer_no_last
            dict_arg_spec['count_questions_answer_no_last'] += count_questions_answer_no_last

            data_specialist_list.append(i)

        # Сформируем общий фильтр для категорий
        q_category = Q(it_test=False) # Убираем тест из статистики
        q_category.add(~Q(id_message=0), Q.AND) # Убираем актуальные вопросы-ответы (они под 0 идексом)
        q_category.add(Q(retarget_category=None), Q.AND) # Убираем перенаправления
        q_category.add(~(~Q(datetime=None) & Q(answer_text=None)), Q.AND)# | (Q(datetime=None) & Q(answer_text=None)) | (~Q(answer_text=None)), Q.AND) # Убираем спам. Это пустой ответ и не пустая дата ответа
        q_category_new = Q(q_category)
        q_category_new.add(Q(it_last_message_in_dialog=True), Q.AND)

        data_category_all = QuestionAnswerLog.objects.filter(q_category_new).values('category__name', 'category').annotate(count_questions=Count('question'), sum_like=Sum('like'), sum_dislike=Sum('dislike')).order_by('category__id_post')

        # Добавим условие для всех ответов
        q_category_answer = Q(q_category)
        q_category_answer.add(Q(it_last_message_in_dialog=True), Q.AND)
        q_category_answer.add(~Q(answer_text=None), Q.AND)

        data_category_answer = QuestionAnswerLog.objects.filter(q_category_answer).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

        # Добавим условие для финальных ответов
        q_category_finaly = Q(q_category)
        q_category_finaly.add(Q(it_finaly=True), Q.AND)

        data_category = QuestionAnswerLog.objects.filter(q_category_finaly).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

        # Добавим условие для просроченных вопросов
        q_category_delay = Q(q_category)
        q_category_delay.add(Q(answer_text=None), Q.AND)
        q_category_delay.add(Q(datetime_question__lte=(timezone.now() - datetime.timedelta(days=2))), Q.AND)

        data_category_data = QuestionAnswerLog.objects.filter(q_category_delay).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

        q_category_1 = Q(q_category)
        q_category_1.add(Q(score_answer=1), Q.AND)
        data_q_category_1 = QuestionAnswerLog.objects.filter(q_category_1).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

        q_category_2 = Q(q_category)
        q_category_2.add(Q(score_answer=2), Q.AND)
        data_q_category_2 = QuestionAnswerLog.objects.filter(q_category_2).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

        q_category_3 = Q(q_category)
        q_category_3.add(Q(score_answer=3), Q.AND)
        data_q_category_3 = QuestionAnswerLog.objects.filter(q_category_3).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')
        
        q_category = Q(it_test=False) # Убираем тест из статистики
        q_category.add(~Q(id_message=0), Q.AND) # Убираем актуальные вопросы-ответы (они под 0 идексом)
        q_category.add(Q(it_last_message_in_dialog=True), Q.AND)
        q_category.add(Q(it_interim=True), Q.AND)
        
        data_category_q_answer = QuestionAnswerLog.objects.filter(q_category).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')

         # Добавим несогласованную переадресацию
        q_category_retarget = Q(it_test=False) # Убираем тест из статистики
        q_category_retarget.add(~Q(id_message=0), Q.AND) # Убираем актуальные вопросы-ответы (они под 0 идексом)
        q_category_retarget.add(~Q(retarget_category=None), Q.AND) # Добавляем перенаправления
        q_category_retarget.add(Q(it_agreed=True), Q.AND)# Только с флагом несогласовано
        q_category_retarget.add(Q(it_last_message_in_dialog=True), Q.AND)

        data_category_retarget = QuestionAnswerLog.objects.filter(q_category_retarget).values('category__name', 'category').annotate(count_questions=Count('question')).order_by('category__id_post')


        dict_arg = {'count_questions': data_category_all.aggregate(Sum('count_questions'))['count_questions__sum'],
                    'sum_like': data_category_all.aggregate(Sum('sum_like'))['sum_like__sum'],
                    'sum_dislike': data_category_all.aggregate(Sum('sum_dislike'))['sum_dislike__sum'],
                    'count_questions_finaly': 0,
                    'count_questions_data': 0,
                    'count_questions_answer': 0,
                    'count_questions_answer_no_last': 0,
                    'count_questions_not_answer': 0,
                    'count_questions_retarget': 0,
                    'count_score_1': 0,
                    'count_score_2': 0,
                    'count_score_3': 0}

        data_category_list = []
    
        for i in data_category_all:
            try:
                count_questions_finaly = data_category.get(category=i['category'])['count_questions']
            except:
                count_questions_finaly = 0            
            i['count_questions_finaly'] = count_questions_finaly
            dict_arg['count_questions_finaly'] += count_questions_finaly

            try:
                count_questions_data = data_category_data.get(category=i['category'])['count_questions']
            except:
                count_questions_data = 0            
            i['count_questions_data'] = count_questions_data
            dict_arg['count_questions_data'] += count_questions_data

            try:
                count_questions_answer = data_category_answer.get(category=i['category'])['count_questions']
            except:
                count_questions_answer = 0            
            i['count_questions_answer'] = count_questions_answer
            dict_arg['count_questions_answer'] += count_questions_answer
            
            try:
                count_questions_answer_no_last = data_category_q_answer.get(category=i['category'])['count_questions']
            except:
                count_questions_answer_no_last = 0            
            i['count_questions_answer_no_last'] = count_questions_answer_no_last
            dict_arg['count_questions_answer_no_last'] += count_questions_answer_no_last

            try:
                count_questions_not_answer = i['count_questions'] - i['count_questions_answer']
            except:
                count_questions_not_answer = 0            
            i['count_questions_not_answer'] = count_questions_not_answer

            try:
                count_score_1 = data_q_category_1.get(category=i['category'])['count_questions']
            except:
                count_score_1 = 0            
            i['count_score_1'] = count_score_1
            dict_arg['count_score_1'] += count_score_1

            try:
                count_score_2 = data_q_category_2.get(category=i['category'])['count_questions']
            except:
                count_score_2 = 0            
            i['count_score_2'] = count_score_2
            dict_arg['count_score_2'] += count_score_2

            try:
                count_score_3 = data_q_category_3.get(category=i['category'])['count_questions']
            except:
                count_score_3 = 0            
            i['count_score_3'] = count_score_3
            dict_arg['count_score_3'] += count_score_3

            try:
                count_questions_retarget = data_category_retarget.get(category=i['category'])['count_questions']
            except:
                count_questions_retarget = 0            
            i['count_questions_retarget'] = count_questions_retarget
            dict_arg['count_questions_retarget'] += count_questions_retarget

            data_category_list.append(i)

        # Количество новых пользователей
        last_rows = СhatMembersCount.objects.all().order_by('-id')[:2]
        count_members = last_rows[0].count - last_rows[1].count
        if count_members < 0:
            count_members_str = str(count_members)
        else:
            count_members_str = f'+{count_members}'

        try:
            count_questions_not_answer = dict_arg['count_questions'] - dict_arg['count_questions_answer']
        except:
            count_questions_not_answer = 0            
        dict_arg['count_questions_not_answer'] = count_questions_not_answer

        dict_arg['percent_questions_finaly'] = round(100/dict_arg['count_questions']*dict_arg['count_questions_finaly'], 2)

        return {'data_specialist': sorted(data_specialist_list, key=lambda d: d['count_questions'] , reverse=True),
                'data_category': data_category_list,
                'count_members': count_members_str,
                'all_members': last_rows[0].count,
                'date_update': last_rows[0].datetime_of_the_cut,
                'dict_agr': dict_arg,
                'dict_arg_spec': dict_arg_spec}

class StatisticDetailtView(generic.ListView):
    model = QuestionAnswer
    template_name = 'statistic_detail.html'

    def get_queryset(self):
        
        q_where = Q(it_test=False)
        q_where.add(~Q(id_message=0), Q.AND)

        id_category = self.request.GET.get('category')
        param = self.request.GET.get('param')

        if id_category != None:
            q_where.add(Q(category=Category.objects.get(id=int(id_category))), Q.AND)

        if param == '0':
            q_where.add(~Q(like=0), Q.AND)
        elif param == '1':
            q_where.add(~Q(dislike=0), Q.AND)

        data = QuestionAnswerLog.objects.filter(q_where)

        if param == '0':
            data = data.order_by('-like')
        elif param == '1':
            data = data.order_by('-dislike')

        return {'data': data} 

@api_view(['POST'])
def smart_response(request):

    if request.method == 'POST':
        smart_response = get_smart_response(request.data['message'], 
                                            request.data['id_message'], 
                                            request.data['id_category'], 
                                            request.data['id_chat'],
                                            request.data.get('reply_to_message_id'),
                                            request.data.get('id_question_author'))
        return Response({'answer': ''})
    
@api_view(['POST'])
def delete_response(request):

    if request.method == 'POST':

        l1 = []
        if type(request.data['list_messages']) == list:
            for i in request.data['list_messages']:
                l1.append(int(i))
        else:
            l1.append(int(request.data['list_messages']))
        
        it_test = int(request.data['chat_id']) == test_chat_id
        find_messages = QuestionAnswerLog.objects.filter(id_message__in=l1, answer_text=None, it_test=it_test)
        if find_messages.count():
            try:
                find_messages.delete()
                return Response({'text': 'Все удалил!'})
            except:
                return Response({'text': 'Какая то ошибочка. Не смог удалить!'})

    return Response({'text': 'Не нашел сообщений. Ни чего не удалил!'})

@api_view(['POST'])
def send_moder_response(request):

    if request.method == 'POST':
        username = request.data.get('username')
        reply_to_message_id = request.data.get('reply_to_message_id')
        it_test = request.data.get('it_test')
        text = request.data.get('text')
        id_message = request.data.get('id_message')
    
        if QuestionAnswerLog.objects.filter(Q(id_message_answer=id_message) & Q(it_test=it_test)).count():
            return Response({'succes': True})

        # Ищем модератора, если не нашли возвращаем ложь
        user_moder_find = User.objects.filter(first_name=username)

        if user_moder_find.count():
            user_moder = user_moder_find[0]
        else:
            return Response({'succes': False, 'answer': 'Модератор не найден в базе'})

        # Ищем только вопросы от пользователей, если не нашли возвращаем ложь
        question_find = QuestionAnswerLog.objects.filter(Q(it_test=it_test) & Q(id_message=reply_to_message_id))

        it_spam = identify_type_message(text, 0)
        it_inner = identify_type_message(text, 1)
        it_finaly = not it_inner

        if text != None and text.lower() == 'вопрос не по теме канала енс':
            it_spam = True

        if question_find.count():
            question = question_find[0]
            question.datetime = timezone.now()
            question.specialist = user_moder
            question.retarget_category = None
            question.it_agreed = False
            question.comment_retarget_category = None
            question.it_last_message_in_dialog = True
            
            if not it_spam:
                question.answer_text = text              
                question.it_finaly = it_finaly
                question.it_interim = it_inner
                question.id_message_answer = id_message
            try:
                question.save()
            except:
                pass

            if it_spam:
                return Response({'succes': True})    

            question_reply_find = QuestionAnswerLog.objects.filter(Q(it_test=it_test) & Q(id_message=question.reply_to_message_id))
            if question_reply_find.count():
                question_reply = question_reply_find[0]
                question_reply.it_finaly = False
                question_reply.it_interim = True
                question_reply.it_last_message_in_dialog = False
                try:
                    question_reply.save()
                except:
                    pass

            if question.id_question_autor != None:
                try:
                    if question.it_test:
                        link_category = str(test_chat_id)
                        link_post = str(question.category.id_post_test)
                    else:
                        link_category = str(chat_id)
                        link_post = str(question.category.id_post)
                    link_category = link_category.replace('-100', '')
                    link_message = f'https://t.me/c/{link_category}/{question.id_message_answer}?thread={link_post}'
                    text_message_score = f"""
Пожалуйста, оцените качество ответа специалиста.
{link_message}
Отправьте цифрой оценку, где:
1 - Полностью удовлетворен 😊
2 - Частично удовлетворен 😐
3 - Не удовлетворен ☹️
4 - Был дан промежуточный ответ"""
                    # if not settings.DEBUG:
                    asyncio.run(send_message(id_user=question.id_question_autor, text_message=text_message_score))
                except:
                    pass

            return Response({'succes': True})
        else:
            return Response({'succes': True, 'answer': 'Сообщение не найдено в базе'})

    return Response({'succes': False})

def get_smart_response(text, 
                       id_message, 
                       id_post, 
                       id_chat, 
                       reply_to_message_id, 
                       id_question_author):
    
    answer_text = ''
    response_find = False
    
    # Определим из какого чата сообщение и из какой категории
    try:
        if int(id_chat) == chat_id:
            category = Category.objects.get(id_post=id_post)
            it_test = False
        else:
            category = Category.objects.get(id_post_test=id_post)
            it_test = True
    except Category.DoesNotExist:
        return {'response_find': False, 'answer': ''}
    
    
    if QuestionAnswerLog.objects.filter(Q(id_message=id_message) & Q(it_test=it_test)).count():
        return {'response_find': response_find, 'answer': answer_text}

    create_log_message(text, 
                        id_message, 
                        it_test=it_test, 
                        category=category, 
                        reply_to_message_id=reply_to_message_id,
                        id_question_author=id_question_author)

    return {'response_find': response_find, 'answer': answer_text}

def create_log_message(question_text, 
                       id_message, 
                       answer=None, 
                       it_test=False, 
                       category=None, 
                       reply_to_message_id=None,
                       id_question_author=None): 

    # Ищем первое сообщение в цепочке, для объединения
    if reply_to_message_id != None:
        first_messages = QuestionAnswerLog.objects.filter(Q(id_message=reply_to_message_id) & Q(it_test=it_test))
        if len(first_messages) == 0:
            first_message = None
        else:
            first_message = first_messages[0]
            if not first_message.first_question is None:
                first_message = first_message.first_question
    else:
        first_message = None  

    # Проверим на наличие спама
    it_spam = identify_type_message(question_text, 0)

    datetime_question = timezone.now()
    if not it_spam:
        datetime_answer = None
    else:
        datetime_answer = timezone.now()

    new_log = QuestionAnswerLog.objects.create(question=question_text, 
                                            answer=answer,
                                            datetime=datetime_answer,
                                            datetime_question=datetime_question,
                                            id_message=id_message,
                                            category=category,
                                            it_test=it_test,
                                            reply_to_message_id=reply_to_message_id,
                                            id_question_autor=id_question_author,
                                            first_question=first_message)
    
    if not it_test:
        new_log.encode = encode_question(question_text, new_log.id, category.id)
        new_log.save()

    users_for_post = UserForPost.objects.filter(category=category)

    for user_for_post in users_for_post:
        payload = {"head": "Новое сообщение", "body": question_text}
        send_user_notification(user=user_for_post.user, payload=payload, ttl=1000)

def identify_type_message(text_message, type_message):

    stop_phrases = StopPhrase.objects.filter(type_message=type_message)

    for stop_phrase in stop_phrases:
        if similarity(stop_phrase.phrase, str(text_message).lower()) >= 0.9:
            return True

    return False

def similarity(a,b):
    seq = SequenceMatcher(a=a, b=b)
    return seq.ratio()

class ARMSpecialist(generic.ListView):

    model = QuestionAnswerLog
    template_name = 'index.html'
    context_object_name = 'data_list'
    paginate_by = 3  

    def get_context_data(self, **kwargs):
        context = super(ARMSpecialist, self).get_context_data(**kwargs)
        context['data_category'] = Category.objects.all().order_by('name').values_list('id', 'name')
        context['data_filter'] = CategoryFilter(self.request.GET, queryset = self.get_queryset())

        user_categories = [item.category for item in UserForPost.objects.filter(user=self.request.user)]

        list_of_hints = get_list_of_hints_ml(list(context['data_list'].values_list('id', flat=True)))
        list_retarget_category = get_list_retarget_category_ml(list(context['data_list'].values('id', 'category_id')))

        for row in context['data_list']:

            # 
            row.it_current_category = row.retarget_category in user_categories                 

            # Добавим к каждому сообщению список предыдущих сообщений        
            row.message_reply = get_list_message_reply(row.reply_to_message_id)

            # Добавим подсказки, если найдены для каждого сообщений
            row.list_of_hints = list_of_hints.get(str(row.id), [])
            
            # Добавим подсказки переадресаций, если найдены для каждого сообщения
            row.list_retarget_category = list_retarget_category.get(str(row.id), [])

            # Добавим к каждому сообщению список подсказок для ответов из базы
            # row.list_of_hints = get_list_of_hints(row.question, row.category, row.it_test)

            # Если не нашли ни чего в этой категории, пробуем поиск в других, для переадресации
            # row.list_retarget_category = None
            # if row.list_of_hints is None:
            #     list_retarget_category = []
            #     for category in Category.objects.filter(~Q(id=row.category.id)):
            #         if get_list_of_hints(row.question, category, row.it_test, True):
            #             list_retarget_category.append(category)
            #     if len(list_retarget_category) != 0:
            #         row.list_retarget_category = list_retarget_category

        return context

    def get_queryset(self):

        user_categories = [item.category for item in UserForPost.objects.filter(user=self.request.user)]

        queryset = super().get_queryset().filter(it_test=False)
        queryset = CategoryFilter(self.request.GET, queryset=queryset).qs
        if len(user_categories) == 0:
            return queryset.filter(category=None, datetime=None,).order_by('-datetime_question')   
        else:
            queryset = queryset.filter((Q(category__in=user_categories) | Q(retarget_category__in=user_categories)) & Q(datetime=None)).order_by('-datetime_question')
            return  queryset 

    def post(self, request, *args, **kwargs):
        question_answer = QuestionAnswerLog.objects.get(id=kwargs['pk'])

        save_model = False
        action = request.POST['action']

        if action == 'it_answer_inner':
            action = 'it_answer'
            it_inner = True
            it_finaly = False
        elif action == 'it_answer':
            it_inner = False
            it_finaly = True

        # Если дата пустая и не кто ещё не ответил на это сообщение, то отвечаем
        if question_answer.datetime == None:
            # Если модератор не согласовал изменение категории
            # то ставим обратно старую категорию
            # и сбрасываем флаг согласования
            if action == 'it_retarget_category_refusal':
                question_answer.category = question_answer.retarget_category 
                question_answer.comment_retarget_category = request.POST['answer']
                question_answer.retarget_category = None
                question_answer.it_agreed = False
            # Если отправка на согласование
            # то ставим новую категорию
            # и ставим флаг согласования
            elif action=='it_retarget_category_agreed':
                question_answer.retarget_category = question_answer.category
                question_answer.category = Category.objects.get(id=int(request.POST['category_new']))
                question_answer.comment_retarget_category = request.POST['answer']
                question_answer.it_agreed = True
            # Если подтверждение согласования
            # то скидываем флаг
            elif action=='it_retarget_category':
                question_answer.it_agreed = False
                question_answer.datetime = timezone.now()
            # Если это обычный ответ
            # то зачищаем старую категрию и все пишем
            else:
                question_answer.specialist = request.user
                if action != 'it_spam':
                    question_answer.answer_text = request.POST['answer']
                question_answer.datetime = timezone.now()
                question_answer.retarget_category = None
                question_answer.it_agreed = False
                question_answer.comment_retarget_category = None
                     
                if action == 'it_answer':
                    question_answer.it_interim = it_inner
                    question_answer.it_finaly = it_finaly

            save_model = True

        if question_answer.it_test:
            chat_id_send = test_chat_id
        else:
            chat_id_send = chat_id

        # Если это ответ, спам или смена категории, сохраняем вопрос
        if save_model:


   
            # Если финальный ответ, то пишем его в базу знаний
            # Если нет, то просто сохраняем ответ в логе
            if question_answer.it_finaly == True:
                try:
                    with transaction.atomic():
                        # if not settings.DEBUG:
                        id_message_answer = asyncio.run(send_message(id_user=chat_id_send, id_message=question_answer.id_message, text_message=question_answer.answer_text))
                        # else:
                        # id_message_answer = QuestionAnswerLog.objects.all().count()
                        question_answer.id_message_answer = id_message_answer
                        question_answer.save()
                except:
                    return HttpResponseRedirect(request.POST['url_filters'])
                try:
                    if question_answer.it_test:
                        link_category = str(test_chat_id)
                        link_post = str(question_answer.category.id_post_test)
                    else:
                        link_category = str(chat_id)
                        link_post = str(question_answer.category.id_post)
                    link_category = link_category.replace('-100', '')
                    link_message = f'https://t.me/c/{link_category}/{question_answer.id_message_answer}?thread={link_post}'
                    text_message_score = f"""
Пожалуйста, оцените качество ответа специалиста.
{link_message}
Отправьте цифрой оценку, где:
1 - Полностью удовлетворен 😊
2 - Частично удовлетворен 😐
3 - Не удовлетворен ☹️
4 - Был дан промежуточный ответ"""
                    # if not settings.DEBUG:
                    asyncio.run(send_message(id_user=question_answer.id_question_autor, text_message=text_message_score))
                except:
                    return HttpResponseRedirect(request.POST['url_filters'])     
            else:
                try:
                    with transaction.atomic():
                        question_answer.save()
                        # Если согласовали изменение, то пишем в ТГ
                        if action == 'it_retarget_category':
                            text_message = f'Здравствуйте! Переадресуйте пожалуйста Ваш вопрос в категорию: {question_answer.category.name}'
                        elif action == 'it_answer':
                            text_message = question_answer.answer_text
                        else:
                            text_message = None
                        if text_message != None: #and not settings.DEBUG:
                            asyncio.run(send_message(id_user=chat_id_send, id_message=question_answer.id_message, text_message=text_message))

                        text_message_spec = None
                        if action=='it_retarget_category_agreed':
                            text_message_spec = 'Появилась заявка на изменение категории'
                        elif action=='it_retarget_category_refusal':
                            text_message_spec = 'Отказ в изменении категории'

                        if not text_message_spec == None:
                            users_for_post = UserForPost.objects.filter(category=question_answer.category)

                            for user_for_post in users_for_post:
                                payload = {"head": "Новое сообщение", "body": text_message_spec}
                                send_user_notification(user=user_for_post.user, payload=payload, ttl=1000)
                except:
                    return HttpResponseRedirect(request.POST['url_filters'])
                
            # Найдем предыдущее сообщение и снимем флаг "Это последний"
            try:
                if question_answer.reply_to_message_id != None:
                    last_question = QuestionAnswerLog.objects.get(id_message=question_answer.reply_to_message_id)
                    last_question.it_last_message_in_dialog = False
                    last_question.it_finaly = False
                    last_question.it_interim = True
                    last_question.save()
            except:
                pass

        return HttpResponseRedirect(request.POST['url_filters'])

@api_view(['GET'])
def update_like_and_dislike_posts(request):
    
    #Получим реакции с тестового канала
    list_id_messages = QuestionAnswerLog.objects.filter(Q(it_test=False) & ~Q(id_message_answer=None)).values_list('id_message_answer', flat=True)
    
    if len(list_id_messages) != 0:
        list_id_messages = asyncio.run(get_like_and_dislike(test_chat_id, list_id_messages))
        
        for message in list_id_messages:
            message_object = QuestionAnswerLog.objects.get(id_message_answer=message['id_message_answer'])
            message_object.like = message['like']
            message_object.dislike = message['dislike']
            message_object.save()

        return Response(f'Обновлено сообщений: {len(list_id_messages)}')
    
@api_view(['GET'])
def update_posts(request):
    
    return Response(f'Загружено категорий: {load_question_answer()}')

@api_view(['POST'])
def update_score_answer(request):

    try:
        score = int(request.data['score'])

        question_answer = QuestionAnswerLog.objects.get(Q(id_message_answer=request.data['id_message']) & Q(it_test=request.data['it_test']))
        if score == 4:
            question_answer.it_interim = True
            question_answer.it_finaly = False
        elif question_answer.score_answer == 0 or question_answer.score_answer == None:
            question_answer.score_answer = score
        question_answer.save()
    except:
        pass

    return Response('OK')

def get_list_message_reply(reply_to_message_id):

    list_message_reply = []
    while reply_to_message_id != None:
        question_log = QuestionAnswerLog.objects.filter(id_message=reply_to_message_id)
        if len(question_log) != 0:
            reply_to_message_id = question_log[0].reply_to_message_id
            list_message_reply.append(question_log[0])
        else:
            reply_to_message_id = None

    return list_message_reply

def get_list_of_hints(text_message, category, it_test, find_category=False):
    
    list_of_tags = [row['name'] for row in TagsForFind.objects.filter(category=category).values('name')]

    # Если не заполнены теги, то возвращаем пустой список подсказок
    if len(list_of_tags) == 0:
        return None
    
    # Если теги заполенны, ищем их в тексте сообщения

    # Очистим строку от всего кроме букв
    reg = re.compile('[^а-яА-Яa-zA-Z ]')
    text_cleared = reg.sub('', text_message)

    # Сформируем список вхождений тегов в строке
    list_of_find_tags = []

    for tag in reg.sub('', text_cleared).lower().split(' '):
        if tag in list_of_tags:
            list_of_find_tags.append(tag)

    # Если не нашли теги в сообщении, возвращаем пустой список
    if len(list_of_find_tags) == 0:
        return None

    # Найдем полное соответствие тегов в текущей категории
    # Собериаем условие
    q_where = Q(category=category)
    # Если это тест, то выводим все подсказки
    if not it_test:
        q_where.add(Q(it_test=False), Q.AND)
    q_where.add(Q(it_finaly=True), Q.AND)
    for i in list_of_find_tags:
        q_where.add((Q(first_question=None) & Q(question__iregex=i)) | (~Q(first_question=None) & Q(first_question__question__iregex=i)), Q.AND)
    messages_find = QuestionAnswerLog.objects.filter(q_where).values('answer_text').annotate(count_questions=Count('question'), max_datetime_answer=Max('datetime')).order_by('-count_questions')

    # Если нашли хоть что то в текущей категории, возвращаем эти сообщения
    # Или возвращаем категорию, если это подсказки для переадресаци
    if messages_find.count() > 0:
        if not find_category:
            for row in messages_find[:10]:
                messages_find_date = QuestionAnswerLog.objects.filter(Q(answer_text=row['answer_text']) & Q(datetime=row['max_datetime_answer']))
                if messages_find_date.count():
                    question = messages_find_date[0].question
                else:
                    question = ''
                row['question'] = question
            return messages_find[:10]
        else:
            return True
    else:
        if not find_category:
            return None
        else:
            return False
    
@api_view(['GET'])
def update_question_answer(request):
    
    count, count_false, count_update = load_question_answer()
    return Response(f'Загружено вопрос-ответов: {count}. Не загружено вопрос-ответов: {count_false}. Обновлено вопрос-ответов: {count_update}.')

@api_view(['GET'])
def update_tags(request):
    
    return Response(f'Загружено вопрос-ответов: {load_tags()}')

@api_view(['GET'])
def update_chat_members_count(request):
    
    count = asyncio.run(get_chat_members_count())
        
    СhatMembersCount.objects.create(datetime_of_the_cut=timezone.now(), count=count)
    
    return Response(f'Количество участиков канала по состоянию на {timezone.now()}: {count}')

@api_view(['GET'])
def update_id_messages(request):
    
    list_q_a = QuestionAnswerLog.objects.filter(id_message=1).values_list('question', 'answer_text', 'id')

    list_q_a_search = []
    for i in list_q_a:
        list_q_a_search.append({'question': i[0], 'answer_text': i[1], 'id': i[2]})

    new_list_q_a_search = asyncio.run(search_message(list_q_a_search))
        
    for i in new_list_q_a_search:
        q_a = QuestionAnswerLog.objects.get(id=i['id'])
        q_a.id_message = i['id_message']
        q_a.reply_to_message_id = i.get('reply_to_message_id')
        q_a.id_message_answer = i.get('id_message_answer')
        q_a.save()
    
    return Response(f'Обновлено {len(new_list_q_a_search)} сообщений из {len(list_q_a_search)}')

@api_view(['GET'])
def update_messages_it_last_message_in_dialog(request):

    count1 = 0 

    questions = QuestionAnswerLog.objects.filter((~Q(id_message=0) & Q(first_question=None) & ~Q(reply_to_message_id=None)))

    for question in questions:
        reply_to_message = QuestionAnswerLog.objects.filter(Q(id_message=question.reply_to_message_id) & Q(it_test=question.it_test))

        error = False
        if len(reply_to_message) == 0:
            error = True
            continue

        if reply_to_message[0].reply_to_message_id == None:
            question.first_question = reply_to_message[0]
            question.save()
            count1 += 1
            continue

        while reply_to_message[0].reply_to_message_id != None:
            reply_to_message = QuestionAnswerLog.objects.filter(Q(id_message=reply_to_message[0].reply_to_message_id) & Q(it_test=reply_to_message[0].it_test))    

            error = False
            if len(reply_to_message) == 0:
                error = True
                break
        if error:
            continue

        question.first_question = reply_to_message[0]
        question.save()
        count1 += 1

    return Response(f'Обновлено {count1} записей.')

@api_view(['GET'])
def create_users_for_posts(request):
    
    count = create_users()
    return Response(f'Создано пользователей: {count}')

def edit_user(request, pk):

    try:
        user = User.objects.get(id=pk)
    except:
        return HttpResponseRedirect(reverse('index')) 

    if request.method == 'POST':
        try:
            # user = User.objects.get(id=pk)
            user.first_name = request.POST['username']
            user.last_name = request.POST['last_name']
            user.save()
        except:
            return HttpResponseRedirect(reverse('index')) 

        return HttpResponseRedirect(reverse('index')) 
    
    return render(request, 'user_profile.html', {
        'form': {'last_name': user.last_name, 'username': user.first_name, 'id': pk},
    })
        
@login_required
def download_statistic(request):
    
    #Созданим уникальны идентификатор для нашей таблицы и файла
    guid = 'data_statistic_' + uuid.uuid4().hex

    # Устанавливаем соединение с базой данных
    with connection.cursor() as cursor:

        # Начальный запрос, на создание временной таблицы и первой таблицы
        text_query = """
        DROP TABLE IF EXISTS temp.question_answer;

        CREATE TEMP TABLE question_answer AS

        SELECT 
        crm_category.name AS category,
        crm_questionanswerlog.category_id AS category_id,
        crm_questionanswerlog.id AS id,
        crm_questionanswerlog.id_message AS id_message,
        crm_questionanswerlog."like" AS "like",
        crm_questionanswerlog.dislike AS dislike,
        crm_questionanswerlog.question AS question,
        crm_questionanswerlog.answer_text AS answer_text,
        crm_questionanswerlog.it_last_message_in_dialog AS it_last_message_in_dialog,
        crm_questionanswerlog.it_finaly AS it_finaly,
        crm_questionanswerlog.it_interim AS it_interim,
        crm_questionanswerlog.score_answer AS score_answer,
        crm_questionanswerlog.datetime_question AS datetime_question,
        crm_questionanswerlog.datetime AS datetime,
        crm_questionanswerlog.first_question_id AS first_question_id,
        row_number() OVER (PARTITION BY crm_questionanswerlog.category_id) AS number

        FROM crm_questionanswerlog AS crm_questionanswerlog
        JOIN crm_category AS crm_category
        ON crm_category.id = crm_questionanswerlog.category_id

        WHERE
        crm_questionanswerlog.it_test = False
        AND NOT crm_questionanswerlog.id_message = 0
        AND crm_questionanswerlog.retarget_category_id IS NULL
        AND NOT (NOT crm_questionanswerlog.datetime IS NULL AND crm_questionanswerlog.answer_text IS NULL)
        AND crm_questionanswerlog.it_last_message_in_dialog=True

        ORDER BY crm_questionanswerlog.id_message;

        SELECT 
        category,
        count_question,
        count_answer,
        count_like,
        count_dislike,
        count_interim,
        count_not_answer,
        count_delay 

        FROM (

        SELECT 
        category AS category,
        COUNT(id) AS count_question,
        SUM(CASE WHEN answer_text IS NULL THEN 0 ELSE 1 END) AS count_answer,
        SUM("like") AS count_like,
        SUM(dislike) AS count_dislike,
        SUM(it_interim) AS count_interim,
        SUM(CASE WHEN answer_text IS NULL THEN 1 ELSE 0 END) AS count_not_answer,
        SUM(CASE WHEN answer_text IS NULL AND datetime_question <= date('now', '-2 day') THEN 1 ELSE 0 END) AS count_delay,
        category_id AS category_id
        FROM temp.question_answer
        WHERE it_last_message_in_dialog = True
        GROUP BY category

        UNION ALL
        SELECT 
        "Итог" AS category,
        COUNT(id) AS count_question,
        SUM(CASE WHEN answer_text IS NULL THEN 0 ELSE 1 END) AS count_answer,
        SUM("like") AS count_like,
        SUM(dislike) AS count_dislike,
        SUM(it_interim) AS count_interim,
        SUM(CASE WHEN answer_text IS NULL THEN 1 ELSE 0 END) AS count_not_answer,
        SUM(CASE WHEN answer_text IS NULL AND datetime_question <= date('now', '-2 day') THEN 1 ELSE 0 END) AS count_delay,
        -1 AS category_id
        FROM temp.question_answer
        WHERE it_last_message_in_dialog = True) AS union_table
        ORDER BY category_id DESC
        """.replace('question_answer', guid)

        #Разбиваем текст на пакеты и выполняем последовательно. Т.к. sqllite не выполняет цепочку за раз
        text_query_split = text_query.split(';')
        for query_row in text_query_split:
            cursor.execute(query_row)
            question_answer = cursor.fetchall()

        df_all = pd.DataFrame(question_answer, columns=['Темы', 'Количество вопросов', 'Количество ответов', 'Количество лайков', 'Количество дизлайков', 'Промежуточные ответы', 'Не даны ответы', 'Просрочка более 2-х дней'])

        #Запрос для категорий
        text_query = """
        SELECT DISTINCT 
        number,
        category_id,
        id_message,
        question,
        datetime_question,
        answer_text,
        datetime,
        like,
        dislike

        FROM ( 

        SELECT 
        question_answer.number AS number,
        question_answer.category_id AS category_id,
        question_answer.id_message AS id_message,
        question_answer."like" AS "like",
        question_answer.dislike AS dislike,
        question_answer.question AS question,
        question_answer.answer_text AS answer_text,
        question_answer.datetime_question AS datetime_question,
        question_answer.datetime AS datetime

        FROM temp.question_answer AS question_answer

        UNION ALL

        SELECT 
        question_answer.number AS number,
        question_answer.category_id AS category_id,
        questionanswerlog.id_message AS id_message,
        questionanswerlog."like" AS "like",
        questionanswerlog.dislike AS dislike,
        questionanswerlog.question AS question,
        questionanswerlog.answer_text AS answer_text,
        questionanswerlog.datetime_question AS datetime_question,
        questionanswerlog.datetime AS datetime

        FROM temp.question_answer AS question_answer
        INNER JOIN crm_questionanswerlog AS questionanswerlog
        ON question_answer.first_question_id=questionanswerlog.id 
        AND NOT question_answer.id_message=questionanswerlog.id_message
        AND NOT questionanswerlog.answer_text IS NULL

        UNION ALL

        SELECT 
        question_answer.number AS number,
        question_answer.category_id AS category_id,
        questionanswerlog.id_message AS id_message,
        questionanswerlog."like" AS "like",
        questionanswerlog.dislike AS dislike,
        questionanswerlog.question AS question,
        questionanswerlog.answer_text AS answer_text,
        questionanswerlog.datetime_question AS datetime_question,
        questionanswerlog.datetime AS datetime

        FROM temp.question_answer AS question_answer
        INNER JOIN crm_questionanswerlog AS questionanswerlog
        ON question_answer.first_question_id=questionanswerlog.first_question_id 
        AND NOT question_answer.id_message=questionanswerlog.id_message
        AND NOT questionanswerlog.answer_text IS NULL) AS question_answer

        ORDER BY number, id_message""".replace('question_answer', guid)

        cursor.execute(text_query)
        question_answer_category = cursor.fetchall()

        #Колонки для листов категорий
        columns = """№ п/п
category_id
id_message
Вопрос
Дата и время поступления вопроса
Ответ
Дата и время публикации ответа
Количество лайков
Количество дизлайков""".split('\n')

        df_category = pd.DataFrame(question_answer_category, columns=columns)

        #Получим все категории, которые участвуют в вопрос-ответах
        text_query = """
        SELECT id, substr(name, 0, INSTR(name, '.')) as header FROM crm_category GROUP BY id ORDER BY id DESC"""
        cursor.execute(text_query)
        categoryes = cursor.fetchall()

        #Удалим временную таблицу
        text_query = """DROP TABLE IF EXISTS temp.question_answer""".replace('question_answer', guid)
        cursor.execute(text_query)

        #Создадим дирректорию для хранения файлов
        dir_name = 'statistic_files'
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        #Получим последнюю дату обновления количества пользователей
        text_query = """
        SELECT 
            datetime_of_the_cut,
            count,
            last_value(count) OVER () - first_value(count) OVER () as delta_users
        FROM crm_сhatmemberscount
        ORDER BY datetime_of_the_cut DESC LIMIT 1
        """
        cursor.execute(text_query)
        users_channel = cursor.fetchall()[0]
        count_users_channel = users_channel[1]
        delta_users_channel = users_channel[2]
        if delta_users_channel < 0:
            string_users_channel = 'от канала отписалось'
            delta_users_channel *= -1
        else:
            string_users_channel = 'на канал подписалось'

        row_total = df_all[df_all['Темы']=='Итог'].iloc[0]

        #Создадим excel
        filename = f'{dir_name}/{guid}.xlsx'
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df_all.to_excel(writer, sheet_name='Статистика', index=False, startrow=4)
            
            sheet_stats = writer.sheets['Статистика']
            sheet_stats.set_column(0, 0, 75)
            cell_format = writer.book.add_format({'text_wrap': True})
            sheet_stats.set_column(1, 7, 15, cell_format)

            sheet_stats.write(0, 0, 'Новостной канал для сотрудников ТНО в telegram-канале «ОКНО в ЕНС 3.0».')
            sheet_stats.write(1, 0, f'По состоянию на {datetime.datetime.now().strftime("%d.%m.%Y")} количество подписчиков составляет {count_users_channel} человек (с 15.05.2023 {string_users_channel} {delta_users_channel} пользователей).')
            sheet_stats.write(2, 0, f'На {datetime.datetime.now().strftime("%d.%m.%Y")} всего поступило {row_total["Количество вопросов"]} вопросов, из них на {row_total["Количество ответов"]} направлено ответов, получено {row_total["Количество лайков"]} лайков и {row_total["Количество дизлайков"]} дизлайков.')
            
            index_column = ['№ п/п', 'id_message']
            for category_row in categoryes:
                df_category[df_category['category_id']==category_row[0]].\
                set_index(index_column).\
                drop(columns=['category_id']).\
                to_excel(writer, sheet_name=category_row[1])
                writer.sheets[category_row[1]].set_column(2, 5, 37, cell_format)
                writer.sheets[category_row[1]].set_column(6, 7, 18)
                writer.sheets[category_row[1]].set_column(1, 1, 40, None, {'hidden': True})

        # Закрываем соединение
        connection.close()

    #Создадим ответ из файла
    response = FileResponse(open(filename, 'rb'))

    return response

class RequestToAddModeratorsListView(generic.ListView):
    model = RequestToAddModerators
    template_name = 'moders.html'
    context_object_name = 'data_list'
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = super().get_queryset().all().order_by('-datatime_request')
        else:
            queryset = super().get_queryset().filter(author=self.request.user).order_by('-datatime_request')
        return queryset
    
class RequestToAddModeratorsFormtView(generic.CreateView):
    model = RequestToAddModerators
    fields = ['name', 'login_tg', 'department', 'categories']
    template_name = 'add_moders.html'
    success_url = reverse_lazy('moders')
    
    def form_valid(self, form): 
        form.instance.author = self.request.user
        return super(RequestToAddModeratorsFormtView, self).form_valid(form)

class RequestToAddModeratorsCreate(generic.UpdateView):
    model = RequestToAddModerators
    form_class = CreateModersForm
    template_name = 'create_moders.html'
    success_url = reverse_lazy('moders')
    
    def form_valid(self, form):
        if not form.instance.it_rejection:
            form.instance.datatime_create_moder = timezone.now()
            password = generate_password()
            user = User.objects.create_user(username=form.instance.login_tg, 
                                    password=password, 
                                    last_name=f'{form.instance.department.name} - {form.instance.name}', 
                                    first_name=form.instance.login_tg)
            department = Department.objects.get(pk=form.instance.department.id)
            department.staff.add(user)
            department.save()

            for category in form.instance.categories.all():
                UserForPost.objects.create(user = user, category = category, it_moder = True)

            text_message = get_message_data_registr(form.instance.login_tg, password)
            asyncio.run(send_message(id_user=form.instance.login_tg, text_message=text_message))

        return super(RequestToAddModeratorsCreate, self).form_valid(form)

class RequestToDeleteModeratorsFormtView(generic.CreateView):
    model = RequestToAddModerators
    fields = ['user_edit_delete']
    template_name = 'delete_moders.html'
    success_url = reverse_lazy('moders')

    def get_form(self, form_class=None):
        form = super(RequestToDeleteModeratorsFormtView, self).get_form(form_class)
        form.fields['user_edit_delete'].required = True
        return form
    
    def form_valid(self, form): 
        form.instance.author = self.request.user
        form.instance.type_action_request = 2
        return super(RequestToDeleteModeratorsFormtView, self).form_valid(form)

class RequestToDeleteModeratorsAction(generic.UpdateView):
    model = RequestToAddModerators
    form_class = DeleteModersForm
    template_name = 'delete_action_moders.html'
    success_url = reverse_lazy('moders')
    
    def form_valid(self, form):
        if not form.instance.it_rejection:
            form.instance.datatime_create_moder = timezone.now()
            user_obj = User.objects.get(id=form.instance.user_edit_delete.id)
            user_obj.is_active = False
            user_obj.save()

            UserForPost.objects.filter(user=user_obj).delete()

        return super(RequestToDeleteModeratorsAction, self).form_valid(form)

@login_required
def request_to_edit_moderators(request):

    user_edit_delete = User.objects.filter(is_active=True)

    return render(request, 'edit_moders.html', {
        'form': {'user_edit_delete': user_edit_delete},
    })

@login_required
def request_to_edit_moderators_user(request, pk):

    user_edit_delete = User.objects.filter(is_active=True)
    target_user = User.objects.get(id=pk)
    departments = Department.objects.filter(staff=target_user)
    if departments.count() > 0:
        department = departments[0]
    else:
        department = None
    categories = list(UserForPost.objects.filter(user=target_user).values_list('category_id', flat=True))
    all_categories = Category.objects.all()

    return render(request, 'edit_moders.html', {
        'form': {'user_edit_delete': user_edit_delete,
                 'target_user': target_user,
                 'name': target_user.last_name,
                 'login_tg': target_user.first_name,
                 'department': department,
                 'departments': Department.objects.all(),
                 'categories': categories,
                 'all_categories': all_categories}
    })

class UpdateModeratorsForm(forms.Form):
    user_edit_delete = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    name = forms.CharField(max_length=100)
    login_tg = forms.CharField(max_length=100)
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all())

@login_required
def request_to_edit_moderators_update(request):
    if request.method == 'POST':
        form = UpdateModeratorsForm(request.POST)
        if form.is_valid():
            # Обработка данных формы и создание заявки
            request_moder = RequestToAddModerators.objects.create(
                user_edit_delete=form.cleaned_data['user_edit_delete'],
                department=form.cleaned_data['department'],
                name=form.cleaned_data['name'],
                login_tg=form.cleaned_data['login_tg'],
                author=request.user,
                type_action_request=1
            )
            for category in form.cleaned_data['categories']:
                request_moder.categories.add(category)
            request_moder.save()

            return HttpResponseRedirect(reverse('moders'))
        else:
            # Если форма невалидна, вернуть ее с ошибками
            return render(request, 'edit_moders.html', {'form': form})
    else:
        form = UpdateModeratorsForm()
    return render(request, 'edit_moders.html', {'form': form})


class RequestToEditModeratorsAction(generic.UpdateView):
    model = RequestToAddModerators
    form_class = EditModersFormAction
    template_name = 'edit_action_moders.html'
    success_url = reverse_lazy('moders')
    
    def form_valid(self, form):
        if not form.instance.it_rejection:
            form.instance.datatime_create_moder = timezone.now()
            user_obj = User.objects.get(id=form.instance.user_edit_delete.id)
            user_obj.last_name = form.instance.name
            user_obj.first_name = form.instance.login_tg
            user_obj.save()
            dep_objs = Department.objects.filter(staff=form.instance.user_edit_delete.id)
            if dep_objs.count():
                dep_obj = dep_objs[0]
                dep_obj.staff.remove(user_obj)
                dep_obj.save()
            department = Department.objects.get(pk=form.instance.department.id)
            department.staff.add(user_obj)
            department.save()

            UserForPost.objects.filter(user = user_obj).delete()

            for category in form.instance.categories.all():
                UserForPost.objects.create(user = user_obj, category = category, it_moder = True)

        return super(RequestToEditModeratorsAction, self).form_valid(form)

def generate_password():

    chars = 'abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
    length = 8
    password =''
    for i in range(length):
        password += random.choice(chars)
    
    return password

def get_message_data_registr(login, password):

    return f"""
Здравствуйте!
Вы зарегистрированы в CRM системе канала "ОКНО в ЕНС 3.0".
Адрес: http://ens.nocfns.ru
Логин: {login}
Пароль: {password}
"""

class RequestToAddModeratorsDelete(generic.DeleteView):
    model = RequestToAddModerators
    success_url = reverse_lazy("moders")  

class FeedbackFromUsersListView(generic.ListView):
    model = FeedbackFromUsers
    template_name = 'feedback.html'
    context_object_name = 'data_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['data_filter'] = FeedbackFilter(self.request.GET, queryset = self.get_queryset())

        return context
    
    def get_queryset(self):
        queryset = super().get_queryset().all().order_by('-like')
        return FeedbackFilter(self.request.GET, queryset=queryset).qs

class FeedbackFromUsersFormtView(generic.CreateView):
    model = FeedbackFromUsers
    form_class = FeedbackAddForm
    template_name = 'add_feedback.html'
    success_url = reverse_lazy('feedback')
    
    def form_valid(self, form): 
        form.instance.author = self.request.user
        return super(FeedbackFromUsersFormtView, self).form_valid(form)
    
class FeedbackFromUsersDelete(generic.DeleteView):
    model = FeedbackFromUsers
    success_url = reverse_lazy("feedback")  

class FeedbackFromUsersUpdate(generic.UpdateView):
    model = FeedbackFromUsers
    form_class = FeedbackUpdateForm
    template_name = 'update_feedback.html'
    success_url = reverse_lazy('feedback')

@login_required
def update_like_dislike_feedback(request, pk, score):

    try:
        with transaction.atomic():

            feedback_object = FeedbackFromUsers.objects.get(id=pk)
            score = int(score)

            try:
                feedback_like_dislike = FeedbackFromUsersLikeDislake.objects.get(feedback=pk, user=request.user)
                it_new = False
            except:
                feedback_like_dislike = FeedbackFromUsersLikeDislake.objects.create(feedback=feedback_object,
                                                                                    user=request.user,
                                                                                    score=score) 
                it_new = True

            if score == 0 and (it_new or (not it_new and score != feedback_like_dislike.score)):
                feedback_object.like += 1
            elif score == 1 and (it_new or (not it_new and score != feedback_like_dislike.score)):
                feedback_object.dislike += 1

            it_delete = False
            if score == 0 and not it_new and score == feedback_like_dislike.score:
                feedback_object.like -= 1
                it_delete = True
            elif score == 1 and not it_new and score == feedback_like_dislike.score:
                feedback_object.dislike -= 1
                it_delete = True

            if not it_new and score == 0 and score != feedback_like_dislike.score:
                feedback_object.dislike -= 1
            elif not it_new and score == 1 and score != feedback_like_dislike.score:
                feedback_object.like -= 1

            if not it_delete:
                feedback_like_dislike.score = score
                feedback_like_dislike.save()
            else:
                feedback_like_dislike.delete()

            feedback_object.save()

    except:
        pass


    return redirect('feedback')