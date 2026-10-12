import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import os

# Configuración de la página
st.set_page_config(
    page_title="XSP & VIX1D Expected Move",
    page_icon="📈",
    layout="wide"
)

st.title("📊 Monitor de Movimiento Esperado (XSP & VIX1D)")
st.caption("Actualización automática minuto a minuto | Zona Horaria: Nueva York (EST/EDT)")

# Archivo local para persistencia de datos (evita pérdidas por F5 o caídas de sesión)
ARCHIVO_PERSISTENCIA = "apertura_dia.csv"

# Inicializar variables de estado en la sesión
if 'xsp_930' not in st.session_state:
    st.session_state.xsp_930 = None
if 'vix1d_930' not in st.session_state:
    st.session_state.vix1d_930 = None
if 'em_call_930' not in st.session_state:
    st.session_state.em_call_930 = None
if 'em_put_930' not in st.session_state:
    st.session_state.em_put_930 = None

# Función para calcular Movimiento Esperado y strikes
def calcular_em(precio, vix):
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    return movimiento_puntos, em_call, em_put

# Función para obtener datos en tiempo real de Yahoo Finance
def obtener_datos():
    try:
        tickers = yf.Tickers('^XSP ^VIX1D')
        xsp_price = tickers.tickers['^XSP'].fast_info['last_price']
        vix1d_price = tickers.tickers['^VIX1D'].fast_info['last_price']
        return round(xsp_price, 2), round(vix1d_price, 2)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Yahoo Finance: {e}")
        return None, None

# Obtener fecha y hora actual en Nueva York
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
fecha_hoy_str = hora_ny.strftime("%Y-%m-%d")
hora_actual_str = hora_ny.strftime("%H:%M:%S")

# LÓGICA DE PERSISTENCIA INFAVIBLE: Cargar datos guardados si existen para el día de hoy
if os.path.exists(ARCHIVO_PERSISTENCIA):
    try:
        df_persistido = pd.read_csv(ARCHIVO_PERSISTENCIA)
        if not df_persistido.empty and df_persistido['fecha'].iloc[0] == fecha_hoy_str:
            st.session_state.xsp_930 = float(df_persistido['xsp_930'].iloc[0])
            st.session_state.vix1d_930 = float(df_persistido['vix1d_930'].iloc[0])
            st.session_state.em_call_930 = float(df_persistido['em_call_930'].iloc[0])
            st.session_state.em_put_930 = float(df_persistido['em_put_930'].iloc[0])
    except Exception:
        pass

# Botón manual en la barra lateral para resetear el estado y borrar el archivo persistente
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Resetear Valores de Apertura"):
        if os.path.exists(ARCHIVO_PERSISTENCIA):
            os.remove(ARCHIVO_PERSISTENCIA)
        st.session_state.xsp_930 = None
        st.session_state.vix1d_930 = None
        st.session_state.em_call_930 = None
        st.session_state.em_put_930 = None
        st.rerun()
    
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# Usamos st.fragment para refrescar cada 60 segundos de forma limpia
@st.fragment(run_every=60)
def render_live_data():
    xsp_actual, vix1d_actual = obtener_datos()

    if xsp_actual and vix1d_actual:
        # Calcular métricas del estado actual (Vivo)
        _, em_call_act, em_put_act = calcular_em(xsp_actual, vix1d_actual)

        # Lógica de congelación instantánea a las 9:30 AM NY en adelante
        hora_apertura = time(9, 30)
        
        # Si ya pasó la hora de apertura y NO tenemos guardados los datos en la sesión
        if hora_ny.time() >= hora_apertura and st.session_state.xsp_930 is None:
            # Capturamos el precio exacto que hay en este instante (la apertura)
            st.session_state.xsp_930 = xsp_actual
            st.session_state.vix1d_930 = vix1d_actual
            st.session_state.em_call_930 = em_call_act
            st.session_state.em_put_930 = em_put_act
            
            # Lo guardamos inmediatamente en un archivo local para sobrevivir a F5/refrescos del navegador
            df_guardar = pd.DataFrame([{
                'fecha': fecha_hoy_str,
                'xsp_930': xsp_actual,
                'vix1d_930': vix1d_actual,
                'em_call_930': em_call_act,
                'em_put_930': em_put_act
            }])
            df_guardar.to_csv(ARCHIVO_PERSISTENCIA, index=False)

        # Determinar si la apertura ya fue fijada (vía memoria o vía archivo persistido)
        apertura_fijada = st.session_state.xsp_930 is not None

        # --- DISEÑO DE LA INTERFAZ ---
        
        # Bloque 1: Apertura de Mercado (9:30 AM)
        st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
        if apertura_fijada:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("XSP Apertura", f"${st.session_state.xsp_930:.2f}")
            col2.metric("VIX1D Apertura", f"{st.session_state.vix1d_930:.2f}%")
            col3.metric("EM0call (Techo 🔺)", f"{st.session_state.em_call_930:.0f}")
            col4.metric("EM0put (Suelo 🔻)", f"{st.session_state.em_put_930:.0f}")
        else:
            st.warning(f"⏳ Esperando a que el mercado abra (09:30 AM NY) para capturar los valores iniciales. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

        st.markdown("---")

        # Bloque 2: Mercado en Tiempo Real
        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_actual:.2f}")
        col2_act.metric("VIX1D Actual", f"{vix1d_actual:.2f}%")
        col1_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col2_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen de desviaciones
        if apertura_fijada:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [st.session_state.xsp_930, st.session_state.vix1d_930, st.session_state.em_call_930, st.session_state.em_put_930],
                "Actual": [xsp_actual, vix1d_actual, em_call_act, em_put_act],
                "Diferencia": [
                    round(xsp_actual - st.session_state.xsp_930, 2), 
                    round(vix1d_actual - st.session_state.vix1d_930, 2), 
                    int(em_call_act - st.session_state.em_call_930), 
                    int(em_put_act - st.session_state.em_put_930)
                ]
            })
            st.table(df_comp)

# Ejecutar el fragmento dinámico
render_live_data()
    
