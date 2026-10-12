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
    movimiento_puntos = precio * (vix / 100) / np.sqrt(365)
    em_call = np.ceil(precio + movimiento_puntos)
    em_put = np.floor(precio - movimiento_puntos)
    return movimiento_puntos, em_call, em_put

# Función para obtener datos en tiempo real de Yahoo Finance
def obtener_datos_actuales():
    try:
        tickers = yf.Tickers('^XSP ^VIX1D')
        xsp_price = tickers.tickers['^XSP'].fast_info['last_price']
        vix1d_price = tickers.tickers['^VIX1D'].fast_info['last_price']
        return round(xsp_price, 2), round(vix1d_price, 2)
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Yahoo Finance (Tiempo Real): {e}")
        return None, None

# Obtener fecha y hora actual en Nueva York de manera global
tz_ny = pytz.timezone('America/New_York')
hora_ny = datetime.now(tz_ny)
fecha_hoy_str = hora_ny.strftime("%Y-%m-%d")
hora_actual_str = hora_ny.strftime("%H:%M:%S")

# NUEVA FUNCIÓN OPTIMIZADA: Descarga solo la primera barra de las 09:30 AM
@st.cache_data(ttl=28800)  # Guarda el resultado en caché durante 8 horas para evitar llamadas redundantes
def obtener_apertura_exacta(fecha_str):
    try:
        # Forzar un rango estrecho para evitar sobrecarga y asegurar la descarga de datos de 1 minuto
        start_date = datetime.strptime(fecha_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        
        # Descarga con estructura explícita para evitar errores de MultiIndex de Pandas
        data_xsp = yf.download('^XSP', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval='1m', progress=False)
        data_vix = yf.download('^VIX1D', start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval='1m', progress=False)
        
        if data_xsp.empty or data_vix.empty:
            return None, None
            
        # Convertir índices a zona horaria de NY de forma segura
        data_xsp.index = data_xsp.index.tz_convert('America/New_York')
        data_vix.index = data_vix.index.tz_convert('America/New_York')
        
        # Filtrar exactamente el minuto de la apertura (09:30 - 09:31)
        apertura_xsp = data_xsp.between_time('09:30', '09:31')
        apertura_vix = data_vix.between_time('09:30', '09:31')
        
        if not apertura_xsp.empty and not apertura_vix.empty:
            # Obtenemos el precio de apertura ('Open') de la primera barra del día
            val_xsp = float(apertura_xsp['Open'].iloc[0])
            val_vix = float(apertura_vix['Open'].iloc[0])
            return round(val_xsp, 2), round(val_vix, 2)
            
        return None, None
    except Exception:
        return None, None

# --- LÓGICA DE CONTROL DE FLUJO ---
xsp_930, vix1d_930, em_call_930, em_put_930 = None, None, None, None
apertura_fijada = False

# Solo intentamos buscar la apertura si el reloj de NY ya superó las 09:30 AM
if hora_ny.time() >= time(9, 30):
    xsp_930, vix1d_930 = obtener_apertura_exacta(fecha_hoy_str)
    if xsp_930 and vix1d_930:
        _, em_call_930, em_put_930 = calcular_em(xsp_930, vix1d_930)
        apertura_fijada = True

# Barra lateral informativa
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Forzar Sincronización"):
        st.cache_data.clear()
        st.rerun()
    st.info(f"🕒 Hora NY: {hora_actual_str}")

# Bloque 1 fijo: Estructura estática para la Apertura (Protegida contra refrescos)
st.subheader("🏁 Fijado a la Apertura (09:30 AM NY)")
if apertura_fijada:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XSP Apertura", f"${xsp_930:.2f}")
    col2.metric("VIX1D Apertura", f"{vix1d_930:.2f}%")
    col3.metric("EM0call (Techo 🔺)", f"{em_call_930:.0f}")
    col4.metric("EM0put (Suelo 🔻)", f"{em_put_930:.0f}")
else:
    st.warning(f"⏳ Esperando que el mercado abra y consolide los datos de las 09:30 AM NY. Hora actual en NY: {hora_ny.strftime('%H:%M')}")

st.markdown("---")

# Bloque 2 dinámico: Usamos fragmento exclusivamente para actualizar el tiempo real cada 60 segundos
@st.fragment(run_every=60)
def render_live_data(xsp_ref, vix_ref, call_ref, put_ref, fijado):
    xsp_actual, vix1d_actual = obtener_datos_actuales()

    if xsp_actual and vix1d_actual:
        # Calcular métricas del estado actual (Vivo)
        _, em_call_act, em_put_act = calcular_em(xsp_actual, vix1d_actual)

        st.subheader(f"⚡ Tiempo Real (Actualizado a las {datetime.now(tz_ny).strftime('%H:%M:%S')} NY)")
        col1_act, col2_act, col3_act, col4_act = st.columns(4)
        
        col1_act.metric("XSP Actual", f"${xsp_actual:.2f}")
        col2_act.metric("VIX1D Actual", f"{vix1d_actual:.2f}%")
        col3_act.metric("EM0call Actual 🔺", f"{em_call_act:.0f}")
        col4_act.metric("EM0put Actual 🔻", f"{em_put_act:.0f}")

        # Tabla resumen de desviaciones utilizando las variables estáticas externas heredadas
        if fijado:
            st.markdown("### 📊 Comparativa vs Apertura")
            df_comp = pd.DataFrame({
                "Métrica": ["Precio XSP", "Volatilidad VIX1D", "Strike EM0call", "Strike EM0put"],
                "Apertura (9:30)": [xsp_ref, vix_ref, call_ref, put_ref],
                "Actual": [xsp_actual, vix1d_actual, em_call_act, em_put_act],
                "Diferencia": [
                    round(xsp_actual - xsp_ref, 2), 
                    round(vix1d_actual - vix_ref, 2), 
                    int(em_call_act - call_ref), 
                    int(em_put_act - put_ref)
                ]
            })
            st.table(df_comp)

# Ejecutar el fragmento dinámico pasándole los parámetros fijos del scope global
render_live_data(xsp_930, vix1d_930, em_call_930, em_put_930, apertura_fijada)
