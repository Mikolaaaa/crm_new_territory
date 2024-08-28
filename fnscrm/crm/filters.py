import django_filters
from .models import *
from django import forms
from django.db.models import Q
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

BOOL_CHOICES = (
    (1, 'Да'),
    (0, 'Нет'),
)

BOOL_CHOICES_SCORE = (
    (1, 'Полностью удовлетворен'),
    (2, 'Частично удовлетворен'),
    (3, 'Не удовлетворен'),
)

BOOL_CHOICES_LIKE_AND_DISLIKE = (
    (0, 'Только с лайками (Возр.)'),
    (1, 'Только с лайками (Убыв.)'),
    (2, 'Только с дизлайками (Возр.)'),
    (3, 'Только с дизлайками (Убыв.)'),
)

BOOL_CHOICES_SORT = (
    (0, 'Дата/время вопроса (Возр.)'),
    (1, 'Дата/время вопроса (Убыв.)'),
    (2, 'Дата/время ответа (Возр.)'),
    (3, 'Дата/время ответа (Убыв.)'),
)

BOOL_CHOICES_ANSWER = (
    (0, 'Финальные'),
    (1, 'Промежуточные'),
    (2, 'Без ответа'),
    (3, 'Просрочка более 2-х дней'),
    (4, 'Спам'),
    (5, 'Несогласованная переадресация'),
)

class DateInput(forms.DateInput):
    input_type = 'date'

class EndFilter(django_filters.DateFilter):

    def filter(self, qs, value):
        if value:
            value = value + timedelta(1)
        return super(EndFilter, self).filter(qs, value)

class LogMessagesFilter(django_filters.FilterSet):

    it_finaly = django_filters.ChoiceFilter(choices=BOOL_CHOICES)
    it_test = django_filters.ChoiceFilter(choices=BOOL_CHOICES)
    only_answer = django_filters.ChoiceFilter(choices=BOOL_CHOICES, field_name='answer_text', method='filter_only_answer')
    score_answer = django_filters.ChoiceFilter(choices=BOOL_CHOICES_SCORE)
    like_and_dislike = django_filters.ChoiceFilter(choices=BOOL_CHOICES_LIKE_AND_DISLIKE, method='filter_like_and_dislike')
    data_sort = django_filters.ChoiceFilter(choices=BOOL_CHOICES_SORT, method='filter_data_sort')
    datetime_question_gte = django_filters.DateFilter(field_name="datetime_question", lookup_expr='gte', widget=DateInput(
            attrs={
                'class': 'datepicker'
            }
        ))
    datetime_question_lte = EndFilter(field_name="datetime_question", lookup_expr='lt', widget=DateInput(
            attrs={
                'class': 'datepicker'
            }
        ))
    choice_answer = django_filters.ChoiceFilter(choices=BOOL_CHOICES_ANSWER, method='filter_choice_answer')

    specialist = django_filters.ModelChoiceFilter(queryset=User.objects.all().order_by('last_name'))

    question_text = django_filters.CharFilter(method='filter_question_text')

    def filter_question_text(self, queryset, name, value):
        return queryset.filter(question__icontains=value)

    def filter_choice_answer(self, queryset, name, value):
        if value == '0':
            return queryset.filter(Q(it_finaly=True))
        elif value == '1':
            return queryset.filter(Q(it_interim=True) & Q(it_last_message_in_dialog=True))
        elif value == '2':
            return queryset.filter(Q(answer_text=None) & Q(retarget_category=None) & Q(datetime=None))
        elif value == '3':
            return queryset.filter(Q(answer_text=None) & Q(datetime_question__lte=(timezone.now() - datetime.timedelta(days=2))) & Q(retarget_category=None) & Q(datetime=None))
        elif value == '4':
            return queryset.filter(Q(answer_text=None) & Q(retarget_category=None) & ~Q(datetime=None))
        elif value == '5':
            return queryset.filter(~Q(retarget_category=None) & Q(it_agreed=True))
        else:
            return queryset

    def filter_specialist(self, queryset, name, value):
        return queryset#.order_by('last_name')

    def filter_only_answer(self, queryset, name, value):
        if value == '0':
            return queryset.filter((Q(answer_text=None) | Q(answer_text='')) & Q(retarget_category=None))
        elif value == '1':
            return queryset.filter(~Q(answer_text=None) & ~Q(answer_text=''))
        else:
            return queryset

    def filter_like_and_dislike(self, queryset, name, value):
        if value == '0':
            return queryset.filter(~Q(like=0)).order_by('like')
        elif value == '1':
            return queryset.filter(~Q(like=0)).order_by('-like')
        elif value == '2':
            return queryset.filter(~Q(dislike=0)).order_by('dislike')
        elif value == '3':
            return queryset.filter(~Q(dislike=0)).order_by('-dislike')
        else:
            return queryset

    def filter_data_sort(self, queryset, name, value):
        if value == '0':
            return queryset.order_by('first_question__datetime')
        elif value == '1':
            return queryset.order_by('-first_question__datetime')
        elif value == '2':
            return queryset.order_by('datetime')
        elif value == '3':
             return queryset.order_by('-datetime')
        else:
            return queryset

    class Meta:
        model = QuestionAnswerLog
        fields = ['question_text', 'category', 'specialist', 'it_finaly', 'it_test', 'score_answer', 'datetime_question_gte', 'datetime_question_lte', 'datetime_question']

class CategoryFilter(django_filters.FilterSet):

    class Meta:
        model = QuestionAnswerLog
        fields = ['category']

class FeedbackFilter(django_filters.FilterSet):

    class Meta:
        model = FeedbackFromUsers
        fields = ['status', 'type_feedback']