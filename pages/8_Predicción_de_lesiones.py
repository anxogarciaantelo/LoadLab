import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# --- LIBRERÍAS DE MACHINE LEARNING ---
try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler
except ImportError:
    st.error("⚠️ Faltan librerías. Añade 'xgboost' y 'scikit-learn' a tu archivo requirements.txt y reinicia la app.")
    st.stop()

# --- IMPORTACIONES LOCALES ---
from utils.math_helpers import *
from database.db_manager import *

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    if st.button("Ir al Login principal"):
        st.session_state.clear()
        st.rerun()
    st.stop()

st.title("🧠 Oráculo: Predicción de Riesgo Lesional")
st.caption("Motor de Inteligencia Artificial (XGBoost) que aprende de los patrones históricos de carga y bienestar de tu plantilla para predecir el riesgo de lesión a 7 días vista.")

# ==========================================
# 1. CONSTRUCCIÓN DEL DATASET TEMPORAL
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def construir_dataset_entrenamiento(sesiones, lesiones):
    registros = []
    
    # 1.1 Extraer métricas diarias de las sesiones
    for s in sesiones:
        if s.get("informe_generado"):
            for d in s.get("datos_informe", []):
                registros.append({
                    "FECHA": pd.to_datetime(s["fecha"]),
                    "JUGADOR": d["JUGADOR"],
                    "RPE": safe_float(d.get("RPE")),
                    "WELLNESS": safe_float(d.get("WELLNESS")),
                    "SUEÑO": safe_float(d.get("W_Sueño")),
                    "FATIGA": safe_float(d.get("W_Fatiga")),
                    "ESTRES": safe_float(d.get("W_Estres")),
                    "DIS_TOTAL": safe_float(d.get("DIS")),
                    "HSR": safe_float(d.get("DIS AI", d.get("HID >21", 0))),
                    "SPRINTS": safe_float(d.get("Nº SPR", d.get("SPR >24", 0))),
                    "ACC": safe_float(d.get("ACC", d.get("ACC >3", 0))),
                    "DCC": safe_float(d.get("DCC", d.get("DCC >3", 0))),
                    "CARGA": safe_float(d.get("CARGA"))
                })
                
    if not registros:
        return pd.DataFrame()
        
    df = pd.DataFrame(registros).sort_values("FECHA")
    
    # 1.2 Ingeniería de Características (Rolling Windows)
    features = []
    for jug, group in df.groupby("JUGADOR"):
        group = group.set_index("FECHA").resample('D').sum().fillna(0)
        
        # Carga Aguda, Crónica y Ratio A/C (Fórmulas EWMA)
        group['Carga_Aguda'] = group['CARGA'].ewm(span=7, adjust=False).mean()
        group['Carga_Cronica'] = group['CARGA'].ewm(span=28, adjust=False).mean()
        group['Ratio_AC'] = np.where(group['Carga_Cronica'] > 0, group['Carga_Aguda'] / group['Carga_Cronica'], 1.0)
        
        # Picos Acumulados (7 días)
        group['HSR_7d'] = group['HSR'].rolling(window=7, min_periods=1).sum()
        group['Sprints_7d'] = group['SPRINTS'].rolling(window=7, min_periods=1).sum()
        group['ACC_7d'] = group['ACC'].rolling(window=7, min_periods=1).sum()
        group['DCC_7d'] = group['DCC'].rolling(window=7, min_periods=1).sum()
        
        # Estado de Bienestar (Promedio 3 días para ver caídas recientes)
        group['Wellness_3d'] = group['WELLNESS'].replace(0, np.nan).rolling(window=3, min_periods=1).mean().fillna(0)
        group['Sueno_3d'] = group['SUEÑO'].replace(0, np.nan).rolling(window=3, min_periods=1).mean().fillna(0)
        
        group['JUGADOR'] = jug
        features.append(group.reset_index())
        
    if not features:
        return pd.DataFrame()
        
    df_features = pd.concat(features, ignore_index=True)
    
    # 1.3 Etiquetado de la Variable Objetivo (Target: 1 = Lesión en los prox 7 días)
    df_features['Lesion_Target'] = 0
    fechas_lesiones = [(l['jugador'], pd.to_datetime(l['id_sesion'])) for l in lesiones]
    
    for jug, fecha_lesion in fechas_lesiones:
        # Ventana de riesgo: los 7 días previos a romperse
        mask_riesgo = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion - pd.Timedelta(days=7)) & (df_features['FECHA'] < fecha_lesion)
        df_features.loc[mask_riesgo, 'Lesion_Target'] = 1
        
        # Eliminar del dataset los días en los que el jugador ya estaba de baja (ruido estadístico)
        mask_baja = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion) & (df_features['FECHA'] <= fecha_lesion + pd.Timedelta(days=21))
        df_features = df_features[~mask_baja]

    return df_features

# ==========================================
# 2. ENTRENAMIENTO E INFERENCIA (ML)
# ==========================================
df_master = construir_dataset_entrenamiento(st.session_state.sesiones, st.session_state.lesiones)

# Control de datos mínimos para Machine Learning
MIN_LESIONES_REQUERIDAS = 3

if df_master.empty:
    st.info("📊 No hay datos suficientes de entrenamientos para generar predicciones.")
    st.stop()

total_lesiones_registradas = len(df_master[df_master['Lesion_Target'] == 1])

