# Radar de SUVs em leilão judicial

Agrega, em um lugar só, os lotes de veículos publicados por leiloeiros
oficiais, classifica quais são SUV, calcula a parcela pela regra do CPC e
mostra tudo em uma página que abre no celular.

## O que este projeto não faz

Ele **não inventa lote, preço, desconto nem opcional**. Todo campo exibido foi
lido da página pública da origem, e cada card traz o link para conferência.
Quando a origem não informa algo (teto solar, por exemplo), a plataforma
escreve "não informado" em vez de preencher por conta própria.

## A regra de parcelamento, sem marketing

Base legal: **Lei 13.105/2015 (CPC), art. 895**.

| O que se diz por aí | O que a lei diz |
|---|---|
| "48x sem entrada" | Não existe. O art. 895, §1º exige **no mínimo 25% à vista**. |
| "30x sem juros" | Correto quanto aos juros, mas o §2º manda **corrigir monetariamente** as parcelas. |
| "sem análise de crédito" | Correto — mas o §1º exige **caução idônea** sobre bem móvel. |
| "é só dar o lance" | A proposta parcelada **pode perder para uma proposta à vista** (§7º). |

Além do lance, entram no custo: **comissão do leiloeiro** (em geral 5%, à
vista), transferência, e os débitos que o **edital do lote** atribuir ao
arrematante. O edital manda — sempre leia antes.

## Fontes coletadas

| Origem | Endereço |
|---|---|
| Mega Leilões | https://www.megaleiloes.com.br/veiculos |
| Leilões Judiciais | https://www.leiloesjudiciais.com.br/veiculos |

Cada origem é um módulo em `src/leiloes/sources/`. Para somar outro leiloeiro,
basta criar um módulo com `collect()`, `enrich()` e `parse_listing()` e
registrá-lo em `sources/__init__.py`.

## Como rodar

```bash
pip install -r requirements.txt

# 1) coletar os lotes publicados agora
PYTHONPATH=src python3 -m leiloes.cli sync --paginas 30 --detalhes 150

# 2) abrir a interface (celular na mesma rede: http://IP-DA-MAQUINA:8000)
PYTHONPATH=src python3 -m uvicorn leiloes.api:app --host 0.0.0.0 --port 8000
```

O banco fica em `leiloes.db` (mude com a variável `LEILOES_DB`).

## API

| Rota | Para quê |
|---|---|
| `GET /` | Interface web, feita para tela de celular. |
| `GET /api/lotes` | Lista filtrada. Filtros: `idade_max` (padrão 5), `incluir_sem_ano`, `tier`, `uf`, `preco_max`, `preco_min`, `desconto_min`, `teto_solar`, `so_parcelavel`, `excluir_direitos`, `excluir_sucata`, `termo`, `ordem`, `entrada_pct`, `parcelas`. |
| `GET /api/simulacao` | Simulação do art. 895 para um valor. Recusa entrada < 25% e mais de 30 parcelas. |
| `POST /api/sync` | Dispara uma nova coleta. |

## Idade do veículo

O filtro padrão é **no máximo 5 anos de uso**, contados do **ano modelo** que o
anúncio declara (`idade_max=5`, ou `--idade-max 5` na linha de comando).

O leiloeiro escreve o ano de duas formas — `2019/2020` e `19/20` — e vale
sempre o segundo número, o ano modelo. Quando o anúncio **não declara ano**, o
lote fica fora da lista: idade não se deduz por geração do modelo nem por
aparência. Para ver esses casos à parte, use `incluir_sem_ano=true`.

## Sinais de alerta que a plataforma marca sozinha

- **só os direitos, não o veículo** — o lote é o direito aquisitivo.
- **anunciado como sucata/incompleto** — o próprio anúncio diz sucata, motor
  inservível, só lataria, sinistrado.
- **pagamento: somente à vista** — o anúncio nega parcelamento nesse lote.
- **valor do anúncio é lance corrente** — a listagem mostra R$ 1,00 ou valor
  simbólico; o número que vale está na página do lote.
- **ano não declarado** — o anúncio não diz ano modelo, então a idade não pôde
  ser conferida.
- **o selo de desconto repete o texto da origem** — "50% abaixo na 2ª praça" é
  condição futura, não abatimento já aplicado no valor exibido.

## Testes

```bash
PYTHONPATH=src python3 tests/test_leiloes.py
```

Os testes rodam sobre amostras reais das páginas (`tests/fixtures/*.html.gz`),
sem tocar na rede.
