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

# --- PERSISTENCIA NATIVA DEL ESTADO GLOBAL ---
# Inicializar variables de estado en la sesión para evitar borrados por fragmentos o refrescos
if 'xsp_930' not in st.session_state:
    st.session_state.xsp_930 = None
if 'vix1d_930' not in st.session_state:
    st.session_state.vix1d_930 = None
if 'em_call_930' not in st.session_state:
    st.session_state.em_call_930 = None
if 'em_put_930' not in st.session_state:
    st.session_state.em_put_930 = None
if 'fecha_guardada' not in st.session_state:
    st.session_state.fecha_guardada = None

# Función para calcular Movimiento Esperado y strikes
def calcular_em(precio, vix):
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    return movimiento_puntos, em_call, em_put

# Función limpia para obtener datos en tiempo real de Yahoo Finance (Evita MultiIndex)
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

# Obtener fecha y hora actual en Nueva York de manera global
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
fecha_hoy_str = hora_ny.strftime("%Y-%m-%d")
hora_actual_str = hora_ny.strftime("%H:%M:%S")

# Control de reinicio diario automático: si cambia el día, limpiamos la apertura anterior
if st.session_state.fecha_guardada != fecha_hoy_str:
    st.session_state.xsp_930 = None
    st.session_state.vix1d_930 = None
    st.session_state.em_call_930 = None
    st.session_state.em_put_930 = None
    st.session_state.fecha_guardada = fecha_hoy_str

# Barra lateral informativa y controles manuales
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Resetear Apertura Manualmente"):
        st.session_state.xsp_930 = None
        st.session_state.vix1d_930 = None
        st.session_state.em_call_930 = None
        st.session_state.em_put_930 = None
        st.rerun()
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# --- CAPTURA EN TIEMPO REAL AL PASAR LAS 9:30 AM ---
# Obtenemos los precios actuales del mercado en el hilo principal
xsp_actual, vix1d_actual = obtener_datos_actuales()

if xsp_actual and vix1d_actual:
    # Si ya es hora de apertura o más tarde, y aún no hemos congelado los valores de hoy...
    if hora_ny.time() >= time(9, 30) and st.session_state.xsp_930 is None:
        st.session_state.xsp_930 = xsp_actual
        st.session_state.vix1d_930 = vix1d_actual
        _, em_call_fijo, em_put_fijo = calcular_em(xsp_actual, vix1d_actual)
        st.session_state.em_call_930 = em_call_fijo
        st.session_state.em_put_930 = em_put_fijo

# Verificar si la apertura ya quedó fijada y guardada en memoria
apertura_fijada = st.session_state.xsp_930 is not None

# Bloque 1: Apertura de Mercado (Estructura fija protegida fuera del fragmento dinámico)
st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
if apertura_fijada:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XSP Apertura", f"${st.session_state.xsp_930:.2f}")
    col2.metric("VIX1D Apertura", f"{st.session_state.vix1d_930:.2f}%")
    col3.metric("EM0call (Techo 🔺)", f"{st.session_state.em_call_930:.0f}")
    col4.metric("EM0put (Suelo 🔻)", f"{st.session_state.em_put_930:.0f}")
else:
    st.warning(f"⏳ Esperando que el mercado abra (09:30 AM NY) para fijar los valores iniciales. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

st.markdown("---")

# Bloque 2 dinámico: Usamos el fragmento puramente para renderizar y actualizar el Tiempo Real cada 60 segundos
@st.fragment(run_every=60)
def render_live_data(fijado):
    # Volvemos a pedir datos frescos para la actualización minuto a minuto en vivo
    xsp_act, vix_act = obtener_datos_actuales()

    if xsp_act and vix_act:
        _, em_call_act, em_put_act = calcular_em(xsp_act, vix_act)

        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_act:.2f}")
        col2_act.metric("VIX1D Actual", f"{vix_act:.2f}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen utilizando los datos de sesión globales estables del hilo principal
        if fijado:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [st.session_state.xsp_930, st.session_state.vix1d_930, st.session_state.em_call_930, st.session_state.em_put_930],
                "Actual": [xsp_act, vix_act, em_call_act, em_put_act],
                "Diferencia": [
                    round(xsp_act - st.session_state.xsp_930, 2), 
                    round(vix_act - st.session_state.vix1d_930, 2), 
                    int(em_call_act - st.session_state.em_call_930), 
                    int(em_put_act - st.session_state.em_put_930)
                ]
            })
            st.table(df_comp)

# Lanzamos el proceso recurrente pasando el booleano de control
render_live_data(apertura_fijada)
