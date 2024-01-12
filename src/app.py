from dash import Dash, html,dcc, Input, Output
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.express as px
import pymongo
import json
import sys

SURVEY_NAME = 'Survey1'

with open('credentials.json') as json_file:
    creds = json.load(json_file)

atlas_conn_str = f"mongodb+srv://{creds['User']}:{creds['Password']}@{creds['Cluster']}.gu6rrz5.mongodb.net/?retryWrites=true&w=majority"
survey_fields = eval(creds['Fields'])

def get_nps_survey_responses(survey):
    try:
        client = pymongo.MongoClient(atlas_conn_str)
    except pymongo.errors.ConfigurationError:
        print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
        sys.exit(1)

    NPSResponsesDB = client.NPSResponsesDB 
    survey_collection = NPSResponsesDB[survey]

    survey_data_docs = []
    for doc in survey_collection.find():
        survey_data_docs.append(doc)

    survey_data_df = pd.DataFrame(survey_data_docs)[survey_fields]
    return survey_data_df

nps_data = get_nps_survey_responses(SURVEY_NAME)

total_responses = nps_data.shape[0]

condition_detractors = (nps_data['Score'] >= 1) & (nps_data['Score'] <= 6)
filter_detractors = nps_data[condition_detractors]
detractors = len(filter_detractors)

condition_detractors = (nps_data['Score'] >= 1) & (nps_data['Score'] <= 6)
filter_detractors = nps_data[condition_detractors]
detractors = len(filter_detractors)

condition_passive = (nps_data['Score'] >= 7) & (nps_data['Score'] <= 8)
filter_passive = nps_data[condition_passive]
passives = len(filter_passive)

condition_promo = (nps_data['Score'] >= 9) & (nps_data['Score'] <= 10)
filter_promo = nps_data[condition_promo]
promoters = len(filter_promo)

nps_score = round(((promoters - detractors) / total_responses) * 100, 2)

nps_data['Category'] = ''
nps_data.loc[condition_detractors, 'Category'] = 'detractors'
nps_data.loc[condition_passive, 'Category'] = 'passive'
nps_data.loc[condition_promo, 'Category'] = 'promoters'

nps_data['Month'] = nps_data['Date'].apply(lambda x : x.split('-')[1])
nps_data.drop('Date', axis='columns')
nps_data.sort_values('Month', inplace=True)

nps_data['NPS-over-time'] = 0
for mo in nps_data['Month'].unique():
    nps_data.loc[nps_data['Month'] == mo, 'NPS-over-time'] = 1 / (nps_data['Month'] == mo).sum()

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def score_color(nps_score):
    if nps_score <= 6:
        return '#c61236'
    elif nps_score >= 9:
        return '#07da63'
    else:
        return '#fd8c3e'

def generate_card(nps_score, review):
    return html.Div(
        dbc.Card(
            dbc.CardBody([
                html.H5(f"Score: {nps_score}", className="card-title", 
                        style={'color': score_color(nps_score)}),
                html.P(review, className="card-text")
            ])
        ),
        style={'margin-bottom': '10px', 'padding-left': '20px', 'padding-right': '20px'}
    )

nps_over_time_fig = px.bar(nps_data, x="Month", y="NPS-over-time", color='Category', color_discrete_sequence= ['#c61236','#fd8c3e','#07da63',])

nps_over_time_fig.update_layout(
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
)

nps_over_time_fig.update_traces(marker_line_width=0)

pie_chart_figure = px.pie(values=[promoters, passives, detractors], 
                          names=['Promoters', 'Passives', 'Detractors'],
                          color_discrete_sequence= ['#c61236','#fd8c3e','#07da63',],
                          title="Categories Distribution")

pie_chart_figure.update_traces(
    textinfo='percent+label', 
    marker=dict(line=dict(color='white', width=2)),
    hoverinfo='label+percent',
    textfont=dict(color='white')
)

pie_chart_figure.update_layout(
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
)

dcc.Graph(
    figure=pie_chart_figure
)

app.layout = dbc.Container([
    html.H1("NPS Responses", className="text-center my-4", style={'color': 'white'}),

  dbc.Row([
        dbc.Col([
            html.H4("Total Responses", className="text-center", style={'color': '#1870d5'}),
            html.H5(f"{total_responses}", className="text-center", style={'color': 'white'}),
            html.H4("NPS Score", className="text-center", style={'color': '#1870d5', 'margin-top': '20px'}),
            html.H5(f"{nps_score}%", className="text-center", style={'color': 'white'})
        ], width=3),
        dbc.Col([
            html.H4("Promoters", className="text-center", style={'color': '#07da63'}),
            html.H5(f"{promoters}", className="text-center", style={'color': 'white'})
        ], width=3),
        dbc.Col([
            html.H4("Passive", className="text-center", style={'color': '#fd8c3e'}),
            html.H5(f"{passives}", className="text-center", style={'color': 'white'})
        ], width=3),

        dbc.Col([
            html.H4("Detractors", className="text-center", style={'color': '#c61236'}),
            html.H5(f"{detractors}", className="text-center", style={'color': 'white'})
        ], width=3),

    ], justify="center"),

    html.Div([
        dcc.Graph(
            figure=nps_over_time_fig
        )
    ], style={'width': '48%', 'display': 'inline-block'}),  

    html.Div([
        dcc.Graph(
            figure=pie_chart_figure
        )
    ], style={'width': '48%', 'display': 'inline-block'}),

    # dcc.Graph(
    #     figure=nps_over_time_fig
    # ),

    # dcc.Graph(
    #     figure=pie_chart_figure
    # ),

    html.P("Filter responses by entering a minimum and maximum score:", 
           className="text-center", style={'color': 'white', 'margin-top': '20px'}),
    
    dbc.Row([
        dbc.Col([
            dcc.Input(id='min-score', type='number', placeholder='Min Score', value=1, 
                      style={'marginRight': '100px', 'width': '100px'}),
            dcc.Input(id='max-score', type='number', placeholder='Max Score', value=10, 
                      style={'width': '100px'})
        ], width=4, className="offset-md-4 text-center")
    ], style={'margin-bottom': '20px'}),

    html.Div(id='response-cards', style={'overflowY': 'scroll', 'height': '400px'})
], fluid=True, style={'backgroundColor': '#010203'} )


@app.callback(
    Output('response-cards', 'children'),
    [Input('min-score', 'value'), Input('max-score', 'value')]
)
def update_cards(min_score, max_score):
    if min_score is None:
        min_score = 1
    if max_score is None:
        max_score = 10
    filtered_data = nps_data[(nps_data['Score'] >= min_score) & (nps_data['Score'] <= max_score)]
    return [generate_card(row['Score'], row['Review']) for index, row in filtered_data.iterrows()]

if __name__ == '__main__':
    app.run(debug=True)
