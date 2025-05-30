import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Configurar página
st.set_page_config(
    page_title="🏠 Wish House Dashboard", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MercadoLibreInmueblesScraper:
    """Scraper optimizado para inmuebles de MercadoLibre Argentina"""
    
    def __init__(self, min_price: str = "200000", max_price: str = "800000", delay: float = 1.0):
        self.min_price = min_price
        self.max_price = max_price
        self.delay = delay
        self.base_url = "https://inmuebles.mercadolibre.com.ar"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error al obtener la página {url}: {e}")
            return None
    
    def extract_meters(self, item) -> Optional[float]:
        """
        Extrae los metros cuadrados del inmueble
        """
        try:
            # Buscar en los atributos de la lista
            attributes = item.find_all('li', {'class': 'poly-attributes-list__bar'})
            for attr in attributes:
                text = attr.get_text(strip=True)
                if 'm² cubiertos' in text or 'm²' in text:
                    meters_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if meters_match:
                        return float(meters_match.group(1))
            
            # Buscar en otros posibles contenedores
            attributes_alt = item.find_all('li', {'class': 'poly-attributes_list__item'})
            for attr in attributes_alt:
                text = attr.get_text(strip=True)
                if 'm²' in text:
                    meters_match = re.search(r'(\d+(?:\.\d+)?)', text)
                    if meters_match:
                        return float(meters_match.group(1))
                        
        except Exception as e:
            logger.warning(f"Error extrayendo metros: {e}")
        
        return None
    
    def extract_product_data(self, item, index: int) -> Optional[Dict]:
        try:
            # Título
            title_elem = item.find('h3', {'class': 'poly-component__title-wrapper'})
            if not title_elem:
                title_elem = item.find('h2', {'class': 'poly-component__title'})
            title = title_elem.get_text(strip=True) if title_elem else "Sin título"
            
            # Moneda
            currency_elem = item.find('span', {'class': 'andes-money-amount__currency-symbol'})
            currency = currency_elem.get_text(strip=True) if currency_elem else "USD"
            
            # Precio
            price_elem = item.find('span', {'class': 'andes-money-amount__fraction'})
            price = 0
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace('.', '').replace(',', '')
                try:
                    price = int(price_text)
                except ValueError:
                    price = 0
            
            # Ubicación
            location_elem = item.find('span', {'class': 'poly-component__location'})
            location = location_elem.get_text(strip=True) if location_elem else "Sin ubicación"
            
            # Metros cuadrados
            meters = self.extract_meters(item)
            
            # Imagen
            img = item.find('img')
            image_url = ""
            if img:
                image_url = img.get('data-src') or img.get('src') or ""
            
            # Link
            link_elem = item.find('a')
            link = ""
            if link_elem and link_elem.get('href'):
                link = urljoin(self.base_url, link_elem['href'])
            
            return {
                'ID': index,
                'title': title,
                'currency': currency,
                'price': price,
                'location': location,
                'meters': meters if meters else 0,
                'image': image_url,
                'links': link
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del producto {index}: {e}")
            return None
    
    def scrape_page(self, url: str, start_index: int) -> List[Dict]:
        products = []
        soup = self.get_soup(url)
        
        if not soup:
            return products
            
        results = soup.find_all('div', {'class': 'andes-card'})
        
        for i, item in enumerate(results):
            product = self.extract_product_data(item, start_index + i + 1)
            if product:
                products.append(product)
        
        return products
    
    def run_scraper(self, max_pages: int = 10):
        """Ejecuta el scraping y retorna lista de productos"""
        all_products = []
        
        # Primera página
        url = f"{self.base_url}/venta/_PriceRange_{self.min_price}USD-{self.max_price}USD"
        products = self.scrape_page(url, 0)
        all_products.extend(products)
        
        # Páginas adicionales
        for page in range(1, max_pages):
            offset = page * 48
            url = f"{self.base_url}/venta/_Desde_{offset + 1}_PriceRange_{self.min_price}USD-{self.max_price}USD"
            products = self.scrape_page(url, len(all_products))
            
            if not products:
                break
                
            all_products.extend(products)
            time.sleep(self.delay)
        
        return all_products

# Funciones auxiliares
@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_data_from_csv(filename: str):
    """Carga datos desde CSV con cache"""
    try:
        if os.path.exists(filename):
            df = pd.read_csv(filename)
            return df
        return None
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
        return None

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y procesa los datos del DataFrame"""
    df = df.copy()
    
    # Limpiar y convertir precio
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['price'] = df['price'].astype(int)
    
    # Limpiar y convertir metros
    df['meters'] = pd.to_numeric(df['meters'], errors='coerce').fillna(0)
    
    # Limpiar otros campos
    df['currency'] = df['currency'].fillna('USD')
    df['image'] = df['image'].fillna('')
    df['links'] = df['links'].fillna('')
    df['location'] = df['location'].fillna('Sin ubicación')
    df['title'] = df['title'].fillna('Sin título')
    
    return df

def scrape_fresh_data(min_price: str, max_price: str) -> pd.DataFrame:
    """Realiza scraping y retorna DataFrame"""
    scraper = MercadoLibreInmueblesScraper(min_price=min_price, max_price=max_price)
    
    with st.spinner('🔍 Scrapeando datos de MercadoLibre...'):
        products = scraper.run_scraper(max_pages=8)
    
    if products:
        df = pd.DataFrame(products)
        df = clean_data(df)
        # Guardar en CSV
        filename = f"inmuebles_{min_price}-{max_price}_output.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        st.success(f"✅ {len(products)} inmuebles encontrados!")
        return df
    else:
        st.error("❌ No se pudieron obtener datos")
        return pd.DataFrame()

def create_image_html(image_url: str) -> str:
    """Crea HTML para mostrar imagen"""
    if not image_url or image_url.startswith('data:'):
        return "📷 Sin imagen"
    return f'<img src="{image_url}" style="max-height:100px;max-width:150px;border-radius:8px;" alt="Property">'

def create_link_html(url: str, text: str = "Ver propiedad") -> str:
    """Crea HTML para enlaces"""
    if not url:
        return "Sin enlace"
    return f'<a href="{url}" target="_blank" style="color:#1f77b4;text-decoration:none;font-weight:bold;">🔗 {text}</a>'

def format_price(price: int, currency: str) -> str:
    """Formatea precio con moneda"""
    return f"{currency} ${price:,.0f}"

def create_plotly_theme():
    """Configuración de tema para gráficos Plotly"""
    return {
        'layout': {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': 'white'},
            'xaxis': {
                'gridcolor': 'rgba(255,255,255,0.2)',
                'linecolor': 'rgba(255,255,255,0.2)',
                'tickcolor': 'rgba(255,255,255,0.2)',
                'title': {'font': {'color': 'white'}}
            },
            'yaxis': {
                'gridcolor': 'rgba(255,255,255,0.2)',
                'linecolor': 'rgba(255,255,255,0.2)',
                'tickcolor': 'rgba(255,255,255,0.2)',
                'title': {'font': {'color': 'white'}}
            },
            'title': {'font': {'color': 'white'}}
        }
    }

# Interfaz principal
def main():
    # Header
    st.title("🏠 Wish House Dashboard")
    st.markdown("### Panel de Control de Inmuebles MercadoLibre")
    st.markdown("---")
    
    # Sidebar - Configuraciones
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Configuración de scraping
        st.subheader("🔍 Parámetros de Búsqueda")
        min_price = st.text_input("Precio mínimo (USD)", value="200000")
        max_price = st.text_input("Precio máximo (USD)", value="800000")
        
        # Botones de acción
        col1, col2 = st.columns(2)
        with col1:
            scrape_new = st.button("🔄 Scraper Nuevo", type="primary")
        with col2:
            load_existing = st.button("📁 Cargar Existente")
    
    # Manejo de datos
    df = None
    filename = f"inmuebles_{min_price}-{max_price}_output.csv"
    
    if scrape_new:
        df = scrape_fresh_data(min_price, max_price)
    elif load_existing:
        df = load_data_from_csv(filename)
        if df is None:
            st.warning("⚠️ No se encontró archivo existente. Ejecutando scraping...")
            df = scrape_fresh_data(min_price, max_price)
        else:
            df = clean_data(df)
    else:
        # Cargar datos existentes si existen
        df = load_data_from_csv(filename)
        if df is not None:
            df = clean_data(df)
    
    if df is None or df.empty:
        st.info("👆 Selecciona una opción en el sidebar para comenzar")
        return
    
    # Sidebar - Filtros
    with st.sidebar:
        st.markdown("---")
        st.subheader("🎛️ Filtros")
        
        # Filtro de moneda
        currencies = df['currency'].unique()
        selected_currency = st.selectbox("💰 Moneda:", currencies)
        
        # Filtro de precio (solo para propiedades con precio > 0)
        df_with_price = df[df['price'] > 0]
        if len(df_with_price) > 0 and df_with_price['price'].max() > df_with_price['price'].min():
            price_range = st.slider(
                "💵 Rango de Precios:",
                int(df_with_price['price'].min()),
                int(df_with_price['price'].max()),
                (int(df_with_price['price'].min()), int(df_with_price['price'].max())),
                step=5000
            )
        else:
            price_range = (0, df['price'].max() if len(df) > 0 else 1000000)
        
        # Filtro de metraje (solo para propiedades con metraje > 0)
        df_with_meters = df[df['meters'] > 0]
        if len(df_with_meters) > 0 and df_with_meters['meters'].max() > df_with_meters['meters'].min():
            meters_range = st.slider(
                "📐 Metraje (m²):",
                int(df_with_meters['meters'].min()),
                int(df_with_meters['meters'].max()),
                (int(df_with_meters['meters'].min()), int(df_with_meters['meters'].max())),
                step=5
            )
        else:
            meters_range = (0, df['meters'].max() if len(df) > 0 else 1000)
        
        # Checkbox para incluir propiedades sin metraje
        include_no_meters = st.checkbox("Incluir propiedades sin metraje especificado", value=True)
        
        # Filtros de texto
        location_filter = st.text_input("📍 Ubicación contiene:", placeholder="Ej: Palermo")
        title_filter = st.text_input("🏠 Descripción contiene:", placeholder="Ej: departamento")
    
    # Aplicar filtros
    df_filtered = df[
        (df['currency'] == selected_currency) &
        (df['price'] >= price_range[0]) &
        (df['price'] <= price_range[1])
    ]
    
    # Filtro de metraje
    if include_no_meters:
        df_filtered = df_filtered[
            ((df_filtered['meters'] >= meters_range[0]) & (df_filtered['meters'] <= meters_range[1])) |
            (df_filtered['meters'] == 0)
        ]
    else:
        df_filtered = df_filtered[
            (df_filtered['meters'] >= meters_range[0]) & (df_filtered['meters'] <= meters_range[1]) & (df_filtered['meters'] > 0)
        ]
    
    if location_filter:
        df_filtered = df_filtered[df_filtered['location'].str.contains(location_filter, case=False, na=False)]
    
    if title_filter:
        df_filtered = df_filtered[df_filtered['title'].str.contains(title_filter, case=False, na=False)]
    
    # Métricas principales
    if not df_filtered.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Propiedades", len(df_filtered))
        
        with col2:
            # Calcular precio promedio solo de propiedades con precio > 0
            df_with_price = df_filtered[df_filtered['price'] > 0]
            if len(df_with_price) > 0:
                avg_price = df_with_price['price'].mean()
                st.metric("💰 Precio Promedio", f"${avg_price:,.0f}")
            else:
                st.metric("💰 Precio Promedio", "N/A")
        
        with col3:
            # Calcular metraje promedio solo de propiedades con metraje > 0
            df_with_meters = df_filtered[df_filtered['meters'] > 0]
            if len(df_with_meters) > 0:
                avg_meters = df_with_meters['meters'].mean()
                st.metric("📐 Metraje Promedio", f"{avg_meters:.0f} m²")
            else:
                st.metric("📐 Metraje Promedio", "N/A")
        
        with col4:
            # Calcular precio por m² solo de propiedades con ambos datos
            df_complete = df_filtered[(df_filtered['price'] > 0) & (df_filtered['meters'] > 0)]
            if len(df_complete) > 0:
                price_per_m2 = (df_complete['price'] / df_complete['meters']).mean()
                st.metric("💵 Precio/m²", f"${price_per_m2:.0f}")
            else:
                st.metric("💵 Precio/m²", "N/A")
    
    # Gráficos
    if not df_filtered.empty and len(df_filtered) > 1:
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Distribución de Precios")
            # Solo graficar propiedades con precio > 0
            df_price_plot = df_filtered[df_filtered['price'] > 0]
            if len(df_price_plot) > 0:
                fig_hist = px.histogram(
                    df_price_plot, 
                    x='price', 
                    nbins=20,
                    title="Distribución de Precios",
                    color_discrete_sequence=['#00d4ff']
                )
                
                # Aplicar tema personalizado
                theme = create_plotly_theme()
                fig_hist.update_layout(**theme['layout'])
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No hay datos de precios para mostrar")
        
        with col2:
            st.subheader("🏠 Precio vs Metraje")
            # Solo graficar propiedades con ambos datos > 0
            df_plot = df_filtered[(df_filtered['meters'] > 0) & (df_filtered['price'] > 0)]
            if len(df_plot) > 0:
                fig_scatter = px.scatter(
                    df_plot,
                    x='meters',
                    y='price',
                    hover_data=['location'],
                    title="Precio vs Metros Cuadrados",
                    color_discrete_sequence=['#ff6b35']
                )
                
                # Aplicar tema personalizado
                theme = create_plotly_theme()
                fig_scatter.update_layout(**theme['layout'])
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("No hay suficientes datos de metraje y precio para mostrar")
    
    # Tabla de resultados
    st.markdown("---")
    st.subheader(f"🏠 Propiedades Encontradas ({len(df_filtered)})")
    
    if not df_filtered.empty:
        # Preparar datos para mostrar
        display_df = df_filtered.copy()
        display_df = display_df.sort_values('price', ascending=False)
        
        # Formatear columnas
        display_df['Precio'] = display_df.apply(lambda x: format_price(x['price'], x['currency']) if x['price'] > 0 else "Consultar", axis=1)
        display_df['Imagen'] = display_df['image'].apply(create_image_html)
        display_df['Enlace'] = display_df['links'].apply(create_link_html)
        display_df['Metraje'] = display_df['meters'].apply(lambda x: f"{x:.0f} m²" if x > 0 else "No especificado")
        
        # Seleccionar columnas para mostrar
        columns_to_show = ['title', 'location', 'Precio', 'Metraje', 'Imagen', 'Enlace']
        final_df = display_df[columns_to_show]
        final_df.columns = ['🏠 Título', '📍 Ubicación', '💰 Precio', '📐 Metraje', '📷 Imagen', '🔗 Link']
        
        # Mostrar tabla con HTML
        st.markdown(
            final_df.to_html(escape=False, index=False, table_id="properties-table"),
            unsafe_allow_html=True
        )
        
        # CSS mejorado para la tabla
        st.markdown("""
        <style>
        #properties-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
            background-color: rgba(255,255,255,0.05);
            border-radius: 10px;
            overflow: hidden;
        }
        #properties-table th, #properties-table td {
            border: 1px solid rgba(255,255,255,0.1);
            padding: 12px;
            text-align: left;
        }
        #properties-table th {
            background-color: rgba(255,255,255,0.1);
            font-weight: bold;
            color: white;
        }
        #properties-table tr:nth-child(even) {
            background-color: rgba(255,255,255,0.02);
        }
        #properties-table tr:hover {
            background-color: rgba(255,255,255,0.05);
        }
        #properties-table td {
            color: rgba(255,255,255,0.9);
        }
        #properties-table a {
            color: #00d4ff !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
    else:
        st.warning("🔍 No se encontraron propiedades con los filtros aplicados")
    
    # Footer
    st.markdown("---")
    st.markdown("*Datos obtenidos de MercadoLibre Argentina*")

# Ejecutar aplicación
if __name__ == "__main__":
    main()