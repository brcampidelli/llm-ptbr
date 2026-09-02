# Triagem de 13 fontes de corpus (2026-09-02) — licença lida na origem, nunca no rótulo

> **O achado que reorganiza a decisão:** o `PleIAs/common_corpus` traz **2,27 trilhões de tokens**
> com procedência documentada **por documento** e uso comercial explicitamente permitido — e cobre
> **7 dos nossos 8 idiomas-alvo**. Falta exatamente **o português**, que é o único onde já temos
> 21,97B próprios. A complementaridade é quase perfeita, e não foi projetada.
>
> ⚠️ **Por que esta triagem foi refeita.** Uma primeira passada existiu em 2026-09-01 e se perdeu
> na compactação do contexto. Escrever "licença verificada na origem" a partir de lembrança seria
> o oposto do que a frase afirma — então tudo abaixo foi consultado de novo na API do HF e nos
> README/termos, em 2026-09-02.

---

## 1. A tabela

| fonte | licença **verificada na origem** | idiomas | veredito |
|---|---|---|---|
| `HuggingFaceFW/fineweb-2` | **ODC-By** | 1.813 | ✅ **em uso** — é o nosso corpus PT |
| `HuggingFaceFW/fineweb` | **ODC-By** | en | ✅ **ADOTAR** — censo de repetição feito (0,975%) |
| `PleIAs/common_corpus` | livre, **uso comercial permitido**, procedência por documento | 13 (⚠️ **sem pt**) | ⭐ **ADOTAR para 7 dos 8** |
| `PleIAs/US-PD-Newspapers` | **CC0-1.0** | en | ⚠️ nicho — jornais históricos |
| `PleIAs/Multilingual-PD` | 🔴 **campo de licença VAZIO** | — | ❌ **não adotar** |
| `PleIAs/openculture` | 🔴 **HTTP 401** — não existe publicamente | — | ❌ **link morto** |
| `uonlp/CulturaX` | 🔴 **VAZIO** + gated | 167 | ❌ **não adotar** |
| `openbmb/Ultra-FineWeb` | Apache-2.0 **auto-contraditória** | en, zh | ❌ **não adotar** |
| `wikimedia/wikipedia` | **CC-BY-SA-3.0 + GFDL** | 322 | ⚠️ share-alike — segue como **holdout** |
| `bigcode/the-stack` (+v2) | **"other"** + gated + ToU repassável | código | ⚠️ conflita com reprodutibilidade |
| `fka/awesome-chatgpt-prompts` | **CC0-1.0** | — | ⚠️ 153 prompts, não é corpus |
| **HPLT v3** (site próprio) | **CC0** declarado | multi | ⚠️ conferir no artefato, não no site |
| `hplt-project/OpusTrainer` | **MIT** — é **código**, não corpus | — | ✅ copiar a ideia, sem dependência |

---

## 2. ⭐⭐ O Common Corpus e o buraco em forma de português

**2,27 trilhões de tokens.** O README declara, com todas as letras:

> *"All data in Common Corpus are either uncopyrighted or freely licensed and may be used for both
> commercial and non-commercial purposes."*

E cada documento carrega o campo `license` com a origem do direito — domínio público, CC0 do
Wikidata, ou licença livre nomeada. Isso é **procedência por documento**, não rótulo de repositório:
é a diferença exata que o projeto aprendeu no caso brWaC.

**Cobertura contra os nossos 8 alvos:**

| alvo | no Common Corpus |
|---|---|
| eng · fra · deu · spa · cmn · jpn · arb | ✅ os sete |
| **por** | 🔴 **ausente** |

⭐ **E é justamente o português que não precisamos dele para ter** — temos 21,97B próprios, em três
faixas, com o censo de repetição feito (0,28%). A fonte de melhor procedência do lote cobre
exatamente o complemento do que já possuímos.

⚠️ **O que isto NÃO decide.** Common Corpus é livro, jornal, ciência e administração pública —
composição muito diferente da web do fineweb-2. Trocar uma pela outra muda a **distribuição**, não
só a licença, e o efeito disso em bpb **não está medido**. Entra no Gate T2 (mistura) como braço,
não como substituição.

