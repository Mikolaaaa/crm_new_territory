# Generated by Django 4.1.7 on 2023-03-23 08:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0024_alter_questionanswerlog_it_finaly'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionanswerlog',
            name='comment_answer',
            field=models.TextField(blank=True, null=True, verbose_name='Ответ'),
        ),
        migrations.AddField(
            model_name='questionanswerlog',
            name='score_answer',
            field=models.IntegerField(default=0, verbose_name='Оценка ответа'),
        ),
    ]