if total_lesiones_registradas < MIN_LESIONES_REQUERIDAS:
    st.info(f"⏳ **Fase de calibración:** El algoritmo necesita aprender de tu equipo. Registra al menos {MIN_LESIONES_REQUERIDAS} lesiones en el historial (actualmente hay {total_lesiones_registradas} ventanas válidas) para activar las predicciones de IA.")
    st.stop()

# Definición de variables predictoras
predictores = ['Ratio_AC', 'Carga_Aguda', 'HSR_7d', 'Sprints_7d', 'ACC_7d', 'DCC_7d', 'Wellness_3d', 'Sueno_3d']

with st.spinner("Entrenando el modelo XGBoost con los patrones físicos de tu plantilla..."):
    X = df_master[predictores]
    y = df_master['Lesion_Target']
    
    # Balanceo matemático (hay muchos días sanos y muy pocos de lesión)
    num_sanos = len(y[y == 0])
    num_lesionados = len(y[y == 1])
    ratio_desbalanceo = num_sanos / num_lesionados if num_lesionados > 0 else 1
    
    # Modelo
    modelo = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=ratio_desbalanceo, 
        eval_metric='logloss'
    )
    
    # Normalización (Mejora la estabilidad del modelo)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Entrenamiento
    modelo.fit(X_scaled, y)
    
    # 2.1 Predicción del riesgo ACTUAL (Último día registrado por jugador)
    df_hoy = df_master.loc[df_master.groupby('JUGADOR')['FECHA'].idxmax()].copy()
    
    X_hoy = scaler.transform(df_hoy[predictores])
    probabilidades = modelo.predict_proba(X_hoy)[:, 1] * 100
    df_hoy['Riesgo_%'] = probabilidades

# ==========================================
# 3. DASHBOARD TÁCTICO
# ==========================================
st.markdown("### ⚡ Panel de Riesgo a 7 Días Vista")

df_hoy = df_hoy.sort_values(by="Riesgo_%", ascending=False)
alto_riesgo = df_hoy[df_hoy['Riesgo_%'] > 60] # Umbral de riesgo crítico

if alto_riesgo.empty:
    st.success("✅ Ningún jugador presenta un patrón crítico de riesgo de lesión para la próxima semana.")
else:
    st.error(f"🚨 Se han detectado {len(alto_riesgo)} jugadores con perfiles físicos idénticos a los que precedieron lesiones en el pasado.")
    
    cols = st.columns(min(len(alto_riesgo), 3))
    for i, (idx, row) in enumerate(alto_riesgo.head(3).iterrows()):
        with cols[i]:
            st.markdown(f"""
            <div style="background-color: #fff1f2; border-left: 5px solid #e11d48; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <h3 style="margin-bottom: 5px; color: #9f1239;">{row['JUGADOR']}</h3>
                <h1 style="color: #be123c; margin: 0;">{row['Riesgo_%']:.1f}%</h1>
                <p style="color: #881337; font-size: 0.9em; margin-top: 10px;">
                    <strong>Foco de alerta actual:</strong><br>
                    Ratio A/C: {row['Ratio_AC']:.2f}<br>
                    HSR (Últimos 7d): {row['HSR_7d']:.0f} m<br>
                    Calidad Sueño: {row['Sueno_3d']:.1f}
                </p>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 4. EXPLICABILIDAD DEL MODELO
# ==========================================
c_info1, c_info2 = st.columns([2, 1])

with c_info1:
    st.markdown("#### 🔍 ¿Qué está provocando las lesiones en tu equipo?")
    st.caption("Importancia de cada métrica (Feature Importance) calculada por la IA según el histórico de tu plantilla.")
    
    importancias = modelo.feature_importances_
    nombres_amigables = {
        'Ratio_AC': 'Ratio A/C (EWMA)', 'Carga_Aguda': 'Carga Aguda', 
        'HSR_7d': 'HSR Acum. (7d)', 'Sprints_7d': 'Sprints Acum. (7d)', 
        'ACC_7d': 'Aceleraciones (7d)', 'DCC_7d': 'Deceleraciones (7d)', 
        'Wellness_3d': 'Caída de Wellness', 'Sueno_3d': 'Falta de Sueño'
    }
    
    df_importancia = pd.DataFrame({
        'Variable': [nombres_amigables.get(p, p) for p in predictores], 
        'Impacto': importancias * 100
    }).sort_values('Impacto', ascending=True)

    fig_imp = px.bar(
        df_importancia, 
        x='Impacto', 
        y='Variable', 
        orientation='h',
        color_discrete_sequence=['#00b4d8']
    )
    fig_imp.update_layout(xaxis_title="Nivel de Impacto en Lesiones (%)", yaxis_title="")
    st.plotly_chart(fig_imp, use_container_width=True)

with c_info2:
    st.markdown("#### 📋 Listado Completo del Equipo")
    # Formateo visual de la tabla
    df_lista = df_hoy[['JUGADOR', 'Riesgo_%', 'Ratio_AC', 'HSR_7d']].copy()
    
    def color_riesgo(val):
        if val > 60: return 'color: white; background-color: #e11d48; font-weight: bold;'
        if val > 30: return 'color: black; background-color: #fcd34d;'
        return 'color: black; background-color: #86efac;'
        
    st.dataframe(
        df_lista.style.format({
            "Riesgo_%": "{:.1f}%", 
            "Ratio_AC": "{:.2f}",
            "HSR_7d": "{:.0f} m"
        }).map(color_riesgo, subset=['Riesgo_%']),
        use_container_width=True,
        hide_index=True
    )
