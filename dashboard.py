from ast import IsNot
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import geopandas
from datetime import datetime


st.set_page_config( layout ='wide')

st.title('House Rocket Company')

st.markdown('Welcome to House Rocket Data Analysis')

st.header('Load data')

# read data
# Lê direto da memória ram em vez do disco, permitindo que a saída seja mutavel
@st.cache(allow_output_mutation=True)
def get_data(path):
    data = pd.read_csv(path)
    data['date']=pd.to_datetime(data['date'])

    return data

def get_geofile( url ):
    geofile = geopandas.read_file( url )
    return geofile

def set_feature( data ):
    data['price_m2'] = data['price'] / data['sqft_lot']
    return data
    
def overview_data( data ):
    f_attributes = st.sidebar.multiselect('Enter columns', data.columns)
    f_zipcode = st.sidebar.multiselect('Enter zipcode:', data['zipcode'].unique())
    st.title('Data Overview')

    if (f_zipcode != []) & (f_attributes != []):
        data = data.loc[data['zipcode'].isin(f_zipcode), f_attributes]

    elif (f_zipcode != []) & (f_attributes == []):
        data = data.loc[data['zipcode'].isin(f_zipcode),:]

    elif (f_zipcode == []) & (f_attributes != []):
        data = data.loc[:, f_attributes]

    else:
        data = data.copy()

    st.dataframe(data.head())

    # determinar a largura das colunas (ordenadamente)
    c1 , c2 = st.columns((1,1))

    # Average metrics

    df1 = data[['id','zipcode']].groupby('zipcode').count().reset_index()

    df2 = data[['price','zipcode']].groupby('zipcode').mean().reset_index()

    df3 = data[['sqft_living','zipcode']].groupby('zipcode').mean().reset_index()

    df4 = data[['price_m2','zipcode']].groupby('zipcode').mean().reset_index()

    # dar um merge para juntar os df : qd quero garantir que o valor seja similar ao da outra coluna

    m1 = pd.merge(df1,df2, on = 'zipcode', how = 'inner')
    m2 = pd.merge(m1,df3, on='zipcode',how = 'inner')
    df = pd.merge(m2, df4, on='zipcode',how= 'inner')

    df.columns = ['ZIPCODE','TOTAL HOUSES','PRICE','SQRT_LIVING','PRICE/m2']

    # com dataframe consigo ajustar tamanhos

    c1.header('Average Values')
    c1.dataframe(df, height = 600)

    # Statistic Descriptive
    num_attributes = data.select_dtypes( include = ['int64','float64'])

    media = pd.DataFrame( num_attributes.apply(np.mean))
    mediana = pd.DataFrame( num_attributes.apply(np.median))
    std = pd.DataFrame( num_attributes.apply(np.std))

    max_ = pd.DataFrame( num_attributes.apply(np.max))
    min_ = pd.DataFrame( num_attributes.apply(np.min))

    df1 = pd.concat([max_, min_, media, mediana, std], axis= 1).reset_index()

    df1.columns = ['attributes','max','min','mean','median','std']

    c2.header('Descriptive Analysis')
    c2.dataframe(df1, height = 800)

    return None

def portfolio_density( data, geofile):
    
    st.title('Region Overview')

    c1,c2 = st.columns((1,1))
    c1.header('Porfolio Density')

    df = data.copy()

    # Base Map - Folium

    density_map = folium.Map( location = [data['lat'].mean(), 
                                        data['long'].mean()],
                                        default_zoom_start=15)


    marker_cluster = MarkerCluster().add_to(density_map)

    for name, row in df.iterrows():
        folium.Marker([row['lat'], row['long']],
            popup= 'Sold R${0} on: {1}. Features: {2} sqft, {3} bedrooms, {4} bathrooms, year built: {5}'.format(row['price'],
                                                                                                                row['date'],
                                                                                                                row['sqft_living'],
                                                                                                                row['bedrooms'],
                                                                                                                row['bathrooms'],
                                                                                                                row['yr_built'] )).add_to(marker_cluster)
    with c1:
        folium_static(density_map)

    # Region Price Map
    c2.header( 'Price Density' )

    df = data[['price','zipcode']].groupby( 'zipcode').mean().reset_index()

    df.columns=['ZIP','PRICE']

    #df = df.sample(10)

    geofile = geofile[geofile['ZIP'].isin(df['ZIP'].tolist())]

    region_price_map = folium.Map( location = [data['lat'].mean(), 
                                        data['long'].mean()],
                                        default_zoom_start=15)

    region_price_map.choropleth(data = df,
                                geo_data = geofile,
                                columns = ['ZIP','PRICE'],
                                key_on = 'feature.properties.ZIP',
                                fill_color = 'YlOrRd',
                                fill_opacity = 0.7,
                                line_opacity = 0.2,
                                legend_name = 'AVG PRICE')

    with c2:
        folium_static( region_price_map )

    return None

