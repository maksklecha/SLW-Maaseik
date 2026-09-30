# SLW-Maaseik
Gezamenlijke repository voor Tectonic Hackathon ronde 1 - SLW Maaseik

Starter kit: a **Streamlit** chat UI on top of a **LangGraph** graph.

| File | What it is |
|---|---|
| `graph.py` | The "brain": the LangGraph graph (nodes + edges). Change the system prompt / add nodes here. |
| `app.py` | The demo web page the jury sees (Streamlit). |
| `check_setup.py` | Tests that your API key + model work. |
| `.env.example` | Template for your secrets. Copy to `.env`. |

## Setup (every team member, once)

```bash
git clone https://github.com/maksklecha/SLW-Maaseik.git
cd SLW-Maaseik
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then open .env and paste your API key
python check_setup.py              # should print "setup works!"
streamlit run app.py               # opens the app in your browser
```

> Every time you open a new terminal, run `source .venv/bin/activate` again.

## Git workflow during the hackathon

```bash
git pull                     # before you start working
git add <files>              # stage your changes
git commit -m "what you did"
git pull                     # get teammates' work
git push
```

- Pull and push **often** (every 20–30 min).
- Try to work in **different files** to avoid merge conflicts.
- **Never commit `.env`** (it's already in `.gitignore`).
