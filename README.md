# Banzai Radar — Guia de Instalação

## 1. Instalar Python

1. Acesse: https://python.org/downloads
2. Baixe **Python 3.13** (botão amarelo grande)
3. Na instalação, marque ✅ **"Add Python to PATH"** antes de clicar em Install
4. Após instalar, abra o **Prompt de Comando** (Win+R → cmd) e confirme:
   ```
   python --version
   ```
   Deve mostrar `Python 3.13.x`

---

## 2. Baixar o projeto

**Se você usa o GitHub Desktop (mais fácil):**
1. Instale: https://desktop.github.com
2. Clone este repositório pela interface gráfica

**Ou pelo terminal:**
```bash
git clone https://github.com/SEU_USUARIO/banzai-radar.git
cd banzai-radar
```

---

## 3. Instalar dependências

No terminal, dentro da pasta do projeto:
```bash
pip install -r requirements.txt
```

---

## 4. Inicializar o banco de dados

```bash
python db/models.py
```
Deve aparecer: `✅ Banco inicializado em: data/radar.db`

---

## 5. Adicionar as primeiras cartas para monitorar

Rode a API e adicione cartas via POST:
```bash
uvicorn api.main:app --reload
```
Acesse: http://localhost:8000/docs  
Use o endpoint `POST /api/cards` para cadastrar cartas com a URL do TCGPlayer.

**Exemplo de carta:**
- name: `Portgas D. Ace`
- set_code: `OP-05`
- game: `OPTCG`
- tcg_url: *(URL da carta no TCGPlayer)*
- rarity: `SEC`

---

## 6. Testar o scraper manualmente

```bash
python collect.py
```

---

## 7. Configurar coleta automática no GitHub Actions

1. Suba o projeto para um repositório no GitHub
2. O arquivo `.github/workflows/scrape.yml` já configura tudo
3. A coleta roda automaticamente 3x por dia (09h, 15h e 21h BRT)
4. Para rodar manualmente: GitHub → Actions → "Coleta de Preços" → Run workflow

---

## Estrutura do projeto

```
banzai-radar/
├── api/
│   └── main.py          ← API FastAPI (endpoints do dashboard)
├── analyzer/
│   └── momentum.py      ← Cálculo de spike, momentum e oportunidades
├── db/
│   └── models.py        ← Schema do banco SQLite
├── scraper/
│   └── tcgplayer.py     ← Coleta de preços no TCGPlayer
├── .github/workflows/
│   └── scrape.yml       ← Agendamento automático (GitHub Actions)
├── collect.py           ← Job principal de coleta
├── requirements.txt
└── data/
    └── radar.db         ← Banco gerado automaticamente (não versionar)
```

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/radar` | Todas as cartas rankeadas por momentum |
| GET | `/api/radar?game=OPTCG` | Filtrado por jogo |
| GET | `/api/watchlist` | Cartas na watchlist |
| POST | `/api/watchlist/{card_id}` | Adicionar à watchlist |
| DELETE | `/api/watchlist/{card_id}` | Remover da watchlist |
| GET | `/api/opportunities` | Lojas com preço abaixo do spike |
| GET | `/api/events` | Calendário de eventos |
| GET | `/api/stats` | KPIs do dashboard |
| POST | `/api/cards` | Cadastrar nova carta |

Documentação interativa disponível em: http://localhost:8000/docs
