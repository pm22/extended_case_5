import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import dash_table
from sqlalchemy import create_engine
import psycopg2
import os
my_passwd = os.environ.get('DB_USER_PASSWORD')

#df = pd.read_csv('aggr.csv', parse_dates=['Entry time'])

engine = create_engine('postgresql://nps_demo_user:my_passwd@nps-demo-instance.cyjpgo7cbnay.us-east-2.rds.amazonaws.com/nps_demo_db')
df = pd.read_sql("SELECT * from aggr", engine.connect(), parse_dates=('OCCURRED_ON_DATE',))

app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/uditagarwal/pen/oNvwKNP.css', 'https://codepen.io/uditagarwal/pen/YzKbqyV.css'])

app.layout = html.Div(children=[
    html.Div(
            children=[
                html.H2(children="Bitcoin Leveraged Trading Backtest Analysis", className='h2-title'),
            ],
            className='study-browser-banner row'
    ),
    html.Div(
        className="row app-body",
        children=[
            html.Div(
                className="twelve columns card",
                children=[
                    html.Div(
                        className="padding row",
                        children=[
                            html.Div(
                                className="two columns card",
                                children=[
                                    html.H6("Select Exchange",),
                                    dcc.RadioItems(
                                        id="exchange-select",
                                        options=[
                                            {'label': label, 'value': label} for label in df['Exchange'].unique()
                                        ],
                                        value=df['Exchange'][0],
                                        labelStyle={'display': 'inline-block'}
                                    )
                                ]
                            ),
                            html.Div(
                                    className="two columns card",
                                    children=[
                                        html.H6("Select Laverage",),
                                        dcc.RadioItems(
                                            id="leverage-select",
                                            options=[
                                                {'label': label, 'value': label} for label in df['Margin'].unique()
                                            ],
                                            value=df['Margin'][0],
                                            labelStyle={'display': 'inline-block'}
                                        )
                                    ]
                            ),
                            html.Div(
                                    className="three columns card",
                                    children=[
                                        dcc.DatePickerRange(
                                            id='date-range-select',
                                            start_date=df['Entry time'].min(), 
                                            end_date=df['Entry time'].max(),
                                            display_format='MMM YY'
                                        )
                                    ]
                            ),
                            html.Div(
                                id="strat-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-returns", className="indicator_value"),
                                    html.P('Strategy Returns', className="twelve columns indicator_text"),
                                ]
                            ),
                            html.Div(
                                id="market-returns-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="market-returns", className="indicator_value"),
                                    html.P('Market Returns', className="twelve columns indicator_text"),
                                ]
                            ),
                            html.Div(
                                id="strat-vs-market-div",
                                className="two columns indicator pretty_container",
                                children=[
                                    html.P(id="strat-vs-market", className="indicator_value"),
                                    html.P('Strategy vs. Market Returns', className="twelve columns indicator_text"),
                                ]
                            )
                        ]
                )
        ]),
        html.Div(
            className="twelve columns card",
            children=[
                dcc.Graph(
                    id="monthly-chart",
                    figure={
                        'data': []
                    }
                )
            ]
        ),
        html.Div(
                className="padding row",
                children=[
                    html.Div(
                        className="six columns card",
                        children=[
                            dash_table.DataTable(
                                id='table',
                                columns=[
                                    {'name': 'Number', 'id': 'Number'},
                                    {'name': 'Trade type', 'id': 'Trade type'},
                                    {'name': 'Exposure', 'id': 'Exposure'},
                                    {'name': 'Entry balance', 'id': 'Entry balance'},
                                    {'name': 'Exit balance', 'id': 'Exit balance'},
                                    {'name': 'Pnl (incl fees)', 'id': 'Pnl (incl fees)'},
                                ],
                                style_cell={'width': '50px'},
                                style_table={
                                    'maxHeight': '450px',
                                    'overflowY': 'scroll'
                                },
                            )
                        ]
                    ),
                    dcc.Graph(
                        id="pnl-types",
                        className="six columns card",
                        figure={}
                    )
                ]
            ),
            html.Div(
                className="padding row",
                children=[
                    dcc.Graph(
                        id="daily-btc",
                        className="six columns card",
                        figure={}
                    ),
                    dcc.Graph(
                        id="balance",
                        className="six columns card",
                        figure={}
                    )
                ]
            )
        ]
    )        
])
                            
@app.callback(
    [dash.dependencies.Output('date-range-select', 'start_date'), dash.dependencies.Output('date-range-select', 'end_date')],
    [dash.dependencies.Input('exchange-select', 'value')]
) 
def update_date(value):
    dff_date = df.copy()
    dff_date = dff_date[dff_date['Exchange'] == value]
    
    return dff_date['Entry time'].min(),dff_date['Entry time'].max() 

