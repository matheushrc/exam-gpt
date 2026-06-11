EXEMPLOS_PROMPT = """
## Exemplos de formatação

### Enunciado com negrito e itálico preservados

```
**Network Kid** *(NK)* afirma que triplicar os servidores DNS raiz eliminaria os demais níveis.
**NK está certo?** Justifique sua resposta.
```

### Enunciado com topologia de rede (ASCII art)

```
Considere a topologia:

\\`\\`\\`
R1 ─── R2 ─── R3 ─── R4
\\`\\`\\`

Com enlaces de 400 Kbps e atraso de propagação de 5 ms por enlace, qual o tempo total para envio de um pacote de 2000 bytes usando comutação de pacotes?
```

### Enunciado com tabela (tabela Markdown)

```
Preencha a evolução da janela de congestionamento TCP:

| Rodada | Janela | Threshold |
|--------|--------|-----------|
| 1      | 1      | 20        |
| 2      |        |           |
```

### Resposta do aluno com tabela preenchida (tabela Markdown)

```
| Rodada | Janela | Threshold |
|--------|--------|-----------|
| 1      | 1      | 20        |
| 2      | 2      | 20        |
| 3      | 4      | 20        |
| 9      | 1      | 11        |
| 10     | 2      | 11        |
```

### Resposta do aluno com diagrama desenhado (ASCII art)

```
\\`\\`\\`
A ──5── B
|       |
3       2
|       |
C ──1── D
\\`\\`\\`
```

### Resposta do aluno dissertativa com cálculo

```
**Não**, pois mesmo que enlaces físicos sejam livres de erros, o TCP ainda precisa
de transmissão confiável para tratar erros nas camadas superiores.

Tempo de transmissão: $t = \\tfrac{2000 \\times 8}{400000} = 40\\,ms$
```
"""
