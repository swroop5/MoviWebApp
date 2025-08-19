# MoviWebApp

A Flask + SQLAlchemy web app that lets users maintain a list of favorite movies.
Metadata is fetched from the OMDb API.

## Features
- Create/select users
- List/add/update/delete movies per user
- Fetch title, director, year, and poster from OMDb
- Simple templates and CSS styling
- SQLite storage under `./data`

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OMDB_API_KEY

python app.py
# open http://127.0.0.1:5000/
```

## Project Structure
```
MoviWebApp/
├── app.py
├── data_manager.py
├── models.py
├── omdb.py
├── requirements.txt
├── .env.example
├── data/
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── movies.html
    ├── 404.html
    └── 500.html
```

## Notes
- OMDb free tier is rate-limited; handle failures gracefully.
- Titles are enforced unique *per user* via a DB constraint.
- You can adjust forms/templates as desired; this is a minimal starter.