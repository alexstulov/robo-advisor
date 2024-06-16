from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import okama as ok
import os

app = Flask(__name__)
app.secret_key = os.urandom(12)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(10))
    description = db.Column(db.String(100))
    initial_balance = db.Column(db.Double)
    tickers = db.Column(db.String(100)) # Sample string with tickers: "ASDF@@20;;QWER@@30;;ZXCV@@40;;RTYU@@10"
    monthly_cash_flow = db.Column(db.Double)
    rebalance_frequency = db.Column(db.String(10))
    discount_rate = db.Column(db.Double)

    def __init__(self, name, description, initial_balance, tickers, monthly_cash_flow, rebalance_frequency, discount_rate):
        self.name = name
        self.description = description
        self.initial_balance = initial_balance
        self.tickers = tickers
        self.monthly_cash_flow = monthly_cash_flow
        self.rebalance_frequency = rebalance_frequency
        self.discount_rate = discount_rate

    def parse_asset_weights(self, input):
        if not len(input):
            return {
                'ticker': '',
                'weight': ''
            }
        asset_tuple = input.split('@@')
        return {
            'ticker': asset_tuple[0],
            'weight': float(asset_tuple[1])
        }
    
    def get_tickers_list(self):
        return list(map(self.parse_asset_weights, self.tickers.split(';;')))
    
    def get_beautiful_tickers(self):
        def beautify(weighted_ticker):
            if not len(weighted_ticker['ticker']):
                return ""
            return f"{weighted_ticker['ticker']} ({weighted_ticker['weight']})"
        assets = self.get_tickers_list()
        return ', '.join(list(map(beautify, assets)))
    
    def join_asset_weights(self, tuple):
        return tuple['ticker'] + '@@' + str(tuple['weight'])

    def set_tickers(self, assets):
        asset_lines = list(map(self.join_asset_weights, assets))
        self.tickers = ';;'.join(asset_lines)
        

@app.route('/')
def Index():
    portfolios = db.session.query(Portfolio).all()

    return render_template('index.html.jinja', portfolios=portfolios)

@app.route('/view/<id>')
def view(id):
    portfolio = db.session.query(Portfolio).get(id)

    return render_template('view.html.jinja', portfolio=portfolio)

@app.route('/add', methods = ['GET', 'POST'])
def insert():
    if request.method == 'GET':
        return render_template('add.html.jinja')

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        initial_balance = request.form['initial_balance']
        monthly_cash_flow = request.form['monthly_cash_flow']
        rebalance_frequency = request.form['rebalance_frequency']

        portfolio = Portfolio(name, description, initial_balance, '', monthly_cash_flow, rebalance_frequency, 0)
        db.session.add(portfolio)
        db.session.commit()

        flash("Portfolio Added Successfully")

        return redirect(url_for('Index'))
    
@app.route('/update/<id>', methods = ['GET', 'POST']) 
def update(id):
    portfolio = db.session.query(Portfolio).get(id)
    if request.method == 'GET':
        return render_template('update.html.jinja', portfolio=portfolio)
    
    if request.method == 'POST':
        portfolio.name = request.form['name']
        portfolio.description = request.form['description']
        portfolio.initial_balance = request.form['initial_balance']
        portfolio.monthly_cash_flow = request.form['monthly_cash_flow']
        portfolio.rebalance_frequency = request.form['rebalance_frequency']

        db.session.commit()
        flash('Portfolio Updated Successfully')

        return redirect(url_for('Index'))
    
@app.route('/delete/<id>/', methods = ['GET', 'POST'])
def delete(id):
    portfolio = db.session.query(Portfolio).get(id)
    name = portfolio.name
    db.session.delete(portfolio)
    db.session.commit()
    flash(f"Portfolio \"f{name}\" Deleted Successfully")

    return redirect(url_for('Index'))

@app.route('/get-assets', methods=['POST'])
def get_assets_route():
    query = request.json
    assets = ok.search(query['data'])
    return assets.to_json(orient='records')

@app.route('/manage-assets/<id>', methods = ['GET', 'POST'])
def manage_assets(id):
    portfolio = db.session.get(Portfolio, id)
    assets = portfolio.get_tickers_list()
    if request.method == 'GET':
        return render_template('manage-assets.html.jinja', portfolio=portfolio, assets=assets)
    if request.method == 'POST':
        weighted_tickers = {}
        # TODO: we rely here on field order as in form, which may cause breaking errors
        for name, value in request.form.items():
            ticker = name.split('asset-ticker-')
            weight = name.split('asset-weight-')
            if len(ticker) == 2:
                asset = {
                    'ticker': value
                }
                weighted_tickers[ticker[1]] = asset
            else:
                weighted_tickers[weight[1]]['weight'] = value
        portfolio.set_tickers(weighted_tickers.values())
        db.session.commit()
        flash(f'Portfolio #{portfolio.id} Assets Updated Successfully')

        return redirect(url_for('Index'))

@app.route('/generate-report', methods = ['POST'])
def generate_report():
    if (request.method == 'POST'):
        data = request.json['data']
        def getPortfolio(id):
            return db.session.get(Portfolio, id)
        portfolios = map(getPortfolio, data['portfolios'])
        start_date = data['start_date']
        end_date = data['end_date']
        ok_portfolios = []
        for portfolio in portfolios:
            tickers = []
            weights = []
            assets = portfolio.get_tickers_list()
            for asset in assets:
                tickers.append(asset['ticker'])
                weights.append(asset['weight'] / 100)
            discount_rate = 0
            if (portfolio.discount_rate > 0):
                discount_rate = portfolio.discount_rate
            ok_portfolio = ok.Portfolio(
                    tickers,
                    first_date=start_date,
                    last_date=end_date,
                    ccy="RUB",
                    weights=weights,
                    rebalancing_period=portfolio.rebalance_frequency,
                    initial_amount=portfolio.initial_balance,
                    cashflow=portfolio.monthly_cash_flow,
                    discount_rate=discount_rate,
                    symbol=portfolio.name
                )
            ok_portfolios.append(ok_portfolio)
        def prepare_data(portfolio):
            return {
                'timeseries': portfolio.dcf.wealth_index.to_json(orient='columns'),
                'statistics': portfolio.describe().to_json(orient='columns', default_handler=str)
            }
        return {'portfolios': list(map(prepare_data, ok_portfolios))}

if __name__ == '__main__':
    app.run(debug=True)
