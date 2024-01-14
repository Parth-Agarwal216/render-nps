from dash import Dash, html,dcc, Input, Output
import pandas as pd
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pymongo
import json
import sys
from collections import Counter

import base64
from io import BytesIO
from wordcloud import WordCloud

SURVEY_NAME = 'Maple_Finance_Gateway_0'

with open('credentials.json') as json_file:
    creds = json.load(json_file)

atlas_conn_str = creds['Atlas-Conn-Str']
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

condition_detractors = (nps_data['nps-score'] >= 1) & (nps_data['nps-score'] <= 6)
filter_detractors = nps_data[condition_detractors]
detractors = len(filter_detractors)

condition_detractors = (nps_data['nps-score'] >= 1) & (nps_data['nps-score'] <= 6)
filter_detractors = nps_data[condition_detractors]
detractors = len(filter_detractors)

condition_passive = (nps_data['nps-score'] >= 7) & (nps_data['nps-score'] <= 8)
filter_passive = nps_data[condition_passive]
passives = len(filter_passive)

condition_promo = (nps_data['nps-score'] >= 9) & (nps_data['nps-score'] <= 10)
filter_promo = nps_data[condition_promo]
promoters = len(filter_promo)

nps_score = round(((promoters - detractors) / total_responses) * 100, 2)

nps_data['Category'] = ''
nps_data.loc[condition_detractors, 'Category'] = 'detractors'
nps_data.loc[condition_passive, 'Category'] = 'passive'
nps_data.loc[condition_promo, 'Category'] = 'promoters'

nps_data['Month'] = nps_data['date'].apply(lambda x : x.split('-')[1])
nps_data.sort_values('date', inplace=True)
nps_data.drop('date', axis='columns')

nps_data['NPS-over-time'] = 0
for mo in nps_data['Month'].unique():
    nps_data.loc[nps_data['Month'] == mo, 'NPS-over-time'] = 1 / (nps_data['Month'] == mo).sum()

## Word Cloud ##

pos_reviews = " ".join(word for word in nps_data.loc[condition_promo, 'review'])
neg_reviews = " ".join(word for word in nps_data.loc[condition_passive | condition_detractors, 'review'])

pos_word_cloud = WordCloud(collocations = False, background_color = '#010203',
                        width = 512, height = 256, min_font_size=16).generate(pos_reviews)

neg_word_cloud = WordCloud(collocations = False, background_color = '#010203',
                        width = 512, height = 256, min_font_size=16).generate(neg_reviews)

pos_word_cloud_img2 = pos_word_cloud.to_image()
neg_word_cloud_img2 = neg_word_cloud.to_image()

with BytesIO() as buffer:
    pos_word_cloud_img2.save(buffer, 'png')
    pos_word_cloud_img = base64.b64encode(buffer.getvalue()).decode()

with BytesIO() as buffer:
    neg_word_cloud_img2.save(buffer, 'png')
    neg_word_cloud_img = base64.b64encode(buffer.getvalue()).decode()

## -------------- ##

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

def score_color(nps_score):
    if nps_score <= 6:
        return '#c61236'
    elif nps_score >= 9:
        return '#07da63'
    else:
        return '#fd8c3e'
    
def sentiment_color(sentiment):
    if sentiment == 'negative':
        return '#c61236'
    elif sentiment == 'positive':
        return '#07da63'
    else:
        return '#fd8c3e'

def generate_card(nps_score, review, sentiment):
    return html.Div(
        dbc.Card(
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.H5(f"Score: {nps_score}", className="card-title", 
                                    style={'color': score_color(nps_score)}), 
                            width="auto", align="start"),
                    dbc.Col(html.H6(f"Sentiment: {sentiment}", className="card-sentiment", 
                                    style={'color': sentiment_color(sentiment)}), 
                            width="auto", align="end")
                ], justify="between"),  
                html.P(review, className="card-text")
            ])
        ),
        style={'margin-bottom': '10px', 'padding-left': '20px', 'padding-right': '20px'}
    )

## NPS over time plots ##

nps_over_time_fig = px.bar(nps_data, x="Month", y="NPS-over-time", color='Category', color_discrete_sequence= ['#c61236','#fd8c3e','#07da63',])

nps_over_time_fig.update_layout(
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
)

nps_over_time_fig.update_traces(marker_line_width=0)

## Product Rebuy ##

percent_rebuy_yes = round(100 * nps_data['rebuy'].sum()/len(nps_data))
br = pd.DataFrame({'Yes/No':['Yes', 'No'], 'Percentage_Customers_Buy_Again':[percent_rebuy_yes, 100 - percent_rebuy_yes], 'Response':['Yes/No', 'Yes/No']})

product_yn_bar = px.bar(br, y="Response", x="Percentage_Customers_Buy_Again", orientation='h', color='Yes/No',
                         color_discrete_sequence= ['green', 'red'], text=br['Percentage_Customers_Buy_Again'].apply(lambda x: f'{x}%'))

product_yn_bar.update_layout(
    height=200,
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False),
    title_x=0.5,
    showlegend=False,
)

## NPS Pie Chart ##

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

## Checkboxes Responses ##

pos_fts_list = []
neg_fts_list = []

for idx in nps_data.index:
    if nps_data.loc[idx, 'sentiment'] == 'positive':
        pos_fts_list.extend(eval(nps_data.loc[idx, 'checkbox_fts']))
    else:
        neg_fts_list.extend(eval(nps_data.loc[idx, 'checkbox_fts']))

