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

# Inicializar variables de estado para la apertura (9:30 AM)
if 'apertura_fijada' not in st.session_state:
    st.session_state.apertura_fijada = False
if 'xsp_930' not in st.session_state:
    st.session_state.xsp_930 = None
if 'vix1d_930' not in st.session_state:
    st.session_state.vix1d_930 = None
if 'em_call_930' not in st.session_state:
    st.session_state.em_call_930 = None
if 'em_put_930' not in st.session_state:
    st.session_state.em_put_930 = None

# Función para obtener datos en tiempo real de Yahoo Finance
def obtener_datos():
    try:
        # ^XSP (Mini-SPX Options) y ^VIX1D (VIX 1-Day)
        tickers = yf.Tickers('^XSP ^VIX1D')
        xsp_price = tickers.tickers['^XSP'].fast_info['last_price']
        vix1d_price = tickers.tickers['^VIX1D'].fast_info['last_price']
        return round(xsp_price, 2), round(vix1d_price, 2)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Yahoo Finance: {e}")
        return None, None

# Calcular Movimiento Esperado y strikes (Ceil para Call / Floor para Put)
def calcular_em(precio, vix):
    # Fórmula estándar: Spot * (VIX1D / 100) / sqrt(365)
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    
    return movimiento_puntos, em_call, em_put

# Obtener hora actual en Nueva York
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
hora_actual_str = hora_ny.strftime("%H:%M:%S")

# Botón manual en la barra lateral para resetear el estado si es necesario
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Resetear Valores de Apertura"):
        st.session_state.apertura_fijada = False
        st.session_state.xsp_930 = None
        st.session_state.vix1d_930 = None
        st.session_state.em_call_930 = None
        st.session_state.em_put_930 = None
        st.rerun()
    
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# Usamos st.fragment para refrescar solo esta sección de datos cada 60 segundos de forma limpia
@st.fragment(run_every=60)
def render_live_data():
    xsp_actual, vix1d_actual = obtener_datos()

    if xsp_actual and vix1d_actual:
        # Calcular métricas del estado actual (Vivo)
        mov_puntos_act, em_call_act, em_put_act = calcular_em(xsp_actual, vix1d_actual)

        # Lógica de fijación a las 9:30 AM
        hora_apertura = time(9, 30)
        if hora_ny.time() >= hora_apertura and not st.session_state.apertura_fijada:
            st.session_state.xsp_930 = xsp_actual
            st.session_state.vix1d_930 = vix1d_actual
            st.session_state.em_call_930 = em_call_act
            st.session_state.em_put_930 = em_put_act
            st.session_state.apertura_fijada = True

        # --- DISEÑO DE LA INTERFAZ ---
        
        # Bloque 1: Apertura de Mercado (9:30 AM)
        st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
        if st.session_state.apertura_fijada:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("XSP Apertura", f"${st.session_state.xsp_930}")
            col2.metric("VIX1D Apertura", f"{st.session_state.vix1d_930}%")
            col3.metric("EM0call (Techo 🔺)", f"{st.session_state.em_call_930:.0f}")
            col4.metric("EM0put (Suelo 🔻)", f"{st.session_state.em_put_930:.0f}")
        else:
            st.warning(f"⏳ Esperando a que el mercado abra (09:30 AM NY) para fijar los valores iniciales. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

        st.markdown("---")

        # Bloque 2: Mercado en Tiempo Real
        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_actual}")
        col2_act.metric("VIX1D Actual", f"{vix1d_actual}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen de desviaciones si la apertura está fijada
        if st.session_state.apertura_fijada:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [st.session_state.xsp_930, st.session_state.vix1d_930, st.session_state.em_call_930, st.session_state.em_put_930],
                "Actual": [xsp_actual, vix1d_actual, em_call_act, em_put_act],
                "Diferencia": [round(xsp_actual - st.session_state.xsp_930, 2), round(vix1d_actual - st.session_state.vix1d_930, 2), em_call_act - st.session_state.em_call_930, em_put_act - st.session_state.em_put_930]
            })
            st.table(df_comp)

# Ejecutar el fragmento dinámico
render_live_data()
  