def commercial_distribution(data):
   
    st.sidebar.title( 'Commercial Options' )
    st.title( 'Commercial Attributes' )

    # ------------ Average Price per Year

    # filters
    min_year_built = int(data['yr_built'].min())
    max_year_built = int(data['yr_built'].max())

    st.sidebar.subheader( 'Select Max Year Built' )
    f_year_built = st.sidebar.slider( 'Year Built', min_year_built, max_year_built, min_year_built)

    st.header( 'Average Price per Year built' )

    # Data selection

    df = data.loc[data['yr_built'] < f_year_built]

    df = data[['yr_built','price']].groupby('yr_built').mean().reset_index()

    # plot 

    fig = px.line( df, x = 'yr_built', y = 'price')

    st.plotly_chart( fig, use_container_width = True)

    # ------------ Average Price per Day
    st.header( 'Average Price per day' )
    st.sidebar.subheader( 'Select Max Date')

    # filters

    s_min_date = datetime.strftime(data['date'].min(), '%Y-%m-%d')
    s_max_date = datetime.strftime(data['date'].max(), '%Y-%m-%d')


    min_date = datetime.strptime(s_min_date, '%Y-%m-%d')
    max_date = datetime.strptime(s_max_date, '%Y-%m-%d')

    f_date = st.sidebar.slider( 'Date', min_date, max_date, min_date)

    # data filtering

    data['date'] = pd.to_datetime(data['date'])
    df = data.loc[data['date'] < f_date]

    df = df[['date', 'price']].groupby('date').mean().reset_index()

    # plot 

    fig = px.line( df, x = 'date', y = 'price' )

    st.plotly_chart( fig, use_container_width = True)


    #================================= Histograms
    st.header( 'Price Distribution' )
    st.sidebar.subheader( 'Select Max Price' )

    # filter
    min_price = int(data['price'].min())
    max_price = int(data['price'].max())
    avg_price = int(data['price'].mean())

    f_price = st.sidebar.slider( 'Price', min_price, max_price, avg_price)

    df = data.loc[data['price'] < f_price]

    # data plot
    fig= px.histogram( df, x='price', nbins = 50)
    st.plotly_chart( fig, use_container_width = True)

    return None


def attributes_distribution(data):
 
    st.sidebar.title( 'Attributes Options')
    st.title( 'House Attributes')

    # filters
    f_bedrooms = st.sidebar.selectbox( 'Max number of bedrooms', data['bedrooms'].sort_values().unique())

    f_bathrooms = st.sidebar.selectbox( 'Max number of bathrooms', data['bathrooms'].sort_values().unique())

    c1, c2 = st.columns(2)

    # House por bedrooms
    c1.header( 'Houses per bedrooms')
    df = data[data['bedrooms'] < f_bedrooms]
    fig = px.histogram( df, x ='bedrooms', nbins=19)
    st.plotly_chart( fig, use_container_width= True)

    # House per bathrooms
    c2.header( 'Houses per bathrooms')
    df = data[data['bathrooms'] < f_bathrooms]
    fig = px.histogram( df, x ='bathrooms', nbins=19)
    st.plotly_chart( fig, use_container_width= True)


    # other filters
    f_floors = st.sidebar.selectbox( 'Max number of floors', data['floors'].sort_values().unique())

    f_waterview = st.sidebar.checkbox( 'Only Houses with waterview')

    c1,c2 = st.columns(2)

    # House per floors
    c1.header( 'Houses per floor' )
    df = data[data['floors'] < f_floors]

    fig = px.histogram( df, x ='floors', nbins=19)
    st.plotly_chart( fig, use_container_width= True)

    # House per water view
    if f_waterview:
        df = data[data['waterfront'] == 1]

    else:
        df = data.copy()

    fig = px.histogram( df, x='waterfront', nbins= 10)
    c2.plotly_chart( fig, use_container_width = True)

    return None

if __name__ == '__main__':
    # ETL
    # data extraction
    path = 'datasets/kc_house_data.csv'
    url = 'https://opendata.arcgis.com/datasets/83fc2e72903343aabff6de8cb445b81c_2.geojson'

    data = get_data(path)
    geofile = get_geofile(url)

    # transformation
    data = set_feature(data)

    overview_data(data)

    portfolio_density( data, geofile )

    commercial_distribution(data)

    attributes_distribution(data)







