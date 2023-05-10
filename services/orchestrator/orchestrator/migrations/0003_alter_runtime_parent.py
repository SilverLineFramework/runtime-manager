# Generated by Django 4.1.7 on 2023-05-10 11:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator", "0002_alter_runtime_max_nmodules"),
    ]

    operations = [
        migrations.AlterField(
            model_name="runtime",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="orchestrator.manager",
            ),
        ),
    ]
