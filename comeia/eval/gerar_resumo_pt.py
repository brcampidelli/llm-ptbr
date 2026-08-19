"""Gera o conjunto de resumo em PT: fonte + fatos essenciais + perguntas + resumo de referência.

⭐ POR QUE TEXTO SINTÉTICO, E NÃO NOTÍCIA REAL

Um corpus de notícias reais daria fontes mais naturais e **nenhum gabarito**. Para medir
invenção e omissão por execução é preciso saber, com certeza, quais fatos a fonte contém e
quais deles são essenciais — e isso ou é anotado à mão (caro, e sujeito a erro silencioso) ou
é construído junto com o texto. Este arquivo constrói junto.

O preço é honesto e vai declarado: os textos são **mais regulares** que jornalismo de verdade.
O modelo é avaliado num registro burocrático-noticioso brasileiro, não em prosa livre. O
número mede fidelidade e cobertura nesse registro; não é uma nota de "sabe resumir qualquer
coisa". A alternativa — ROUGE contra referência humana — não mede nem isso.

⚠️ CADA ITEM TRAZ O SEU PRÓPRIO RESUMO DE REFERÊNCIA, e ele existe para uma finalidade só:
   provar que o item é **resolvível** — que existe pelo menos um resumo que passa em todas as
   condições do avaliador. Esta é a lição de 35 referências impossíveis por construção, que
   fizeram o projeto medir 23,5% onde o real era 57,6%. A referência **não** é gabarito de
   texto: o modelo não é comparado a ela.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
SAIDA = RAIZ / "comeia" / "eval" / "benchmarks" / "resumo_pt.jsonl"

CIDADES = ["Sorocaba", "Juiz de Fora", "Feira de Santana", "Londrina", "Caxias do Sul",
           "Petrolina", "Marabá", "Chapecó", "Uberaba", "Campina Grande", "Blumenau",
           "Imperatriz", "Volta Redonda", "Rio Branco", "Divinópolis", "Araçatuba"]
BAIRROS = ["Vila Nova", "Jardim Paulista", "Centro Histórico", "Alto da Boa Vista",
           "Parque Industrial", "Cidade Alta", "Bela Vista", "Santa Terezinha"]
PESSOAS = ["Marina Salgado", "Rogério Tavares", "Cleide Nascimento", "Wilson Prado",
           "Andrea Bittencourt", "Otávio Mendonça", "Selma Rezende", "Ivan Queiroz",
           "Débora Vasconcelos", "Nelson Arruda", "Priscila Camargo", "Hamilton Ribas"]
EMPRESAS = ["Metalfrio Componentes", "Verdano Alimentos", "Trilha Log", "Aurora Têxtil",
            "Kaeta Bebidas", "Serrano Cimentos", "Pilar Farmacêutica", "Nordeste Solar"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def _n(rng, a, b, passo=1):
    return rng.randrange(a, b, passo)


def _brl(v: int) -> str:
    return f"{v:,}".replace(",", ".")


# ---------------------------------------------------------------- moldes
# Cada molde devolve (fonte, resumo_referencia, fatos_essenciais, perguntas).
# Os fatos ESSENCIAIS são os que qualquer resumo decente precisa carregar; as PERGUNTAS
# apontam para o subconjunto que um leitor perguntaria primeiro (o lide).
#
# ⚠️ As perguntas são verificadas por PRESENÇA da resposta no resumo, não por compreensão.
#    Um avaliador determinístico não sabe se o modelo entendeu; sabe se a informação
#    necessária para responder sobreviveu. Chamar isso de "QA" seria generoso, então fica
#    dito: é cobertura de segunda camada, medida sobre os fatos do lide.

def molde_obra(rng, i):
    cid, bai = rng.choice(CIDADES), rng.choice(BAIRROS)
    pes, mes = rng.choice(PESSOAS), rng.choice(MESES)
    custo, prazo = _n(rng, 4, 90) * 100_000, _n(rng, 8, 30)
    fam, metros = _n(rng, 300, 4000, 50), _n(rng, 400, 3200, 100)
    ano = rng.choice([2024, 2025, 2026])
    fonte = (
        f"A Prefeitura de {cid} assinou nesta semana o contrato de canalização do córrego que "
        f"corta o bairro {bai}. O investimento previsto é de R$ {_brl(custo)}, com recursos do "
        f"orçamento municipal e de repasse estadual. Segundo a secretária de Obras, {pes}, o "
        f"prazo de execução é de {prazo} meses a contar da ordem de serviço, emitida em {mes} "
        f"de {ano}. O projeto prevê {metros} metros de galeria e a recuperação da via marginal, "
        f"hoje interditada em dois trechos. A administração estima que {fam} famílias deixem de "
        f"ser atingidas pelas cheias que se repetem no verão. Moradores relatam alagamentos em "
        f"todos os anos desde a ocupação da área. O contrato prevê multa por atraso e vistoria "
        f"mensal da fiscalização, com relatórios publicados no portal da transparência. A "
        f"empresa vencedora apresentou a menor proposta entre as quatro habilitadas na "
        f"licitação, disputada em sessão pública. A obra será executada em três frentes "
        f"simultâneas para reduzir o impacto no trânsito local, segundo a pasta."
    )
    resumo = (
        f"A Prefeitura de {cid} contratou a canalização do córrego do bairro {bai} por "
        f"R$ {_brl(custo)}, com prazo de {prazo} meses. A obra terá {metros} metros de galeria "
        f"e deve tirar {fam} famílias da área de cheia, segundo a secretária {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "entidade", "valor": bai},
        {"tipo": "numero", "valor": custo}, {"tipo": "numero", "valor": prazo},
        {"tipo": "numero", "valor": metros}, {"tipo": "numero", "valor": fam},
        {"tipo": "entidade", "valor": pes, "aliases": [pes.split()[0], pes.split()[-1]]},
    ]
    perguntas = [
        {"pergunta": "Quanto custa a obra?", "fato": fatos[2]},
        {"pergunta": "Qual o prazo de execução?", "fato": fatos[3]},
        {"pergunta": "Em que cidade?", "fato": fatos[0]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_balanco(rng, i):
    emp, cid = rng.choice(EMPRESAS), rng.choice(CIDADES)
    pes = rng.choice(PESSOAS)
    receita = _n(rng, 12, 400) * 1_000_000
    margem, func, filiais = _n(rng, 3, 28), _n(rng, 120, 5000, 10), _n(rng, 2, 40)
    ano = rng.choice([2024, 2025])
    fonte = (
        f"A {emp} divulgou o balanço do exercício de {ano} com receita líquida de "
        f"R$ {_brl(receita)}. A margem operacional ficou em {margem}%, acima do registrado no "
        f"ano anterior, segundo o diretor financeiro {pes}. A companhia encerrou o período com "
        f"{_brl(func)} funcionários e {filiais} filiais em operação, concentradas no interior. "
        f"A sede administrativa permanece em {cid}, onde fica também o maior centro de "
        f"distribuição. O documento aponta que o endividamento de curto prazo foi reduzido e "
        f"que não houve captação nova no período. A empresa afirma que o plano de investimento "
        f"aprovado pelo conselho prioriza automação de linha e eficiência energética, sem "
        f"previsão de fechamento de unidades. O relatório foi auditado sem ressalvas e será "
        f"apresentado à assembleia de acionistas no próximo trimestre. A direção não divulgou "
        f"projeção de receita para o exercício seguinte, prática que mantém desde a abertura "
        f"de capital, e afirmou que o setor segue pressionado por custo de insumo importado."
    )
    resumo = (
        f"A {emp} fechou {ano} com receita líquida de R$ {_brl(receita)} e margem operacional "
        f"de {margem}%. A empresa, sediada em {cid}, tem {_brl(func)} funcionários e "
        f"{filiais} filiais, informou o diretor financeiro {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": emp, "aliases": [emp.split()[0]]},
        {"tipo": "numero", "valor": receita}, {"tipo": "numero", "valor": margem},
        {"tipo": "numero", "valor": func}, {"tipo": "numero", "valor": filiais},
        {"tipo": "entidade", "valor": cid},
        {"tipo": "numero", "valor": ano},
    ]
    perguntas = [
        {"pergunta": "Qual foi a receita?", "fato": fatos[1]},
        {"pergunta": "Qual a margem?", "fato": fatos[2]},
        {"pergunta": "Qual empresa?", "fato": fatos[0]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_saude(rng, i):
    cid, pes, mes = rng.choice(CIDADES), rng.choice(PESSOAS), rng.choice(MESES)
    casos, leitos, doses = _n(rng, 40, 3000, 10), _n(rng, 5, 120), _n(rng, 1000, 90000, 500)
    postos, cobertura = _n(rng, 4, 60), _n(rng, 41, 96)
    fonte = (
        f"A Secretaria de Saúde de {cid} registrou {_brl(casos)} casos de dengue confirmados "
        f"em {mes}, número que interrompeu a queda observada nos dois meses anteriores. A rede "
        f"municipal mantém {leitos} leitos de observação exclusivos para hidratação, "
        f"distribuídos em três unidades. Segundo a coordenadora de vigilância, {pes}, a "
        f"campanha aplicou {_brl(doses)} doses de vacina desde o início do ano, o que "
        f"corresponde a cobertura de {cobertura}% do público-alvo estimado. Os {postos} postos "
        f"da rede passam a funcionar aos sábados enquanto durar o período de maior "
        f"transmissão. A pasta reforça que a eliminação de criadouros dentro das residências "
        f"segue como a medida de maior efeito, já que a maior parte dos focos é encontrada em "
        f"quintais. Agentes de endemias visitam bairros com maior incidência e emitem "
        f"notificação em caso de recusa de acesso ao imóvel. O boletim completo é publicado "
        f"semanalmente e detalha a situação por região administrativa da cidade."
    )
    resumo = (
        f"{cid} confirmou {_brl(casos)} casos de dengue em {mes} e mantém {leitos} leitos de "
        f"hidratação. A campanha aplicou {_brl(doses)} doses, cobertura de {cobertura}%, e os "
        f"{postos} postos passam a abrir aos sábados, informou {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": casos},
        {"tipo": "numero", "valor": leitos}, {"tipo": "numero", "valor": doses},
        {"tipo": "numero", "valor": cobertura}, {"tipo": "numero", "valor": postos},
        {"tipo": "entidade", "valor": mes},
    ]
    perguntas = [
        {"pergunta": "Quantos casos?", "fato": fatos[1]},
        {"pergunta": "Qual a cobertura vacinal?", "fato": fatos[4]},
        {"pergunta": "Em qual cidade?", "fato": fatos[0]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_escola(rng, i):
    cid, pes = rng.choice(CIDADES), rng.choice(PESSOAS)
    mat, escolas, prof = _n(rng, 2000, 60000, 100), _n(rng, 8, 190), _n(rng, 100, 3000, 10)
    nota, vagas = _n(rng, 40, 89) / 10, _n(rng, 100, 4000, 50)
    ano = rng.choice([2025, 2026])
    fonte = (
        f"A rede municipal de {cid} abriu a matrícula para {ano} com {_brl(vagas)} vagas novas "
        f"na educação infantil. O sistema atende hoje {_brl(mat)} estudantes em {escolas} "
        f"escolas, com quadro de {_brl(prof)} professores efetivos. A secretária de Educação, "
        f"{pes}, afirmou que a meta é zerar a fila de espera para creche até o fim do primeiro "
        f"semestre. O índice de aprendizagem da rede ficou em {nota} pontos na última avaliação "
        f"estadual, resultado que a pasta considera insuficiente para a média histórica do "
        f"município. Entre as medidas anunciadas estão reforço em leitura no contraturno e "
        f"compra de material específico para os anos iniciais. A inscrição é feita pelo portal "
        f"da prefeitura ou presencialmente nas unidades, mediante comprovante de residência. "
        f"Famílias que já têm filho na rede têm prioridade de vaga na mesma unidade, regra "
        f"mantida desde o ano passado. O calendário letivo será publicado em diário oficial."
    )
    resumo = (
        f"{cid} abriu {_brl(vagas)} vagas novas na educação infantil para {ano}. A rede tem "
        f"{_brl(mat)} alunos, {escolas} escolas e {_brl(prof)} professores, e marcou {nota} "
        f"pontos na avaliação estadual, segundo a secretária {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": vagas},
        {"tipo": "numero", "valor": mat}, {"tipo": "numero", "valor": escolas},
        {"tipo": "numero", "valor": prof}, {"tipo": "numero", "valor": nota},
    ]
    perguntas = [
        {"pergunta": "Quantas vagas novas?", "fato": fatos[1]},
        {"pergunta": "Quantos alunos a rede atende?", "fato": fatos[2]},
        {"pergunta": "Qual a nota na avaliação?", "fato": fatos[5]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_transporte(rng, i):
    cid, pes = rng.choice(CIDADES), rng.choice(PESSOAS)
    linhas, passag = _n(rng, 6, 120), _n(rng, 8000, 400000, 1000)
    tarifa = _n(rng, 400, 750) / 100
    onibus, km = _n(rng, 20, 600, 5), _n(rng, 30, 900, 10)
    fonte = (
        f"O sistema de ônibus de {cid} passa a operar com {linhas} linhas a partir do próximo "
        f"mês, após a reorganização anunciada pela secretaria de Mobilidade. A tarifa fica em "
        f"R$ {tarifa:.2f}".replace(".", ",") + (
        f", valor mantido pelo terceiro reajuste adiado. A frota é de {onibus} veículos e "
        f"percorre {km} quilômetros de itinerário, segundo o secretário {pes}. A demanda média "
        f"é de {_brl(passag)} passageiros por dia útil, com pico entre seis e oito da manhã. A "
        f"mudança concentra as linhas troncais em dois corredores e cria integração temporal de "
        f"noventa minutos, sem cobrança adicional. O contrato de concessão prevê renovação da "
        f"frota e instalação de ar-condicionado em todos os veículos até o fim da vigência. "
        f"Usuários poderão consultar o itinerário novo no aplicativo oficial e nos pontos de "
        f"embarque, onde a sinalização será substituída. A secretaria manterá equipes de "
        f"orientação nos terminais durante as duas primeiras semanas de operação."
        )
    )
    resumo = (
        f"{cid} reorganiza o transporte para {linhas} linhas, com tarifa de "
        f"R$ {tarifa:.2f}".replace(".", ",") + (
        f". A frota de {onibus} ônibus cobre {km} quilômetros e atende {_brl(passag)} "
        f"passageiros por dia útil, informou o secretário {pes}."))
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": linhas},
        {"tipo": "numero", "valor": tarifa}, {"tipo": "numero", "valor": onibus},
        {"tipo": "numero", "valor": km}, {"tipo": "numero", "valor": passag},
    ]
    perguntas = [
        {"pergunta": "Qual a tarifa?", "fato": fatos[2]},
        {"pergunta": "Quantas linhas?", "fato": fatos[1]},
        {"pergunta": "Quantos passageiros por dia?", "fato": fatos[5]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_safra(rng, i):
    cid, pes = rng.choice(CIDADES), rng.choice(PESSOAS)
    hect, sacas = _n(rng, 500, 90000, 100), _n(rng, 20, 95)
    chuva, produtores = _n(rng, 40, 400, 5), _n(rng, 60, 4000, 10)
    queda = _n(rng, 3, 34)
    fonte = (
        f"A safra de milho da região de {cid} deve ocupar {_brl(hect)} hectares neste ciclo, "
        f"área semelhante à do ano passado. A produtividade estimada é de {sacas} sacas por "
        f"hectare, número que o sindicato rural considera conservador diante do volume de "
        f"chuva. O acumulado do trimestre chegou a {chuva} milímetros, distribuído de forma "
        f"irregular entre os municípios vizinhos. Segundo o engenheiro agrônomo {pes}, o "
        f"plantio tardio em áreas de várzea explica a diferença de estágio entre as lavouras. "
        f"A região reúne {_brl(produtores)} produtores cadastrados, a maioria em propriedades "
        f"de até cinquenta hectares. O custo de insumo subiu e comprimiu a margem, com queda de "
        f"{queda}% na rentabilidade projetada em relação ao ciclo anterior. Cooperativas "
        f"ampliaram a capacidade de armazenagem para reduzir a venda imediata na colheita, "
        f"quando o preço costuma ser o menor do ano. O boletim é revisado a cada quinze dias."
    )
    resumo = (
        f"O milho da região de {cid} deve ocupar {_brl(hect)} hectares com {sacas} sacas por "
        f"hectare. A chuva somou {chuva} milímetros, e a rentabilidade projetada cai {queda}% "
        f"para os {_brl(produtores)} produtores, diz o agrônomo {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": hect},
        {"tipo": "numero", "valor": sacas}, {"tipo": "numero", "valor": chuva},
        {"tipo": "numero", "valor": produtores}, {"tipo": "numero", "valor": queda},
    ]
    perguntas = [
        {"pergunta": "Quantos hectares?", "fato": fatos[1]},
        {"pergunta": "Qual a produtividade?", "fato": fatos[2]},
        {"pergunta": "Quanto caiu a rentabilidade?", "fato": fatos[5]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_energia(rng, i):
    cid, emp, pes = rng.choice(CIDADES), rng.choice(EMPRESAS), rng.choice(PESSOAS)
    mw, inv = _n(rng, 5, 400), _n(rng, 20, 900) * 1_000_000
    munic, empregos = _n(rng, 2, 30), _n(rng, 40, 2000, 10)
    meses = _n(rng, 10, 40)
    fonte = (
        f"A {emp} obteve licença para instalar um parque solar de {mw} megawatts na zona rural "
        f"de {cid}. O investimento anunciado é de R$ {_brl(inv)} e a obra deve durar {meses} "
        f"meses, segundo o diretor de operações {pes}. A energia gerada atenderá consumidores "
        f"de {munic} municípios por meio do mercado livre, sem afetar a tarifa regulada da "
        f"distribuidora local. A empresa estima {_brl(empregos)} empregos diretos no pico da "
        f"construção, a maior parte contratada na própria região. O licenciamento exigiu "
        f"estudo de fauna e compensação ambiental em área de cerrado preservado. A conexão será "
        f"feita em subestação existente, o que reduz a necessidade de nova linha de "
        f"transmissão. O cronograma prevê início da terraplenagem logo após o período chuvoso, "
        f"com montagem dos módulos em etapas. A operação comercial depende ainda de "
        f"autorização do operador nacional, cujo prazo de análise não foi informado."
    )
    resumo = (
        f"A {emp} vai instalar um parque solar de {mw} megawatts em {cid}, com investimento de "
        f"R$ {_brl(inv)} e {meses} meses de obra. A usina atenderá {munic} municípios e deve "
        f"gerar {_brl(empregos)} empregos diretos, diz o diretor {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": emp, "aliases": [emp.split()[0]]},
        {"tipo": "numero", "valor": mw}, {"tipo": "numero", "valor": inv},
        {"tipo": "numero", "valor": meses}, {"tipo": "numero", "valor": munic},
        {"tipo": "numero", "valor": empregos}, {"tipo": "entidade", "valor": cid},
    ]
    perguntas = [
        {"pergunta": "Qual a potência?", "fato": fatos[1]},
        {"pergunta": "Qual o investimento?", "fato": fatos[2]},
        {"pergunta": "Onde fica?", "fato": fatos[6]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_cultura(rng, i):
    cid, pes = rng.choice(CIDADES), rng.choice(PESSOAS)
    edicao, atracoes = _n(rng, 3, 40), _n(rng, 6, 90)
    publico, ingresso = _n(rng, 2000, 200000, 500), _n(rng, 0, 120, 5)
    dias, palcos = _n(rng, 2, 12), _n(rng, 1, 9)
    fonte = (
        f"O festival de música de {cid} chega à {edicao}ª edição com {atracoes} atrações "
        f"distribuídas em {palcos} palcos. A programação ocupa {dias} dias e a expectativa da "
        f"organização é de {_brl(publico)} pessoas no total. O ingresso para os shows da noite "
        f"custa R$ {ingresso}, e as apresentações diurnas são gratuitas, segundo a curadora "
        f"{pes}. Metade das atrações é formada por artistas da própria região, critério adotado "
        f"desde a retomada do evento. A prefeitura cede a área e a segurança, enquanto a "
        f"produção é bancada por patrocínio privado e por lei de incentivo. O festival mantém "
        f"programa de acessibilidade com intérprete de libras nos palcos principais e área "
        f"elevada para cadeirantes. A organização também firmou acordo com o comércio local "
        f"para ampliar a oferta de alimentação nos arredores. O balanço de público é divulgado "
        f"na semana seguinte ao encerramento, com dados de bilheteria auditados."
    )
    resumo = (
        f"A {edicao}ª edição do festival de {cid} terá {atracoes} atrações em {palcos} palcos "
        f"por {dias} dias, com expectativa de {_brl(publico)} pessoas. O ingresso da noite "
        f"custa R$ {ingresso} e as atrações diurnas são gratuitas, informou a curadora {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": edicao},
        {"tipo": "numero", "valor": atracoes}, {"tipo": "numero", "valor": publico},
        {"tipo": "numero", "valor": ingresso}, {"tipo": "numero", "valor": dias},
        {"tipo": "numero", "valor": palcos},
    ]
    perguntas = [
        {"pergunta": "Quantas atrações?", "fato": fatos[2]},
        {"pergunta": "Quanto custa o ingresso?", "fato": fatos[4]},
        {"pergunta": "Quantos dias?", "fato": fatos[5]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_esporte(rng, i):
    cid, pes = rng.choice(CIDADES), rng.choice(PESSOAS)
    g1, g2 = _n(rng, 0, 6), _n(rng, 0, 5)
    publico, renda = _n(rng, 800, 45000, 100), _n(rng, 20, 900) * 1_000
    rodada, pontos = _n(rng, 1, 38), _n(rng, 5, 70)
    fonte = (
        f"O time de {cid} venceu por {g1} a {g2} na {rodada}ª rodada, jogando em casa diante de "
        f"{_brl(publico)} torcedores. A renda bruta da partida foi de R$ {_brl(renda)}, "
        f"segundo o boletim divulgado pelo clube mandante. O técnico {pes} escalou time "
        f"reserva no segundo tempo, poupando titulares para a sequência de jogos fora. Com o "
        f"resultado, a equipe chegou a {pontos} pontos e se manteve na parte de cima da "
        f"tabela. O gol da vitória saiu de cobrança de falta no início da etapa final, em "
        f"lance que a arbitragem revisou no vídeo. O adversário terminou a partida com um "
        f"jogador a menos e reclamou da marcação do pênalti anulado. A próxima partida do time "
        f"da casa acontece no meio da semana, em campo neutro, por decisão da federação. O "
        f"clube informou que os ingressos serão vendidos apenas pelo site oficial."
    )
    resumo = (
        f"O time de {cid} venceu por {g1} a {g2} na {rodada}ª rodada diante de "
        f"{_brl(publico)} torcedores, com renda de R$ {_brl(renda)}. A equipe do técnico {pes} "
        f"chegou a {pontos} pontos."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid}, {"tipo": "numero", "valor": g1},
        {"tipo": "numero", "valor": publico}, {"tipo": "numero", "valor": renda},
        {"tipo": "numero", "valor": rodada}, {"tipo": "numero", "valor": pontos},
    ]
    perguntas = [
        {"pergunta": "Qual o público?", "fato": fatos[2]},
        {"pergunta": "Qual a renda?", "fato": fatos[3]},
        {"pergunta": "Quantos pontos?", "fato": fatos[5]},
    ]
    return fonte, resumo, fatos, perguntas


def molde_licitacao(rng, i):
    cid, emp, pes = rng.choice(CIDADES), rng.choice(EMPRESAS), rng.choice(PESSOAS)
    valor, itens = _n(rng, 3, 200) * 100_000, _n(rng, 4, 90)
    propostas, desconto = _n(rng, 2, 14), _n(rng, 2, 40)
    vigencia = _n(rng, 6, 60)
    fonte = (
        f"O pregão eletrônico da Prefeitura de {cid} para compra de merenda escolar foi "
        f"homologado no valor de R$ {_brl(valor)}. A {emp} venceu a disputa com desconto de "
        f"{desconto}% sobre o preço de referência, entre {propostas} propostas apresentadas. O "
        f"contrato cobre {itens} itens de gêneros alimentícios e tem vigência de {vigencia} "
        f"meses, prorrogável na forma da lei. Segundo o pregoeiro {pes}, não houve recurso "
        f"administrativo dentro do prazo legal. A entrega é semanal e escalonada por região, "
        f"com conferência de peso e validade na porta de cada unidade escolar. O edital exigiu "
        f"comprovação de capacidade técnica e amostra de cada item antes da assinatura. A "
        f"fiscalização será feita por comissão específica, com registro fotográfico das "
        f"entregas. O município informa que o pagamento segue a ordem cronológica de "
        f"apresentação das notas fiscais, conforme determina a legislação de contratos."
    )
    resumo = (
        f"A Prefeitura de {cid} homologou por R$ {_brl(valor)} o pregão da merenda escolar, "
        f"vencido pela {emp} com {desconto}% de desconto entre {propostas} propostas. O "
        f"contrato tem {itens} itens e vigência de {vigencia} meses, informou o pregoeiro {pes}."
    )
    fatos = [
        {"tipo": "entidade", "valor": cid},
        {"tipo": "entidade", "valor": emp, "aliases": [emp.split()[0]]},
        {"tipo": "numero", "valor": valor}, {"tipo": "numero", "valor": desconto},
        {"tipo": "numero", "valor": propostas}, {"tipo": "numero", "valor": itens},
        {"tipo": "numero", "valor": vigencia},
    ]
    perguntas = [
        {"pergunta": "Qual o valor homologado?", "fato": fatos[2]},
        {"pergunta": "Quem venceu?", "fato": fatos[1]},
        {"pergunta": "Qual o desconto?", "fato": fatos[3]},
    ]
    return fonte, resumo, fatos, perguntas


MOLDES = [molde_obra, molde_balanco, molde_saude, molde_escola, molde_transporte,
          molde_safra, molde_energia, molde_cultura, molde_esporte, molde_licitacao]


def gerar(n_por_molde: int = 15, semente: int = 20260819) -> list[dict]:
    rng = random.Random(semente)
    itens = []
    for molde in MOLDES:
        for k in range(n_por_molde):
            fonte, resumo, fatos, perguntas = molde(rng, k)
            itens.append({
                "id": f"{molde.__name__.replace('molde_', '')}-{k:02d}",
                "tema": molde.__name__.replace("molde_", ""),
                "fonte": fonte,
                "resumo_referencia": resumo,
                "fatos_essenciais": fatos,
                "perguntas": perguntas,
            })
    return itens


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    itens = gerar()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", encoding="utf-8") as f:
        for it in itens:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    h = hashlib.sha256(SAIDA.read_bytes()).hexdigest()[:32]
    print(f"✅ {len(itens)} itens · {len(MOLDES)} temas · {SAIDA.name}")
    print(f"   sha256[:32] = {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
