# Generated by Django 4.1.7 on 2023-04-05 06:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0032_сhatmemberscount"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="сhatmemberscount",
            options={
                "verbose_name": "Запись",
                "verbose_name_plural": "Количество участников (Лог)",
            },
        ),
    ]
