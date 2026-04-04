# Setup

## 1) Preparação
1. Crie e ative um ambiente virtual Python 3.11+.
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Copie `.env.example` para `.env` e preencha credenciais.

## 2) Estrutura de arquivos
- `src/leadmachine/config.py`: configuração.
- `src/leadmachine/models.py`: modelos do banco.
- `src/leadmachine/db.py`: engine/sessão.
- `src/leadmachine/lead_sources.py`: ingestão CSV e banco.
- `src/leadmachine/messaging.py`: envio WhatsApp via Evolution API.
- `src/leadmachine/emailer.py`: envio de e-mail automático.
- `src/leadmachine/classifier.py`: lógica de qualificação.
- `src/leadmachine/workflow.py`: orquestração de pré-venda.
- `src/leadmachine/dashboard.py`: métricas.
- `src/leadmachine/main.py`: API + agendador contínuo.
- `run.py`: execução contínua.

## 3) Execução contínua
```bash
python run.py
```

## 4) Operação
- Importar leads por CSV:
  - `POST /ingest/csv?path=/caminho/leads.csv`
- Importar leads por banco:
  - `POST /ingest/database` com `db_url` e `query`.
- Receber respostas:
  - `POST /webhook/inbound`.
- Dashboard:
  - `GET /dashboard/metrics`.

## 5) Automação sem intervenção manual
- Scheduler interno executa continuamente:
  - disparo de mensagens iniciais;
  - follow-up 24h e 72h;
  - e-mail complementar.

