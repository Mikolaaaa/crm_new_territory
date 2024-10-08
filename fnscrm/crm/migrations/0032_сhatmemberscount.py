# Generated by Django 4.1.7 on 2023-04-04 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0031_questionanswerlog_it_last_message_in_dialog"),
    ]

    operations = [
        migrations.CreateModel(
            name="СhatMembersCount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "datetime_of_the_cut",
                    models.DateTimeField(verbose_name="Дата/время среза"),
                ),
                (
                    "count",
                    models.IntegerField(
                        default=0, verbose_name="Количество участников"
                    ),
                ),
            ],
        ),
    ]
