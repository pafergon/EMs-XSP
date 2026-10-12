import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
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
    # Fórmula estándar: Spot * (VIX1D / 100) / sqrt(365)
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    return movimiento_puntos, em_call, em_put

# Función para obtener datos en tiempo real (último precio disponible)
def obtener_datos_actuales():
    try:
        tickers = yf.Tickers('^XSP ^VIX1D')
        xsp_price = tickers.tickers['^XSP'].fast_info['last_price']
        vix1d_price = tickers.tickers['^VIX1D'].fast_info['last_price']
        return round(xsp_price, 2), round(vix1d_price, 2)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Yahoo Finance (Tiempo Real): {e}")
        return None, None

# NUEVA FUNCIÓN: Obtiene el valor histórico exacto de las 09:30 AM NY de hoy
def obtener_datos_apertura_historicos():
    try:
        tz_ny = pytz.timezone('America/New_York')
        hoy_ny = datetime.now(tz_ny).date()
        mañana_ny = hoy_ny + timedelta(days=1)
        
        # Descargamos datos históricos de 1 minuto para el día de hoy
        # (YFinance requiere start/end en formato string YYYY-MM-DD)
        df_xsp = yf.download('^XSP', start=hoy_ny.strftime('%Y-%m-%d'), end=mañana_ny.strftime('%Y-%m-%d'), interval='1m', progress=False)
        df_vix = yf.download('^VIX1D', start=hoy_ny.strftime('%Y-%m-%d'), end=mañana_ny.strftime('%Y-%m-%d'), interval='1m', progress=False)
        
        if df_xsp.empty or df_vix.empty:
            return None, None

        # Convertir el índice temporal a la zona horaria de NY
        df_xsp.index = df_xsp.index.tz_convert('America/New_York')
        df_vix.index = df_vix.index.tz_convert('America/New_York')

        # Buscamos la fila que corresponda exactamente a las 09:30
        apertura_xsp = df_xsp.between_time('09:30', '09:31')
        apertura_vix = df_vix.between_time('09:30', '09:31')

        if not apertura_xsp.empty and not apertura_vix.empty:
            # Extraemos el precio 'Open' de la barra de las 9:30 AM
            xsp_930 = float(apertura_xsp['Open'].iloc[0])
            vix_930 = float(apertura_vix['Open'].iloc[0])
            return round(xsp_930, 2), round(vix_930, 2)
            
        return None, None
    except Exception as e:
        # Falla silenciosa o advertencia si el mercado aún no ha generado velas históricas
        return None, None

# Obtener hora actual en Nueva York
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
hora_actual_str = hora_ny.strftime("%H:%M:%S")

with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Forzar Recarga Completa"):
        st.rerun()
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# Fragmento dinámico que se refresca cada 60 segundos
@st.fragment(run_every=60)
def render_live_data():
    # 1. Obtener datos actuales en vivo
    xsp_actual, vix1d_actual = obtener_datos_actuales()

    if xsp_actual and vix1d_actual:
        # Calcular métricas del estado actual
        _, em_call_act, em_put_act = calcular_em(xsp_actual, vix1d_actual)

        # 2. Buscar datos de la apertura de forma persistente (Historial)
        xsp_930, vix1d_930 = obtener_datos_apertura_historicos()
        
        # Inicializamos variables para el bloque de apertura
        apertura_fijada = False
        em_call_930, em_put_930 = None, None

        if xsp_930 and vix1d_930:
            _, em_call_930, em_put_930 = calcular_em(xsp_930, vix1d_930)
            apertura_fijada = True

        # --- DISEÑO DE LA INTERFAZ ---
        
        # Bloque 1: Apertura de Mercado (09:30 AM NY)
        st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
        if apertura_fijada:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("XSP Apertura", f"${xsp_930}")
            col2.metric("VIX1D Apertura", f"{vix1d_930}%")
            col3.metric("EM0call (Techo 🔺)", f"{em_call_930:.0f}")
            col4.metric("EM0put (Suelo 🔻)", f"{em_put_930:.0f}")
        else:
            st.warning(f"⏳ Esperando a que las velas de las 09:30 AM NY estén consolidadas en el histórico. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

        st.markdown("---")

        # Bloque 2: Mercado en Tiempo Real
        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_actual}")
        col2_act.metric("VIX1D Actual", f"{vix1d_actual}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen de desviaciones si la apertura está fijada a través del histórico
        if apertura_fijada:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [xsp_930, vix1d_930, em_call_930, em_put_930],
                "Actual": [xsp_actual, vix1d_actual, em_call_act, em_put_act],
                "Diferencia": [
                    round(xsp_actual - xsp_930, 2), 
                    round(vix1d_actual - vix1d_930, 2), 
                    int(em_call_act - em_call_930), 
                    int(em_put_act - em_put_930)
                ]
            })
            st.table(df_comp)

# Ejecutar el fragmento dinámico
render_live_data()
