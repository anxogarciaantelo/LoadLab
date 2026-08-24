import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Librerías de Machine Learning
try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
except ImportError:
    st.error("Faltan librerías. Añade 'xgboost' y 'scikit-learn' a tu requirements.txt")
    st.stop()

from utils.math_helpers import *
from database.db_manager import *

if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo.")
    st.stop()

st.title("🧠 Oráculo: Predicción de Lesiones por IA")
st.caption("Motor predictivo impulsado por XGBoost basado en el historial acumulado de GPS, Wellness y Ratio A/C.")

# --- 1. CONSTRUCCIÓN DEL DATASET TEMPORAL ---
@st.cache_data(ttl=3600, show_spinner=False)
def construir_dataset_entrenamiento(sesiones, lesiones):
    registros = []
    
    # Extraer métricas diarias
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
    
    # Ingeniería de Características (Rolling Windows)
    # Calculamos la media de los últimos 7 días y la desviación estándar para ver picos
    features = []
    for jug, group in df.groupby("JUGADOR"):
        group = group.set_index("FECHA").resample('D').sum().fillna(0)
        
        # Aguda (7d) y Crónica (28d) nativa usando las matemáticas de LoadLab
        group['Carga_Aguda'] = group['CARGA'].ewm(span=7, adjust=False).mean()
        group['Carga_Cronica'] = group['CARGA'].ewm(span=28, adjust=False).mean()
        group['Ratio_AC'] = np.where(group['Carga_Cronica'] > 0, group['Carga_Aguda'] / group['Carga_Cronica'], 1.0)
        
        # Picos de HSR y Sprints (Agudo 7 días)
        group['HSR_7d'] = group['HSR'].rolling(window=7, min_periods=1).sum()
        group['Sprints_7d'] = group['SPRINTS'].rolling(window=7, min_periods=1).sum()
        group['ACC_7d'] = group['ACC'].rolling(window=7, min_periods=1).sum()
        
        # Caídas de Wellness (Promedio 3 días)
        group['Wellness_3d'] = group['WELLNESS'].rolling(window=3, min_periods=1).mean()
        group['Sueno_3d'] = group['SUEÑO'].rolling(window=3, min_periods=1).mean()
        
        group['JUGADOR'] = jug
        features.append(group.reset_index())
        
    df_features = pd.concat(features, ignore_index=True)
    
    # Etiquetado de la Variable Objetivo (Y): ¿Hubo lesión en los siguientes 7 días?
    df_features['Lesion_Target'] = 0
    fechas_lesiones = [(l['jugador'], pd.to_datetime(l['id_sesion'])) for l in lesiones]
    
    for jug, fecha_lesion in fechas_lesiones:
        # Marcamos como '1' la ventana de 7 días previos a la lesión
        mask = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion - pd.Timedelta(days=7)) & (df_features['FECHA'] < fecha_lesion)
        df_features.loc[mask, 'Lesion_Target'] = 1
        
        # Excluimos los días donde el jugador ya estaba lesionado para no confundir al modelo
        baja = mask_baja = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion) & (df_features['FECHA'] <= fecha_lesion + pd.Timedelta(days=21))
        df_features = df_features[~baja]

    return df_features

# --- 2. ENTRENAMIENTO E INFERENCIA ---
df_master = construir_dataset_entrenamiento(st.session_state.sesiones, st.session_state.lesiones)

if df_master.empty or len(df_master[df_master['Lesion_Target'] == 1]) < 10:
    st.info("📊 El algoritmo está en fase de aprendizaje. Necesitamos al menos 10 registros históricos de lesiones y más volumen de entrenamientos para generar predicciones fiables.")
    st.stop()

with st.spinner("Entrenando el modelo XGBoost con los patrones físicos de tu plantilla..."):
    # Selección de variables predictoras
    predictores = ['Ratio_AC', 'Carga_Aguda', 'HSR_7d', 'Sprints_7d', 'ACC_7d', 'Wellness_3d', 'Sueno_3d']
    X = df_master[predictores]
    y = df_master['Lesion_Target']
    
    # Compensación matemática por la rareza de las lesiones
    ratio_desbalanceo = len(y[y == 0]) / len(y[y == 1]) if len(y[y == 1]) > 0 else 1
    
    # Configuración del modelo XGBoost
    modelo = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=ratio_desbalanceo, # Penalización crucial para encontrar los falsos negativos
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    # Normalización
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Entrenamiento
    modelo.fit(X_scaled, y)
    
    # --- PREDICCIÓN A DÍA DE HOY ---
    df_hoy = df_master[df_master['FECHA'] == df_master['FECHA'].max()].copy()
    if not df_hoy.empty:
        X_hoy = scaler.transform(df_hoy[predictores])
        probabilidades = modelo.predict_proba(X_hoy)[:, 1] * 100
        df_hoy['Riesgo_%'] = probabilidades

# --- 3. DASHBOARD VISUAL DE ALERTAS TÁCTICAS ---
st.markdown("### ⚡ Panel de Riesgo a 7 Días Vista")

df_hoy = df_hoy.sort_values(by="Riesgo_%", ascending=False)
alto_riesgo = df_hoy[df_hoy['Riesgo_%'] > 65]

if alto_riesgo.empty:
    st.success("✅ Ningún jugador presenta un patrón crítico de riesgo de lesión para la próxima semana.")
else:
    st.error(f"🚨 Se han detectado {len(alto_riesgo)} jugadores en zona crítica basándonos en tu histórico.")
    
    cols = st.columns(min(len(alto_riesgo), 3))
    for i, (idx, row) in enumerate(alto_riesgo.head(3).iterrows()):
        with cols[i]:
            st.markdown(f"""
            <div style="background-color: #fff1f2; border-left: 5px solid #e11d48; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <h3 style="margin-bottom: 5px; color: #9f1239;">{row['JUGADOR']}</h3>
                <h1 style="color: #be123c; margin: 0;">{row['Riesgo_%']:.1f}%</h1>
                <p style="color: #881337; font-size: 0.9em; margin-top: 10px;">
                    <strong>Foco de alerta:</strong><br>
                    Ratio A/C: {row['Ratio_AC']:.2f}<br>
                    HSR Acumulado: {row['HSR_7d']:.0f} m
                </p>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("#### 🔍 Explicabilidad del Modelo (Feature Importance)")
st.caption("¿Qué variables están teniendo más peso a la hora de lesionar a los jugadores de esta plantilla específica?")

importancias = modelo.feature_importances_
df_importancia = pd.DataFrame({'Variable': predictores, 'Impacto': importancias}).sort_values('Impacto', ascending=True)

fig_imp = px.bar(
    df_importancia, 
    x='Impacto', 
    y='Variable', 
    orientation='h',
    title="Patrones clave aprendidos por la IA",
    color_discrete_sequence=['#0f172a']
)
st.plotly_chart(fig_imp, use_container_width=True)
