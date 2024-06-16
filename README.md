# Just Another Robo Advisor
Generate portfolio of assets with weights and compare them with Portfolio Wealth Index and some descriptive statistics (CAGR, Mean Return, Risk etc.).

## Deploy and run

Create virtual environment
```
python -m venv .venv 
```

Activate environment every time you start working with project (run the app or manage dependencies)
```sh
(linux) $ source myenv/bin/activate 
(windows) # .\.venv\Scripts\activate 
```

Install dependencies
```py
pip install -r requirements.txt
```

Generate sqlite database
```
python
>>> from app import app, db, Portfolio
>>> app.app_context().push()
>>> db.create_all()
```

Add latest Bootstrap and Icons to `./templates/base.html.jinja` from [Bootstrap](https://getbootstrap.com/docs/5.0/getting-started/download/).

Run with
```
python app.py
```