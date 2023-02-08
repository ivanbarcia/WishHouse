from json import load
import streamlit as st  # pip install streamlit
import pandas as pd  # pip install pandas openpyxl
# import plotly.express as px  # pip install plotly-express
import os.path
from mercadolibre_por_precio import run

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
st.title(":bar_chart: Wish Car Dashboard")
st.markdown("""---""")

data_load_state = st.text('Cargando datos...')
df = load_data()
data_load_state.text("")

if df is not None:
    # ---- SIDEBAR ----
    st.sidebar.header("Filtros:")
    currencies = df['currency'].drop_duplicates()
    currency = st.sidebar.selectbox('Seleccione moneda: ', currencies)
    price_1, price_2 = st.sidebar.slider("Seleccione rango de precios:", int(df["price"].min()), int(df["price"].max()), [int(df["price"].min()), int(df["price"].max())], step=50000)
    
    if st.button("Refrescar datos"):
        data_load_state = st.text('Cargando datos...')
        df = refresh_data()
        data_load_state.text("")
        
    st.markdown("""####""")

    # Filter selections from Dataframe
    df_selection = df.query("price >= @price_1 & price <= @price_2")
    
    # Filter title
    # df_selection = df_selection[df_selection['title'].str.contains('(?i)' + title)] # The (?i) in the regex pattern tells the re module to ignore case.

    df_selection.set_index('ID')
    df_selection['price'] = df['price'].apply('{:,}'.format)
    df_selection['links'] = df.apply(convert, axis=1)

    cars_by_brand = df_selection.count()

    st.bar_chart(cars_by_brand)

    for house in df_selection:
        filtered = house.iloc()
        filtered = filtered.sort_values(by=['price'])
        filtered = filtered[['ID', 'title', 'currency', 'price', 'links']].set_index('ID')
        filtered.columns = ['Nombre', 'Moneda', 'Precio', 'Link']
        # Display result
        st.write('\r\n' + '** result:' + ' **')
        st.write(filtered.head(10).to_html(escape=False), unsafe_allow_html=True)
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
