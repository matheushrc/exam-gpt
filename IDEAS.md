# Ideias

Legenda:

- [x] Implementado
- [ ] Não implementado
- [ ] Parcial: existe uma parte, mas ainda falta completar

## Fluxo de upload da prova

**Status geral:** parcial.

- [x] O aluno faz upload da prova — existe tela de upload e endpoint de extração para PDF/imagens.
- Da prova vamos extrair:
  - [x] nome do professor
  - [x] semestre — implementado como `ano_semestre`.
  - [x] matéria
  - [x] questões
  - [ ] alternativas, quando existirem — não encontrado como campo estruturado; hoje tende a ficar dentro do enunciado.
  - [x] pergunta — implementada como `enunciado`.
  - [x] resposta
  - [x] valor total — implementado como `pontuacao` na questão e `nota_final` na prova.
  - [x] valor recebido — implementado como `nota_recebida` na questão.

## Experiência de estudo

**Status geral:** parcial.

- [ ] Parcial: o aluno quer saber de uma prova de uma matéria, por exemplo estrutura de dados, e o sistema mostra várias provas em branco em tela — o chat faz busca RAG por matéria e mostra questões/fontes, mas não há tela dedicada de "provas em branco".
- [ ] Parcial: o aluno pode estudar sem as respostas da prova, pedindo para a IA não dar a resposta no prompt — o usuário pode pedir isso no prompt e os cards deixam a resolução recolhida, mas não há modo explícito/garantia de sistema para omitir respostas.
- [ ] Parcial: o aluno também pode estudar já com as respostas — o chat inclui respostas quando elas existem e os cards têm "Ver resolução".
- [ ] Fazer com que a IA consiga mostrar a frequência com que uma questão caiu em provas anteriores e mostrar os tipos de questão que caem.
- [ ] Montar um plano de estudo baseado nas questões mais frequentes.

## Respostas dos alunos

**Status geral:** parcial no modelo de dados, pendente na política de uso das
respostas.

- [ ] Deixar bem claro para a IA que as respostas serão baseadas nas respostas dos alunos — não encontrado no prompt do chat; o schema descreve `resposta` como resposta do aluno, mas o chat fala genericamente em questões, respostas e gabaritos.
- [ ] Usar um threshold de aceitação pelo valor recebido na questão, já que alguém que tira `0.5` em uma questão de `2` pontos não deveria ter sua resposta usada para ajudar outros alunos — `nota_recebida` e `pontuacao` são armazenadas, mas não há filtro no RAG baseado na razão `nota_recebida / pontuacao`.

## Prova principal

**Status geral:** pendente.

- [ ] Prova principal com todas as questões acumuladas — não encontrado modelo, entidade ou fluxo de prova principal/canônica.
- [x] A prova que entra é convertida em questões.
- [ ] Se a similaridade com a prova principal for menor que `20`, adicionar automaticamente na prova principal — não encontrado; a similaridade existente é usada para busca RAG e UI, não para mesclar questões em uma prova principal.
- [ ] Se a similaridade com a prova principal for maior que `80`, não adicionar na prova principal — não encontrado.

## Melhorias diversas

- [ ] Adicionar no texto de geração de embedding o nome completo do professor.
