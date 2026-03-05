from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Adds the GoogleSocialAccount model which links a Django User
    to their Google OAuth identity (sub = Google's unique user ID).
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('posts', '0002_add_like_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleSocialAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                # Google's immutable unique identifier for the user
                ('google_id', models.CharField(max_length=255, unique=True)),
                # Store basic profile info returned by Google
                ('email', models.EmailField(max_length=254)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('picture_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='google_account',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Google Social Account',
                'verbose_name_plural': 'Google Social Accounts',
            },
        ),
    ]