pos_counter = Counter(pos_fts_list)
pos_counter = dict(pos_counter.most_common(5))

neg_counter = Counter(neg_fts_list)
neg_counter = dict(neg_counter.most_common(5))

positive_aspects_bar = px.bar(pd.DataFrame({'Well Performing Aspects' : pos_counter.keys(), '#Responses' : pos_counter.values()}), 
                                x='Well Performing Aspects', y='#Responses', color_discrete_sequence=['green'])

negative_aspects_bar = px.bar(pd.DataFrame({'Poorly Performing Aspects' : neg_counter.keys(), '#Responses' : neg_counter.values()}), 
                                x='Poorly Performing Aspects', y='#Responses', color_discrete_sequence=['#E34234'])

positive_aspects_bar.update_layout(
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
    title_x=0.5,
    title=dict(text="Well Performing Aspects", font=dict(size=30)),
)

negative_aspects_bar.update_layout(
    paper_bgcolor='#010203',
    plot_bgcolor='#010203',
    font=dict(color='white'),
    title_x=0.5,
    title=dict(text="Poorly Performing Aspects", font=dict(size=30)),
)

## -------------- ##

app.layout = dbc.Container([
    html.H1("NPS Responses", className="text-center my-4", style={'color': 'white'}),

  dbc.Row([
        dbc.Row([
            dbc.Col([
                html.H4("Total Responses", className="text-center", style={'color': '#1870d5'}),
                html.H5(f"{total_responses}", className="text-center", style={'color': 'white'}),
                # html.H4("NPS Score", className="text-center", style={'color': '#1870d5', 'margin-top': '20px'}),
                # html.H5(f"{nps_score}%", className="text-center", style={'color': 'white'})
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
            ], width=3)
        ], justify='center'),

        dbc.Row([
            dbc.Col([
                html.H4("NPS Score", className="text-center", style={'color': '#1870d5', 'margin-top': '60px'}),
                html.H5(f"{nps_score}%", className="text-center", style={'color': 'white'})
            ], width=3),

            dbc.Col([
                html.Div([
                    dcc.Graph(
                        figure=product_yn_bar
                    )
                ])
            ], width=6),
        ], justify='between')

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


    html.Div(children=[
                    html.H4("Positive Feedback Wordcloud", style={'color': 'white', 'text-align': 'center'}),
                    html.Img(src="data:image/png;base64," + pos_word_cloud_img),
                ], style={'width': '48%', 'display': 'inline-block', 'text-align': 'center', 'margin': 'auto'}),

    html.Div(children=[
                    html.H4("Negative Feedback Wordcloud", style={'color': 'white', 'text-align': 'center'}),
                    html.Img(src="data:image/png;base64," + neg_word_cloud_img)
                ], style={'width': '48%', 'display': 'inline-block', 'text-align': 'center', 'margin': 'auto'}),

    html.Div(
        [
            html.Br(),
            html.Br(),
            html.Br(),
        ]
    ),

    html.Div([
        dcc.Graph(
            figure=positive_aspects_bar
        )
    ], style={'width': '48%', 'display': 'inline-block', 'margin':10}),  

    html.Div([
        dcc.Graph(
            figure=negative_aspects_bar
        )
    ], style={'width': '48%', 'display': 'inline-block', 'margin':10}),
    
    html.Div(
        [
            html.Br(),
            html.Br(),
        ]
    ),

    html.Div([
        dbc.Row([
            
            dbc.Col(
                html.Div([
                    html.P("Filter responses by min and max score:", 
                        className="text-center", style={'color': 'white'}),
                    html.Div([
                        dcc.Input(id='min-score', type='number', placeholder='Min Score', 
                                style={'marginRight': '10px', 'width': '100px'}),
                        dcc.Input(id='max-score', type='number', placeholder='Max Score',
                                style={'marginLeft': '10px', 'width': '100px'}),
                    ], style={'display': 'flex', 'justifyContent': 'center', 'marginTop': '10px'}),
                ], style={'textAlign': 'center'}),
                width=6
            ),
            
            dbc.Col(
                html.Div([
                    html.P("Filter responses by sentiment:", 
                        className="text-center", style={'color': 'white'}),
                    dcc.Dropdown(
                        id='sentiment', placeholder = 'Sentiment',
                        options=[
                            {'label': 'Positive', 'value': 'positive'},
                            {'label': 'Neutral', 'value': 'neutral'},
                            {'label': 'Negative', 'value': 'negative'},
                        ],
                        style={'width': '140px', 'margin': '10px auto'},
                    ),
                ], style={'textAlign': 'center'}),
                width=6
            ),
        ], style={'marginBottom': '20px'})
    ]),

    html.Div(id='response-cards', style={'overflowY': 'scroll', 'height': '400px'})
], fluid=True, style={'backgroundColor': '#010203'} )


@app.callback(
    Output('response-cards', 'children'),
    [Input('min-score', 'value'), Input('max-score', 'value'), Input('sentiment', 'value')]
)
def update_cards(min_score, max_score, sentiment):
    if min_score is None:
        min_score = 1
    if max_score is None:
        max_score = 10
    filtered_data = nps_data[(nps_data['nps-score'] >= min_score) & (nps_data['nps-score'] <= max_score)]
    if sentiment != None:
        filtered_data = filtered_data[(filtered_data['sentiment']) == sentiment]
    return [generate_card(row['nps-score'], row['review'], row['sentiment']) for index, row in filtered_data.iterrows()]

if __name__ == '__main__':
    app.run(debug=True)
