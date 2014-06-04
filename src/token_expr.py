# -*- coding: utf-8 -*-

import contrib_nltk.tokenize, re

str = '''O Corpus Histórico do Português Tycho Brahe é um corpus eletrônico anotado, composto de textos em português escritos por autores nascidos entre 1380 e 1845.

Atualmente, 53 textos (2.464.191 palavras) estão disponíveis para pesquisa livre, com um sistema de anotação linguística em duas etapas: anotação morfológica (aplicada em 30 textos); e anotação sintática (aplicada em 11 textos).

O Corpus é desenvolvido junto ao projeto temático
Padrões Rítmicos, Fixação de Parâmetros & Mudança Linguística

Valores: 100$000 (R$ 100.000,00) .3% 0.8% 1° 3 = 4 $30 [(x + (y - z))*3] 4+4=8 5*6 (4-(2*1))
Arcaísmos: no~ algu~
Twitter: #hashtag
XML: <texto>
Data: 22/10/1934
Módulo: |x|
Vende-se carros; são "três", não 'seis'; D. João VI, m.to, Prof. Leo, Dr. João, Exmo., Illmo., O.N.U.,
Outras pontuações: Que foi? Você, Pedro?! Não acredito! Que pena...
Espanhol: ¿Que fue? ¡Habla muchacho!
Coordenadora: Profa. Dra. Charlotte Galves (galvesc@unicamp.br)

A motivação para esta pesquisa é a busca por uma abordagem distinta – e, talvez, mais abstrata – para
o conhecimento gramatical, que permita desenvolver um modelo de aquisição alternativo ao de
Berwick, que seja mais robusto – abarque um maior conhecimento gramatical – e mais universal – seja
aplicável a um maior conjunto de línguas. É justamente nestes dois aspectos que se situam as
principais limitações do modelo de Berwick (algumas das quais são apontadas em Mazuka, 1998), o que
nos leva a crer que os modelos teóricos – Gramática Transformacional (cf. Chomsky, 1965) e Teoria de
Regência e Ligação (cf. Chomsky, 1986) – em que se baseia contém idiossincrasias linguísticas (no
caso, do inglês e, possivelmente, das línguas românicas), não sendo, portanto, tão universais quanto
desejaríamos. Em termos de aquisição, ademais, outros modelos propostos (Wexler & Culicover, 1980;
Gibson & Wexler, 1994; Fodor, 1998; Fodor & Sakas, 2004; entre outros) incorrem, de modo geral, no
mesmo tipo de limitação.

1.1. Introdução
'''

expr = ['Prof(a)?\.',
        'D\.',
        'Illm[ao]\.',
        'Dr(a)?\.',
        'Exm[ao]\.',
        'cf\.',
        'O\.N\.U\.',
        '[\(\[\{\'"]',  # Abertura de parênteses, aspas, etc.
        '[\)\]\}]',  # Fechamento de parênteses
        '^[¿¡]',  # Pontuações no início da sentença (espanhol)
        '[\.!?;:,]+$',  # Pontuações ao final das palavras
        '.*[^\.!?;:,\)\]\}\'"]']  # Palavras (alfanumérico)

# Parágrafos são definidos pelo salto de uma linha em branco
for p in contrib_nltk.tokenize.blankline(str):
    p_rev = ''
    # Passo 1: tokeniza primeiramente por espaço em branco
    for pre_tk in contrib_nltk.tokenize.regexp(p, r'[^\s]+'):
        # Passo 2: retokeniza os tokens obtidos com base na lista de expressões
        for punc_tk in contrib_nltk.tokenize.regexp(pre_tk, '|'.join(expr)):
            p_rev += punc_tk + ' '
    # Passo 3: agora, que identificamos mais confiavelmente as pontuações de
    #          fim de sentença, fazemos a separação das sentenças
    for s in contrib_nltk.tokenize.regexp(p_rev, r'(.+?)( ([\.!?]+)? |$)'):
        print s + '\n'

    print '\n'

print re.escape('Dr.')
