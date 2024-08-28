from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField('Наименование', max_length=250)
    id_post = models.IntegerField('ИД поста')
    id_post_test = models.IntegerField('ИД тестового поста', default=0)
    it_test = models.BooleanField('Это тест', default=False)

    class Meta:
        verbose_name = u'Категория'
        verbose_name_plural = u'Категории'

    def __str__(self):
        return self.name
    
class UserForPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Сотрудник')
    category = models.ForeignKey('Category', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Категория')
    it_moder = models.BooleanField('Это модератор')
    it_test = models.BooleanField('Это тест', default=False)

    class Meta:
        verbose_name = u'Ответственнй сотрудник темы'
        verbose_name_plural = u'Ответственные сотрудники тем'

    def __str__(self):
        return f'{self.user} {self.category}'


class Field(models.Model):
    name = models.CharField('Наименование', max_length=250)

    def __str__(self):
        return self.name

class QuestionAnswer(models.Model):
    question = models.TextField('Вопрос')
    answer = models.TextField('Ответ', null=True, blank=True)
    category = models.ForeignKey('Category', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Категория', 
                                 null=True, blank=True)
    field = models.ForeignKey('Field', 
                              on_delete=models.CASCADE,
                              verbose_name='Область', 
                              null=True, blank=True)
    specialist = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Специалист', 
                                   null=True, blank=True)
    datetime = models.DateTimeField('Дата/время ответа', null=True, blank=True)
    datetime_question = models.DateTimeField('Дата/время вопроса', null=True)
    it_test = models.BooleanField('Это тест', default=False)

    def __str__(self):
        return f'({self.id}) {self.answer}'

class QuestionAnswerLog(models.Model):
    id_message = models.IntegerField('ID сообщения в ТГ')
    question = models.TextField('Вопрос')
    answer = models.ForeignKey('QuestionAnswer', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Ответ в базе', 
                                 null=True,
                                 blank=True)
    answer_text = models.TextField('Ответ', null=True, blank=True)
    datetime = models.DateTimeField('Дата/время ответа', null=True, blank=True)
    datetime_question = models.DateTimeField('Дата/время вопроса')
    it_test = models.BooleanField('Это тест', default=False)
    category = models.ForeignKey('Category', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Категория', 
                                 null=True, blank=True)
    retarget_category = models.ForeignKey('Category', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Старая категория', 
                                 null=True, blank=True, related_name='retarget_category')
    reply_to_message_id = models.IntegerField('ID предыдущего сообщения в ТГ', null=True, blank=True)
    specialist = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Специалист', 
                                   null=True, blank=True)
    it_agreed = models.BooleanField('Не согласовано', default=False)   
    like = models.IntegerField('Лайк', default=0)                         
    dislike = models.IntegerField('Дизлайк', default=0)    
    id_message_answer = models.IntegerField('ID сообщения ответа в ТГ', null=True, blank=True)                     
    id_question_autor = models.IntegerField('ID автора вопроса в ТГ', null=True, blank=True)
    it_finaly = models.BooleanField('Финальный ответ', default=False)
    score_answer = models.IntegerField('Оценка ответа', default=0)
    comment_retarget_category = models.TextField('Комментарий при смене категории', null=True, blank=True)
    it_last_message_in_dialog = models.BooleanField('Это последнее сообщение в диалоге', default=True)
    first_question = models.ForeignKey('QuestionAnswerLog', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Начальный вопрос', 
                                 null=True,
                                 blank=True)
    it_interim = models.BooleanField('Промежуточный ответ', default=False)
    encode = models.BooleanField('Вопрос кодирован', default=False)

    class Meta:
        verbose_name = u'Вопрос-ответ'
        verbose_name_plural = u'База данных'

class ConstantData(models.Model):
    name = models.CharField('Наименование', max_length=100)
    value = models.CharField('Значение', max_length=300)

    def __str__(self):
        return f'{self.name}: {self.value}'
    
