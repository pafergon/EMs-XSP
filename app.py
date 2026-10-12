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

# Función para obtener datos en tiempo real de Yahoo Finance (Último precio cotizado)
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

# NUEVA FUNCIÓN INFAVIBLE: Extrae la primera barra del gráfico de un minuto de hoy
@st.cache_data(ttl=300)  # Cachea por 5 minutos para no saturar la API
def obtener_apertura_desde_historico_un_minuto():
    try:
        t_xsp = yf.Ticker('^XSP')
        t_vix = yf.Ticker('^VIX1D')
        
        # Solicitamos el gráfico de 1 minuto para el día de hoy
        df_xsp = t_xsp.history(period="1d", interval="1m")
        df_vix = t_vix.history(period="1d", interval="1m")
        
        if df_xsp.empty or df_vix.empty:
            return None, None
        
        # Localizar y extraer de forma segura el valor 'Open' de la PRIMERA barra registrada del día (09:30 AM NY)
        # Usamos .iloc[0] para asegurar que sea el primer dato de la mañana sin importar los husos horarios
        xsp_open = float(df_xsp['Open'].iloc[0])
        vix_open = float(df_vix['Open'].iloc[0])
        
        return round(xsp_open, 2), round(vix_open, 2)
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

# --- ASIGNACIÓN DE VALORES DE APERTURA ---
xsp_930, vix1d_930, em_call_930, em_put_930 = None, None, None, None
em_pts_930 = None # Línea añadida para guardar los puntos de apertura
apertura_fijada = False

# Si el mercado ya abrió (09:30 AM NY o posterior), extraemos la primera barra del gráfico de hoy
if hora_ny.time() >= time(9, 30):
    xsp_930, vix1d_930 = obtener_apertura_desde_historico_un_minuto()
    if xsp_930 and vix1d_930:
        em_pts_930, em_call_930, em_put_930 = calcular_em(xsp_930, vix1d_930) # Modificado para capturar em_pts_930
        apertura_fijada = True

# Bloque 1: Apertura de Mercado (Fijo y protegido en el hilo principal)
st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
if apertura_fijada:
    st.metric("Movimiento Esperado Inicial (Puntos sin redondeo)", f"±{em_pts_930:.4f}") # Línea añadida
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XSP Apertura", f"${xsp_930:.2f}")
    col2.metric("VIX1D Apertura", f"{vix1d_930:.2f}%")
    col3.metric("EM0call (Techo 🔺)", f"{em_call_930:.0f}")
    col4.metric("EM0put (Suelo 🔻)", f"{em_put_930:.0f}")
else:
    st.warning(f"⏳ Esperando que el mercado abra y consolide la primera barra de las 09:30 AM NY. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

st.markdown("---")

# Bloque 2 dinámico: Fragmento aislado para actualizar el tiempo real cada 60 segundos
@st.fragment(run_every=60)
def render_live_data(xsp_ref, vix_ref, call_ref, put_ref, fijado):
    xsp_act, vix_act = obtener_datos_actuales()

    if xsp_act and vix_act:
        em_pts_act, em_call_act, em_put_act = calcular_em(xsp_act, vix_act) # Modificado para capturar em_pts_act

        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        st.metric("Movimiento Esperado Actual (Puntos sin redondeo)", f"±{em_pts_act:.4f}") # Línea añadida
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_act:.2f}")
        col2_act.metric("VIX1D Actual", f"{vix_act:.2f}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen utilizando las referencias estáticas reales pasadas por argumento
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

# Ejecutar el fragmento pasándole los datos de la primera barra del día
render_live_data(xsp_930, vix1d_930, em_call_930, em_put_930, apertura_fijada)
    
