import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz

# Configuración de la página
st.set_page_config(
    page_title="XSP & VIX1D Expected Move",
    page_icon="📈",
    layout="wide"
)

st.title("📊 Monitor de Movimiento Esperado (XSP & VIX1D)")
st.caption("Actualización automática minuto a minuto | Zona Horaria: Nueva York (EST/EDT)")

# Función para calcular Movimiento Esperado y strikes
def calcular_em(precio, vix):
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    return movimiento_puntos, em_call, em_put

# Función para obtener datos en tiempo real de Yahoo Finance
def obtener_datos_actuales():
    try:
        ticker_xsp = yf.Ticker('^XSP')
        ticker_vix = yf.Ticker('^VIX1D')
        
        xsp_price = ticker_xsp.fast_info['last_price']
        vix1d_price = ticker_vix.fast_info['last_price']
        
        return round(xsp_price, 2), round(vix1d_price, 2)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Yahoo Finance (Tiempo Real): {e}")
        return None, None

# NUEVA FUNCIÓN INFAVIBLE: Obtiene el precio oficial de apertura del mercado de los datos estáticos de Yahoo
@st.cache_data(ttl=3600) # Cacheamos por 1 hora para evitar peticiones repetidas innecesarias
def obtener_valores_apertura_oficiales():
    try:
        ticker_xsp = yf.Ticker('^XSP')
        ticker_vix = yf.Ticker('^VIX1D')
        
        # Extraemos el precio oficial de apertura bursátil asignado por el mercado a las 9:30 AM
        xsp_open = ticker_xsp.info.get('open') or ticker_xsp.fast_info['open']
        
        # Para el VIX1D, si el 'open' de hoy no está consolidado, tomamos el cierre previo o el valor regular de apertura
        vix_open = ticker_vix.info.get('open') or ticker_vix.info.get('previousClose')
        
        if xsp_open and vix_open:
            return round(float(xsp_open), 2), round(float(vix_open), 2)
        return None, None
    except Exception:
        return None, None

# Obtener fecha y hora actual en Nueva York de manera global
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
hora_actual_str = hora_ny.strftime("%H:%M:%S")

# Barra lateral informativa y controles manuales
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Forzar Recarga de Datos"):
        st.cache_data.clear()
        st.rerun()
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# --- OBTENCIÓN DE DATOS DE APERTURA OFICIALES ---
xsp_930, vix1d_930, em_call_930, em_put_930 = None, None, None, None
apertura_fijada = False

# Si ya pasó la hora de la apertura (9:30 AM NY), traemos los datos fijos del "Open" del mercado de hoy
if hora_ny.time() >= time(9, 30):
    xsp_930, vix1d_930 = obtener_valores_apertura_oficiales()
    if xsp_930 and vix1d_930:
        _, em_call_930, em_put_930 = calcular_em(xsp_930, vix1d_930)
        apertura_fijada = True

# Bloque 1: Apertura de Mercado (Estructura Fija con los datos oficiales de Apertura de Yahoo)
st.subheader("🏁 Fijado a la Apertura (09:30 AM NY Oficial)")
if apertura_fijada:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XSP Apertura", f"${xsp_930:.2f}")
    col2.metric("VIX1D Apertura", f"{vix1d_930:.2f}%")
    col3.metric("EM0call (Techo 🔺)", f"{em_call_930:.0f}")
    col4.metric("EM0put (Suelo 🔻)", f"{em_put_930:.0f}")
else:
    st.warning(f"⏳ Esperando que el mercado abra (09:30 AM NY) para fijar los valores iniciales. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

st.markdown("---")

# Bloque 2 dinámico: Fragmento aislado para actualizar el tiempo real cada 60 segundos
@st.fragment(run_every=60)
def render_live_data(xsp_ref, vix_ref, call_ref, put_ref, fijado):
    # Pedimos los precios que cotizan en este preciso instante de forma independiente
    xsp_act, vix_act = obtener_datos_actuales()

    if xsp_act and vix_act:
        _, em_call_act, em_put_act = calcular_em(xsp_act, vix_act)

        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_act:.2f}")
        col2_act.metric("VIX1D Actual", f"{vix_act:.2f}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen utilizando las referencias estáticas reales calculadas al inicio
        if fijado:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [xsp_ref, vix_ref, call_ref, put_ref],
                "Actual": [xsp_act, vix_act, em_call_act, em_put_act],
                "Diferencia": [
                    round(xsp_act - xsp_ref, 2), 
                    round(vix_act - vix_ref, 2), 
                    int(em_call_act - call_ref), 
                    int(em_put_act - put_ref)
                ]
            })
            st.table(df_comp)

# Ejecutar el fragmento pasándole las referencias globales calculadas de la apertura real
render_live_data(xsp_930, vix1d_930, em_call_930, em_put_930, apertura_fijada)
