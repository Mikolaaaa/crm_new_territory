# Generated by Django 4.1.7 on 2023-04-03 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0028_remove_questionanswerlog_comment_answer_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionanswerlog",
            name="it_last_message_in_dialog",
            field=models.BooleanField(
                default=False, verbose_name="Это последнее сообщение в диалоге"
            ),
        ),
    ]