---

## 3. 🔴 Três reprovações, e cada uma por um motivo diferente

### 3.1 CulturaX — "gated" não é "licenciado"

Campo de licença **vazio**. O termo que se aceita para baixar diz, na íntegra:

> *"you acknowledge that the provided data is offered as is […] you accept full responsibility for
> any repercussions […] you agree that the data must not be utilized for malicious or harmful
> purposes"*

⭐ **Isso é uma isenção de responsabilidade, não uma concessão de direitos.** Aceitar o termo diz o
que *não* se pode fazer; em momento nenhum diz sob que licença o conteúdo é oferecido. Um portão na
frente de uma porta sem fechadura declarada continua sem fechadura declarada.

### 3.2 Ultra-FineWeb — o rótulo contradiz o próprio README

O campo diz **Apache-2.0**. O README diz:

> *"since Ultra-FineWeb is built using multiple datasets, users should check the LICENSE of each
> dataset individually"*

⭐ **Um invólucro permissivo sobre conteúdo de licença não declarada não torna o conteúdo
permissivo.** E some-se: só **inglês e chinês** — não resolve seis dos nossos oito.

### 3.3 The Stack — conflito com um item do nosso próprio checklist

Licença **"other"**, gated, e o ToU exige três coisas. A terceira é a que morde:

> *"By clicking on 'Access repository', you agree to **update your own version of The Stack to the
> most recent usable version**"* — conforme pedidos de remoção de dados são processados.

🔴 **Um corpus que muda sob você é incompatível com "corpus verificado por hash contra a
referência"**, que é item do checklist deste projeto. Ou o hash bate e o ToU está sendo violado, ou
o ToU é cumprido e o corpus não é mais o que produziu o modelo publicado. As duas coisas não cabem
juntas.

⚠️ E o ToU é **repassável**: quem hospedar ou compartilhar tem de incluir os termos e exigir aceite.
Isso se propaga a qualquer derivado que redistribuamos.

---

## 4. ⚠️ Wikipédia — a que fica, mas não onde se pensa

**CC-BY-SA-3.0 + GFDL**, 322 idiomas. *Share-alike* sobre corpus de treino é área cinzenta que este
projeto não vai resolver por conta própria.

✅ **E ela já cumpre o melhor papel possível: holdout.** O gate das faixas usou Wikipédia-PT como
régua primária justamente porque nenhum braço a via — 0,12% de sobreposição com o pool. Ler como
teste não é redistribuir, e a função dela ali é insubstituível.

---

## 5. O que muda no plano

1. **Inglês:** `fineweb` — ✅ decidido, censo feito, ODC-By.
2. **Os outros 6 não-PT:** `fineweb-2` continua a base; **Common Corpus entra como braço do Gate T2**,
   não como troca. A pergunta a medir é se procedência melhor vem com bpb pior, e por quanto.
3. **Português:** o nosso, sem alternativa neste lote — e é o único idioma para o qual o lote inteiro
   não oferece nada com licença limpa.
4. **Código:** The Stack **não entra** enquanto o conflito de reprodutibilidade não for resolvido.
   Alternativa a triar: o `OpenSource` do Common Corpus (GitHub, sob a mesma declaração de licença
   livre), que não tem o ToU repassável.
5. **OpusTrainer:** copiar a **ideia** de currículo, não a dependência. É MIT e é código.

---

## 6. A regra que este lote confirma

⭐ **Campo de licença vazio, gate de aceite e rótulo permissivo são três coisas diferentes, e
nenhuma das três é uma licença.** Das 13 fontes, **quatro** pareciam adotáveis pelo rótulo ou pela
fama e caíram na leitura do texto — CulturaX (vazio), Ultra-FineWeb (auto-contraditório),
Multilingual-PD (vazio), openculture (não existe). Nenhuma delas daria erro em lugar nenhum: o
download funciona, o corpus treina, o modelo sai.

É a mesma família de todo o resto deste projeto — **nada reclama** — aplicada à procedência em vez
de à medição.
