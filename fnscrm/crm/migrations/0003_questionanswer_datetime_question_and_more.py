# Generated by Django 4.1.7 on 2023-03-03 08:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0002_questionanswer'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionanswer',
            name='datetime_question',
            field=models.DateTimeField(null=True, verbose_name='Дата/время вопроса'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='answer',
            field=models.TextField(verbose_name='Ответ'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.category', verbose_name='Категория'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='datetime',
            field=models.DateTimeField(null=True, verbose_name='Дата/время ответа'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='field',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.field', verbose_name='Область'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='question',
            field=models.TextField(verbose_name='Вопрос'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='specialist',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Специалист'),
        ),
        migrations.CreateModel(
            name='questionanswerlog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_message', models.IntegerField(verbose_name='ID сообщения в ТГ')),
                ('question', models.TextField(verbose_name='Вопрос')),
                ('datetime', models.DateTimeField(null=True, verbose_name='Дата/время ответа')),
                ('datetime_question', models.DateTimeField(verbose_name='Дата/время вопроса')),
                ('answer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='crm.questionanswer', verbose_name='Ответ в базе')),
            ],
        ),
    ]
