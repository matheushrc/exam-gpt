from django.core.validators import RegexValidator
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    DateField,
    FloatField,
    Form,
    IntegerField,
)


class MetaForm(Form):
    professor = ChoiceField(required=False)
    cursos = CharField(required=False)
    ano_semestre = CharField(
        validators=[RegexValidator(r"^\d{4}\.[12]$")],
    )
    materia = CharField()
    numero_avaliacao = IntegerField(min_value=1)
    recuperacao = BooleanField(required=False)
    nota_final = FloatField(required=False)
    data_aplicacao = DateField()

    def __init__(self, *args, professores: list[dict] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        professores = professores or []
        choices = [(p["username"], p["name"]) for p in professores]
        self.fields["professor"].choices = [("", "---")] + choices