def filter_df(dff, exchange, margin, start_date, end_date):
    dff['YearMonth'] =pd.to_datetime(dff['Entry time'].map(lambda x: "{}-{}".format(x.year, x.month)))
    return dff[(dff['Exchange'] == exchange) & (dff['Margin'] == margin) & (dff['Entry time'] >= start_date) & (dff['Entry time'] < end_date)]

def calc_returns_over_month(dff):
    out = []
    
    for name, group in dff.groupby('YearMonth'):
        exit_balance = group.head(1)['Exit balance'].values[0]
        entry_balance = group.tail(1)['Entry balance'].values[0]
        monthly_return = (exit_balance*100 / entry_balance)-100
        out.append({
            'month': name,
            'entry': entry_balance,
            'exit': exit_balance,
            'monthly_return': monthly_return
        })
    return out

def calc_returns_over_day(dff):
    dff['Day'] =pd.to_datetime(dff['Entry time'].map(lambda x: "{}-{}-{}".format(x.year, x.month,x.day)))
    out = []
    for name, group in dff.groupby('Day'):
        exit_balance = group.head(1)['Exit balance'].values[0]
        entry_balance = group.tail(1)['Entry balance'].values[0]
        btc_price = group.head(1)['BTC Price'].values[0]
        out.append({
            'day': name,
            'entry': entry_balance,
            'exit': exit_balance,
            'btc_price': btc_price
        })
    return out

def calc_btc_returns(dff):
    btc_start_value = dff.tail(1)['BTC Price'].values[0]
    btc_end_value = dff.head(1)['BTC Price'].values[0]
    btc_returns = (btc_end_value * 100/ btc_start_value)-100
    return btc_returns

def calc_strat_returns(dff):
    start_value = dff.tail(1)['Exit balance'].values[0]
    end_value = dff.head(1)['Entry balance'].values[0]
    returns = (end_value * 100/ start_value)-100
    return returns

@app.callback(
    [
        dash.dependencies.Output('monthly-chart', 'figure'),
        dash.dependencies.Output('market-returns', 'children'),
        dash.dependencies.Output('strat-returns', 'children'),
        dash.dependencies.Output('strat-vs-market', 'children'),
    ],
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),

    )
)
def update_monthly(exchange, leverage, start_date, end_date):
    df2 = df.copy()
    dff = filter_df(df2, exchange, leverage, start_date, end_date)
    data = calc_returns_over_month(dff)
    btc_returns = calc_btc_returns(dff)
    strat_returns = calc_strat_returns(dff)
    strat_vs_market = strat_returns - btc_returns
    
    return {
        'data': [
            go.Candlestick(
                open=[each['entry'] for each in data],
                close=[each['exit'] for each in data],
                x=[each['month'] for each in data],
                low=[each['entry'] for each in data],
                high=[each['exit'] for each in data]
            )
        ],
        'layout': {
            'title': 'Overview of Monthly performance'
        }
    }, f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'      

@app.callback(
    dash.dependencies.Output('table', 'data'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_table(exchange, leverage, start_date, end_date):
    dff_table = df.copy()
    dff_table = filter_df(dff_table, exchange, leverage, start_date, end_date)
    return dff_table.to_dict('records')  

@app.callback(
    dash.dependencies.Output('pnl-types', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_bar_chart(exchange, leverage, start_date, end_date):
    dff_bar = df.copy()
    dff_bar = filter_df(dff_bar, exchange, leverage, start_date, end_date)
    
    short=dff_bar[dff_bar['Trade type']=='Short']    
    short_data = go.Bar(
                x=short['Entry time'], 
                y=short['Pnl (incl fees)'], 
                name='Short' 
                )
    
    long=dff_bar[dff_bar['Trade type']=='Long']
    long_data = go.Bar(
                x=long['Entry time'], 
                y=long['Pnl (incl fees)'], 
                name='Long' 
                )
    
    return {'data': [short_data, long_data],
            'layout': go.Layout(title='PnL vs Trade type',height= 500)}

@app.callback(
    dash.dependencies.Output('daily-btc', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_btc(exchange, leverage, start_date, end_date):
    dff_btc = df.copy()
    dff_btc = dff_btc[(dff_btc['Entry time'] >= start_date) & (dff_btc['Entry time'] < end_date)]
    data=calc_returns_over_day(dff_btc)
        
    return {'data': [
                go.Scatter(
                    x=[each['day'] for each in data], 
                    y=[each['btc_price'] for each in data]
                    )
                ],
            'layout': go.Layout(title='BTC Price',height= 500)}  

@app.callback(
    dash.dependencies.Output('balance', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_balance(exchange, leverage, start_date, end_date):
    dff_btc = df.copy()
    dff_btc = filter_df(dff_btc, exchange, leverage, start_date, end_date)
    
    return {'data': [
                go.Scatter(
                    x=dff_btc['Entry time'],
                    y = dff_btc['Exit balance']+dff_btc['Pnl (incl fees)']
                    )
                ],
            'layout': go.Layout(title='Balance',height= 500)}  


if __name__ == "__main__":
    app.run_server(debug=True)