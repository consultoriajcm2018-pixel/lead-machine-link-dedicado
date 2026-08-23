# lead-machine-link-dedicado

Sistema automatizado de pré-venda B2B para link dedicado corporativo com:
- ingestão de leads (CSV e banco);
- qualificação automática por WhatsApp;
- envio complementar por e-mail;
- classificação quente/morno/descartar;
- follow-ups automáticos em 24h e 72h;
- dashboard de métricas em tempo real.

## Executar
```bash
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Consulte `SETUP.md` para configuração completa.

---

## Radar de SUVs em leilão judicial

Segundo projeto neste repositório: agregador de lotes de veículos de
leiloeiros oficiais, com classificação de SUV, filtros e simulação de
parcelamento pela regra do art. 895 do CPC.

```bash
PYTHONPATH=src python3 -m leiloes.cli sync
PYTHONPATH=src python3 -m uvicorn leiloes.api:app --host 0.0.0.0 --port 8000
```

Detalhes em [`RADAR_LEILOES.md`](RADAR_LEILOES.md).

