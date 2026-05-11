from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generator", "0004_generatorprofile_transform_modes"),
    ]

    operations = [
        migrations.AddField(
            model_name="word",
            name="adult_only",
            field=models.BooleanField(default=False),
        ),
    ]