class TagsForFind(models.Model):
    name = models.CharField('Тег', max_length=200)
    category = models.ForeignKey('Category', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Категория')

    class Meta:
        verbose_name = u'Тег'
        verbose_name_plural = u'Теги'

    def __str__(self):
        return f'{self.name}: {self.category.name}'
    
class СhatMembersCount(models.Model):
    datetime_of_the_cut = models.DateTimeField('Дата/время среза')
    count = models.IntegerField('Количество участников', default=0)

    class Meta:
        verbose_name = u'Запись'
        verbose_name_plural = u'Количество участников (Лог)'

    def __str__(self):
        return f'{self.datetime_of_the_cut}: {self.count}'    

def get_name(self):
    return '{} {}'.format(self.last_name, self.first_name)

User.add_to_class("__str__", get_name)

class Department(models.Model):

    name = models.CharField('Подразделение', max_length=200)
    staff = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Сотрудники')

    def __str__(self):
        return f'({self.id}) {self.name}'

CHOISE_TYPE_ACTION_REQUEST = [(0, 'Создать'), (1, 'Изменить'), (2, 'Удалить')]

class RequestToAddModerators(models.Model):

    name = models.CharField('Фамилия инициалы', max_length=200)
    department = models.ForeignKey('Department', on_delete=models.CASCADE, max_length=200, verbose_name='Подразделение', null=True, blank=True)
    login_tg = models.CharField('Логин в ТГ', max_length=200, null=True, blank=True)
    categories = models.ManyToManyField('Category', verbose_name='Категории')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Автор заявки')
    datatime_request = models.DateTimeField(auto_now_add=True, verbose_name='Дата/время создания завявки')
    datatime_create_moder = models.DateTimeField(null=True, blank=True, verbose_name='Дата/время создания модератора')
    comment = models.TextField('Комментарий', null=True, blank=True, default='')
    it_rejection = models.BooleanField('Отказ', default=False)
    type_action_request = models.IntegerField('Тип дейтсвия заявки', choices=CHOISE_TYPE_ACTION_REQUEST, default=0)
    user_edit_delete = models.ForeignKey(settings.AUTH_USER_MODEL,
                                         on_delete=models.CASCADE,
                                         verbose_name='Модератор', related_name='user_edit_delete', blank=True, null=True)

    def __str__(self):
        if self.user_edit_delete:
            return f'{self.user_edit_delete}'
        else:
            return f'{self.name}'
    
CHOISE_TYPE_MESSAGE = [(0, 'Спам'), (1, 'Промежуточный')]

class StopPhrase(models.Model):

    phrase = models.CharField('Стоп фраза', max_length=300)
    type_message = models.IntegerField('Тип сообщения', choices=CHOISE_TYPE_MESSAGE)

    class Meta:
        verbose_name = u'Стоп фраза'
        verbose_name_plural = u'Стоп фразы'

    def __str__(self):
        return f'{CHOISE_TYPE_MESSAGE[self.type_message][1]}: {self.phrase}'
    
CHOISE_STATUS_FEEDBACK = [(0, 'Зарегистрировано'), 
                          (1, 'Просмотрено'),
                          (2, 'На рассмотрении'),
                          (3, 'В работе'),
                          (4, 'Завершено'),
                          (5, 'Отклонено')]

class FeedbackFromUsers(models.Model):

    CHOISE_TYPE_FEEDBACK = [(0, 'Предложение по улучшению'),
                            (1, 'Сообщить об ошибке')]

    feedback = models.TextField('Обратная связь')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Автор')
    datatime_feedback = models.DateTimeField(auto_now_add=True, verbose_name='Дата/время сообщения')
    like = models.IntegerField('Лайки', default=0)
    dislike = models.IntegerField('Дизлайки', default=0)
    comment = models.TextField('Комментарий', blank=True, null=True, default='')
    status = models.IntegerField('Статус', default=0, choices=CHOISE_STATUS_FEEDBACK)
    type_feedback = models.IntegerField('Тип обратной связи', default=0, choices=CHOISE_TYPE_FEEDBACK)

class FeedbackFromUsersLikeDislake(models.Model):

    feedback = models.ForeignKey('FeedbackFromUsers', 
                                 on_delete=models.CASCADE,
                                 verbose_name='Обратная связь')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   verbose_name='Пользователь')
    
    score = models.BooleanField('Оценка')