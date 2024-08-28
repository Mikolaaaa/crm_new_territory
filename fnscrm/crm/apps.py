from django.apps import AppConfig

class CrmConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    def ready(self):

        from django.conf import settings

        # if not settings.DEBUG:
        if not settings.DEBUG:
            from .models import QuestionAnswerLog
            from django.db.models import Q
            from crm.bot.my_app_telegram_functions import get_last_id_message, send_message

            import asyncio

            id_messages = QuestionAnswerLog.objects.filter(it_test=False).values_list('id_message', flat=True)
            id_messages_answer = QuestionAnswerLog.objects.filter(Q(it_test=False), ~Q(id_message_answer=None)).values_list('id_message_answer', flat=True)

            try:

                max_id_message = max(id_messages)

            except:

                max_id_message = 0

            try:
                max_id_message_answer = max(id_messages_answer)

            except:
                max_id_message_answer = 0

            start_id = max(max_id_message, max_id_message_answer)
            try:
                end_id = asyncio.run(get_last_id_message())
            except:
                end_id = 0

            if start_id > end_id:
                text_message = 'Начальный индекс в БД больше индекса в чате. Возможно какая то проблема!'
            elif start_id == end_id:
                text_message='Нет пропущенных сообщения с момента простоя'
            else:
                text_message = f'loadmessages:{start_id}:{end_id}'
            asyncio.run(send_message('me', text_message=text_message))


            asyncio.run(send_message(id_user='me', text_message='Сервер запущен!'))
            
            from scheduler import scheduler
            scheduler.start()
