from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Adds the Like model.
    Depends on the previous migration that created Post and Comment.
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # Replace '0001_initial' with the name of your latest existing migration
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='likes',
                    to='posts.post',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='likes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('user', 'post')},
            },
        ),
    ]