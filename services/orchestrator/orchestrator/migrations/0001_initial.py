# Generated by Django 4.1.7 on 2023-02-17 13:46

from django.db import migrations, models
import django.db.models.deletion
import orchestrator.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Manager',
            fields=[
                ('uuid', models.CharField(default=orchestrator.models._uuidstr, max_length=64, primary_key=True, serialize=False)),
                ('name', models.CharField(default='manager', max_length=255)),
                ('status', models.CharField(default='A', max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='Runtime',
            fields=[
                ('uuid', models.CharField(default=orchestrator.models._uuidstr, max_length=64, primary_key=True, serialize=False)),
                ('name', models.CharField(default='runtime', max_length=255)),
                ('runtime_type', models.CharField(default='linux', max_length=16)),
                ('max_nmodules', models.IntegerField(default=1)),
                ('apis', models.JSONField(blank=True, default=orchestrator.models._default_runtime_apis)),
                ('platform', models.JSONField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('ka_interval_sec', models.IntegerField(default=60)),
                ('ka_ts', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(default='A', max_length=2)),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='orchestrator.manager')),
            ],
        ),
        migrations.CreateModel(
            name='Module',
            fields=[
                ('index', models.AutoField(primary_key=True, serialize=False)),
                ('uuid', models.CharField(default=orchestrator.models._uuidstr, max_length=64)),
                ('name', models.CharField(default='module', max_length=255)),
                ('file', models.TextField()),
                ('apis', models.JSONField(blank=True, default=orchestrator.models._default_required_apis)),
                ('args', models.JSONField(blank=True, default=orchestrator.models._emptylist)),
                ('channels', models.JSONField(blank=True, default=orchestrator.models._emptylist)),
                ('status', models.CharField(default='A', max_length=2)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='orchestrator.runtime')),
            ],
        ),
    ]
