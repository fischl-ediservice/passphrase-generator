from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generator", "0003_user_word_feedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatorprofile",
            name="digit_mode",
            field=models.CharField(default="off", max_length=20),
        ),
        migrations.AddField(
            model_name="generatorprofile",
            name="special_mode",
            field=models.CharField(default="off", max_length=20),
        ),
        migrations.AddField(
            model_name="generatorprofile",
            name="syllable_shuffle_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
