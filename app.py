from json import load
import streamlit as st  # pip install streamlit
import pandas as pd  # pip install pandas openpyxl
# import plotly.express as px  # pip install plotly-express
import os.path
from mercadolibre_por_precio import run
from IPython.display import Image, HTML

FILENAME = "por_precio_output.csv"


# ---- READ CSV ----
@st.cache(suppress_st_warning=True)
def load_data():
    try:
        df = pd.read_csv(FILENAME)
        return df
    except:
        run()
        return load_data()


def refresh_data():
    if os.path.isfile(FILENAME):
        os.remove(FILENAME)  # Remove previous file
        run()
    return load_data()


# Add HTML link into field
def convert(row):
    return '<a href="{}" target="_blank">{}</a>'.format(row['links'], row.links)


# --- STREAMLIT PAGE ---
st.set_page_config(page_title="Wish House Dashboard", page_icon=":bar_chart:", layout="wide")

# ---- MAINPAGE ----
st.title(":bar_chart: Wish House Dashboard")
st.markdown("""---""")

data_load_state = st.text('Cargando datos...')
df = load_data()
data_load_state.text("")

if df is not None:
    # ---- SIDEBAR ----
    st.sidebar.header("Filtros:")
    currencies = df['currency'].drop_duplicates()
    currency = st.sidebar.selectbox('Seleccione moneda: ', currencies)
    price_1, price_2 = st.sidebar.slider("Seleccione rango de precios:", int(df["price"].min()), int(df["price"].max()), [int(df["price"].min()), int(df["price"].max())], step=10000)
    
    # location = st.sidebar.multiselect(
    #     "Seleccione Ubicacion:",
    #     options=df["location"].unique(),
    #     default=df["location"].unique()
    # )

    location = st.sidebar.text_input("Escriba palabra para buscar sobre ubicacion: ")
    title = st.sidebar.text_input("Escriba palabra para buscar sobre descripcion: ")
    # TODO: Filtrar por ambientes

    if st.button("Refrescar datos"):
        data_load_state = st.text('Cargando datos...')
        df = refresh_data()
        data_load_state.text("")
        
    st.markdown("""####""")

    # Filter selections from Dataframe
    df_selection = df.query("price >= @price_1 & price <= @price_2")
    
    # Filter location
    df_selection = df_selection[df_selection['location'].str.contains('(?i)' + location)] # The (?i) in the regex pattern tells the re module to ignore case.

    # Filter title
    df_selection = df_selection[df_selection['title'].str.contains('(?i)' + title)] # The (?i) in the regex pattern tells the re module to ignore case.

    # Format values
    df_selection.set_index('ID')
    #df_selection['price'] = df['currency'] + ' ' + df['price'].apply('{:,}'.format)
    df_selection['image_html'] = df['image'].str.replace('(.*)', '<img src="\\1" style="max-height:124px;max-width: 200px;"></img>')
    df_selection['links'] = df.apply(convert, axis=1)

    # Add column names
    filtered = df_selection.sort_values(by=['price'])
    filtered = filtered[['ID', 'title', 'location', 'price', 'image_html', 'links']].set_index('ID')
    filtered.columns = ['Nombre', 'Ubicacion', 'Precio', 'Foto', 'Link']

    # Display result
    # st.write('\r\n' + '** result:' + ' **')
    st.write(filtered.to_html(escape=False), unsafe_allow_html=True)
    st.write('\r\n')
    st.write('\r\n')

    # ---- HIDE STREAMLIT STYLE ----
    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """

    st.markdown(hide_st_style, unsafe_allow_html=True)


### TODO: Favoritos?
