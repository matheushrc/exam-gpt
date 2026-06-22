from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rag_ingestion', '0005_remove_prova_unique_prova_prova_ano_semestre_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='questao',
            name='unique_questao',
        ),
        migrations.RenameField(
            model_name='questao',
            old_name='numero',
            new_name='ordem',
        ),
        migrations.AlterField(
            model_name='questao',
            name='ordem',
            field=models.IntegerField(
                help_text='Posição ordinal da questão, usada para reconstruir a ordem original — não é exibida ao usuário.'
            ),
        ),
        migrations.AddConstraint(
            model_name='questao',
            constraint=models.UniqueConstraint(fields=('ordem', 'enunciado'), name='unique_questao'),
        ),
    ]
