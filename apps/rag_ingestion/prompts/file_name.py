FILE_NAME_PROMPT = """
# Convenção de nomes

**Padrão:**

```text
<disciplina>/<aaaa-mm-dd>_np<n>[_rec][_p<n>]_<@professor>.<ext>
```

**Legenda:**

| Segmento        | Descrição                       | Exemplo                 |
| --------------- | ------------------------------- | ----------------------- |
| `<disciplina>`  | pasta da disciplina, sem acento | `redes-de-computadores` |
| `<aaaa-mm-dd>`  | data de aplicação               | `2026-05-04`            |
| `_np<n>`        | número da NP                    | `_np1`                  |
| `[_rec]`        | recuperação (opcional)          | `_rec`                  |
| `[_p<n>]`       | parte (opcional)                | `_p2`                   |
| `_<@professor>` | @ do professor na UFFS          | `_marco.spohn`          |
| `.<ext>`        | extensão do arquivo             | `.pdf`                  |

**Exemplos:**

```text
redes-de-computadores/2026-05-04_np1_marco.spohn.pdf
redes-de-computadores/2026-05-04_np1_rec_marco.spohn.pdf
redes-de-computadores/2026-05-04_np1_rec_p1_marco.spohn.png
algoritmos/2024-08-20_np1_acneri.pdf
algoritmos/2024-09-10_np2_p1_andrei.braga.png
```

## Saída de nome de arquivo
- Preencha `arquivo.disciplina` e `arquivo.nome_arquivo` usando a convenção de nomes acima.
- A extensão do arquivo gerado deve ser `.json`.
- Use o usuário institucional do professor quando aparecer no documento; caso contrário,
  derive um identificador curto e estável do nome do professor, em minúsculas, sem acentos.
- Se a prova for recuperação, inclua `_rec`; se for parte específica, inclua `_p<n>`.
- Retorne somente dados extraídos ou inferidos a partir da prova.
"""

EXTRACTION_USER_PROMPT = "Extraia a prova completa do material anexo. Origem: {source_hint}"
