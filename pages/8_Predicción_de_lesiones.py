import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler
except ImportError:
    st.error("⚠️ Faltan librerías. Añade 'xgboost' y 'scikit-learn' a tu archivo requirements.txt.")
    st.stop()

from utils.math_helpers import *
from database.db_manager import *

if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo.")
    st.stop()

aplicar_color_sidebar()

st.title("🧠 Oráculo: Predicción de Riesgo Lesional")
st.caption("Sistema Híbrido: Combina algoritmos científicos de prevención deportiva con Machine Learning adaptativo (XGBoost) para tu plantilla.")

# ==========================================
# 1. CONSTRUCCIÓN DEL DATASET TEMPORAL (CON IMPUTACIÓN Y AJUSTE A METROS)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def construir_dataset_entrenamiento(sesiones, lesiones):
    registros = []
    dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", "Desconocida") for p in st.session_state.get("plantilla", [])}
    dict_pos_gen = {limpiar_nombre(p["JUGADOR"]): p.get("POS", "DEF") for p in st.session_state.get("plantilla", [])}

    for s in sesiones:
        if not s.get("informe_generado"): continue
            
        es_partido = "Partido" in s.get("tipo", "")
        disp_dict = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
        
        datos_gps_validos = []
        for d in s.get("datos_informe", []):
            # CORRECCIÓN: Convertir explícitamente los KM a METROS multiplicando por 1000
            dis_val = safe_float(d.get("DIS")) * 1000
            min_val = safe_float(d.get("MIN", 0))
            
            if dis_val > 0 and min_val > 0:
                jug_limpio = limpiar_nombre(d["JUGADOR"])
                hsr_val = safe_float(d.get("DIS AI", d.get("HID >21", 0))) * 1000
                
                datos_gps_validos.append({
                    "POS_ESP": dict_pos_esp.get(jug_limpio, "Desconocida"),
                    "POS_GEN": dict_pos_gen.get(jug_limpio, "DEF"),
                    "MIN": min_val,
                    "DIS_pm": dis_val / min_val,
                    "HSR_pm": hsr_val / min_val,
                    "SPRINTS_pm": safe_float(d.get("Nº SPR", d.get("SPR >24", 0))) / min_val,
                    "ACC_pm": safe_float(d.get("ACC", d.get("ACC >3", 0))) / min_val,
                    "DCC_pm": safe_float(d.get("DCC", d.get("DCC >3", 0))) / min_val,
                })
        
        medias_esp, medias_gen, medias_equipo = {}, {}, {}
        if datos_gps_validos:
            df_validos = pd.DataFrame(datos_gps_validos)
            cols_pm = ["DIS_pm", "HSR_pm", "SPRINTS_pm", "ACC_pm", "DCC_pm"]
            medias_esp = df_validos.groupby("POS_ESP")[cols_pm].mean().to_dict('index')
            medias_gen = df_validos.groupby("POS_GEN")[cols_pm].mean().to_dict('index')
            medias_equipo = df_validos[cols_pm].mean().to_dict()

        for d in s.get("datos_informe", []):
            jug_nombre = d["JUGADOR"]
            jug_limpio = limpiar_nombre(jug_nombre)
            min_jug = safe_float(d.get("MIN", 0))
            
            # CORRECCIÓN: Convertir explícitamente a METROS
            dis_jug = safe_float(d.get("DIS")) * 1000
            hsr_jug = safe_float(d.get("DIS AI", d.get("HID >21", 0))) * 1000
            spr_jug = safe_float(d.get("Nº SPR", d.get("SPR >24", 0)))
            acc_jug = safe_float(d.get("ACC", d.get("ACC >3", 0)))
            dcc_jug = safe_float(d.get("DCC", d.get("DCC >3", 0)))
            
            estado = disp_dict.get(jug_limpio, "Disponible" if not es_partido else "Titular")
            elegible = (estado in ["Titular", "Suplente"] and min_jug > 0) if es_partido else (estado == "Disponible" and min_jug > 0)

            if elegible and dis_jug == 0 and min_jug > 0 and datos_gps_validos:
                pos_e = dict_pos_esp.get(jug_limpio, "Desconocida")
                pos_g = dict_pos_gen.get(jug_limpio, "DEF")
                ratios = medias_esp.get(pos_e, medias_gen.get(pos_g, medias_equipo))
                
                dis_jug = ratios["DIS_pm"] * min_jug
                hsr_jug = ratios["HSR_pm"] * min_jug
                spr_jug = ratios["SPRINTS_pm"] * min_jug
                acc_jug = ratios["ACC_pm"] * min_jug
                dcc_jug = ratios["DCC_pm"] * min_jug

            registros.append({
                "FECHA": pd.to_datetime(s["fecha"]),
                "JUGADOR": jug_nombre,
                "RPE": safe_float(d.get("RPE")),
                "WELLNESS": safe_float(d.get("WELLNESS")),
                "SUEÑO": safe_float(d.get("W_Sueño")),
                "FATIGA": safe_float(d.get("W_Fatiga")),
                "ESTRES": safe_float(d.get("W_Estres")),
                "DIS_TOTAL": dis_jug,
                "HSR": hsr_jug,
                "SPRINTS": spr_jug,
                "ACC": acc_jug,
                "DCC": dcc_jug,
                "CARGA": safe_float(d.get("CARGA"))
            })
                
    if not registros: return pd.DataFrame()
        
    df = pd.DataFrame(registros).sort_values("FECHA")
    
    features = []
    for jug, group in df.groupby("JUGADOR"):
        group = group.set_index("FECHA").resample('D').sum().fillna(0)
        group['Carga_Aguda'] = group['CARGA'].ewm(span=7, adjust=False).mean()
        group['Carga_Cronica'] = group['CARGA'].ewm(span=28, adjust=False).mean()
        group['Ratio_AC'] = np.where(group['Carga_Cronica'] > 0, group['Carga_Aguda'] / group['Carga_Cronica'], 1.0)
        group['HSR_7d'] = group['HSR'].rolling(window=7, min_periods=1).sum()
        group['Sprints_7d'] = group['SPRINTS'].rolling(window=7, min_periods=1).sum()
        group['ACC_7d'] = group['ACC'].rolling(window=7, min_periods=1).sum()
        group['DCC_7d'] = group['DCC'].rolling(window=7, min_periods=1).sum()
        group['Wellness_3d'] = group['WELLNESS'].replace(0, np.nan).rolling(window=3, min_periods=1).mean().fillna(0)
        group['Sueno_3d'] = group['SUEÑO'].replace(0, np.nan).rolling(window=3, min_periods=1).mean().fillna(0)
        group['JUGADOR'] = jug
        features.append(group.reset_index())
        
    df_features = pd.concat(features, ignore_index=True)
    
    # Target: Solo lesiones MUSCULARES/TENDINOSAS SIN CONTACTO
    df_features['Lesion_Target'] = 0
    fechas_lesiones = [
        (l['jugador'], pd.to_datetime(l['id_sesion'])) 
        for l in lesiones 
        if l.get('tipo') in ["Muscular", "Tendinosa"] and l.get('contacto') == "No"
    ]
    
    for jug, fecha_lesion in fechas_lesiones:
        mask_riesgo = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion - pd.Timedelta(days=7)) & (df_features['FECHA'] < fecha_lesion)
        df_features.loc[mask_riesgo, 'Lesion_Target'] = 1
        mask_baja = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion) & (df_features['FECHA'] <= fecha_lesion + pd.Timedelta(days=21))
        df_features = df_features[~mask_baja]

    return df_features

# ==========================================
# 2. SELECCIÓN DEL MOTOR DE IA (HÍBRIDO)
# ==========================================
df_master = construir_dataset_entrenamiento(st.session_state.sesiones, st.session_state.lesiones)

if df_master.empty:
    render_estado_vacio(
        icono="🧠", 
        titulo="El oráculo necesita datos", 
        descripcion="Para que el algoritmo pueda calcular el riesgo lesional mediante Machine Learning, necesita un volumen mínimo de entrenamientos procesados con minutos, RPE o GPS.",
        accion_sugerida="Vuelve a la pestaña 'Entrenamientos' y carga los datos físicos de tus sesiones."
    )
    st.stop()

# Extracción de la fotografía actual
df_hoy = df_master.loc[df_master.groupby('JUGADOR')['FECHA'].idxmax()].copy()

# EXCLUSIÓN DE JUGADORES LESIONADOS ACTUALMENTE
lesionados_activos = [l['jugador'] for l in st.session_state.lesiones if l.get('estado') == 'Activa']
df_hoy = df_hoy[~df_hoy['JUGADOR'].isin(lesionados_activos)]

MIN_LESIONES_REQUERIDAS = 10

# CORRECCIÓN DEL CONTEO: Contamos eventos reales, no filas de entrenamiento
lesiones_musculares_validas = [l for l in st.session_state.lesiones if l.get('tipo') in ["Muscular", "Tendinosa"] and l.get('contacto') == "No"]
total_lesiones_reales = len(lesiones_musculares_validas)

predictores = ['Ratio_AC', 'Carga_Aguda', 'HSR_7d', 'Sprints_7d', 'ACC_7d', 'DCC_7d', 'Wellness_3d', 'Sueno_3d']
modo_ia = False

if total_lesiones_reales >= MIN_LESIONES_REQUERIDAS:
    modo_ia = True
    with st.spinner("Motor XGBoost Activo: Procesando patrones individuales..."):
        X = df_master[predictores]
        y = df_master['Lesion_Target']
        ratio_desbalanceo = len(y[y == 0]) / len(y[y == 1]) if len(y[y == 1]) > 0 else 1
        
        modelo = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, scale_pos_weight=ratio_desbalanceo, eval_metric='logloss')
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        modelo.fit(X_scaled, y)
        
        if not df_hoy.empty:
            X_hoy = scaler.transform(df_hoy[predictores])
            df_hoy['Riesgo_%'] = modelo.predict_proba(X_hoy)[:, 1] * 100
else:
    # MOTOR HEURÍSTICO / LITERATURA CIENTÍFICA CORREGIDO
    st.info(f"🧠 **Motor Heurístico Científico Activo:** ({total_lesiones_reales}/{MIN_LESIONES_REQUERIDAS} lesiones musculares sin contacto). La IA requiere más histórico. Predicciones actuales calculadas mediante baremos científicos estándar.")
    
    def calcular_riesgo_cientifico(row):
        riesgo = 5.0 # Riesgo base
        
        # 1. Ratio A/C
        if row['Ratio_AC'] > 1.5: riesgo += 35.0
        elif row['Ratio_AC'] > 1.3: riesgo += 15.0
        elif row['Ratio_AC'] < 0.8: riesgo += 10.0
        
        # 2. Wellness y Sueño (Escala inversa: mayor = peor)
        if row['Sueno_3d'] >= 5: 
            riesgo += 15.0
            
        if row['Wellness_3d'] >= 24: 
            riesgo += 15.0 # Wellness crítico
        elif row['Wellness_3d'] >= 18: 
            riesgo += 5.0  # Wellness moderado
        
        # 3. Historial clínico inteligente (Últimos 60 días)
        riesgo_previo = 0.0
        for l in st.session_state.lesiones:
            if l['jugador'] == row['JUGADOR']:
                fecha_l = datetime.strptime(l['id_sesion'], "%Y-%m-%d")
                if (datetime.today() - fecha_l).days <= 60:
                    tipo_lesion = l.get('tipo', '')
                    
                    if tipo_lesion in ["Muscular", "Tendinosa"]:
                        # Riesgo altísimo por posible recaída directa del tejido
                        riesgo_previo = max(riesgo_previo, 20.0) 
                    elif tipo_lesion == "Artículo-ligamentosa":
                        # Riesgo moderado por alteraciones y compensaciones biomecánicas
                        riesgo_previo = max(riesgo_previo, 10.0)
                        
        riesgo += riesgo_previo
        
        return min(riesgo, 95.0)

    df_hoy['Riesgo_%'] = df_hoy.apply(calcular_riesgo_cientifico, axis=1)

# ==========================================
# 3. DASHBOARD TÁCTICO
# ==========================================
st.markdown("### ⚡ Panel de Riesgo a 7 Días Vista")

df_hoy = df_hoy.sort_values(by="Riesgo_%", ascending=False)
alto_riesgo = df_hoy[df_hoy['Riesgo_%'] > 60]

if alto_riesgo.empty:
    st.success("✅ Ningún jugador activo presenta un patrón crítico de riesgo de lesión para la próxima semana.")
else:
    st.error(f"🚨 Se han detectado {len(alto_riesgo)} jugadores con parámetros que indican alto riesgo lesional inminente.")
    
    cols = st.columns(min(len(alto_riesgo), 3))
    for i, (idx, row) in enumerate(alto_riesgo.head(3).iterrows()):
        with cols[i]:
            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-left: 5px solid #dc2626; padding: 18px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #0a0a0a; font-weight: 800; text-transform: uppercase;">{row['JUGADOR']}</h4>
                    <span style="background: #dc2626; color: #ffffff; font-weight: 800; padding: 4px 10px; border-radius: 4px; font-size: 0.8rem; letter-spacing: 0.05em;">
                        {row['Riesgo_%']:.1f}% RIESGO
                    </span>
                </div>
                <hr style="margin: 12px 0; border-color: #f4f4f5;">
                <div style="font-size: 0.85rem; color: #475569; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div><b style="color:#1c1c1e;">Ratio A/C:</b> {row['Ratio_AC']:.2f}</div>
                    <div><b style="color:#1c1c1e;">HSR (7d):</b> {row['HSR_7d']:.0f} m</div>
                    <div><b style="color:#1c1c1e;">Sueño:</b> {row['Sueno_3d']:.1f}/7</div>
                    <div><b style="color:#1c1c1e;">Fatiga/Dolor:</b> {row['Wellness_3d']:.1f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

c_info1, c_info2 = st.columns([2, 1])

with c_info1:
    if modo_ia:
        st.markdown("#### 🔍 Explicabilidad del Modelo (XGBoost)")
        importancias = modelo.feature_importances_
        nombres_amigables = {'Ratio_AC': 'Ratio A/C (EWMA)', 'Carga_Aguda': 'Carga Aguda', 'HSR_7d': 'HSR Acum. (7d)', 'Sprints_7d': 'Sprints Acum. (7d)', 'ACC_7d': 'Aceleraciones (7d)', 'DCC_7d': 'Deceleraciones (7d)', 'Wellness_3d': 'Fatiga / Dolor', 'Sueno_3d': 'Falta de Sueño'}
        
        df_importancia = pd.DataFrame({'Variable': [nombres_amigables.get(p, p) for p in predictores], 'Impacto': importancias * 100}).sort_values('Impacto', ascending=True)

        fig_imp = px.bar(df_importancia, x='Impacto', y='Variable', orientation='h', color_discrete_sequence=['#00b4d8'])
        fig_imp.update_layout(xaxis_title="Peso en la predicción (%)", yaxis_title="")
        st.plotly_chart(fig_imp, use_container_width=True)
    else:
        st.markdown("#### ⚖️ Baremos Científicos Aplicados")
        st.info("**Ponderación actual:** \n\n• Ratio A/C > 1.5 (+35%)\n• Ratio A/C < 0.8 (+10%)\n• Lesión Previa en 60d (+20%)\n• Wellness Crítico > 24 (+15%)\n• Sueño Deficiente > 5 (+15%)")

with c_info2:
    st.markdown("#### 📋 Listado del Equipo (Disponibles)")
    df_lista = df_hoy[['JUGADOR', 'Riesgo_%', 'Ratio_AC', 'HSR_7d']].copy()
    
    def color_riesgo(val):
        if val > 60: return 'color: white; background-color: #e11d48; font-weight: bold;'
        if val > 30: return 'color: black; background-color: #fcd34d;'
        return 'color: black; background-color: #86efac;'
        
    st.dataframe(df_lista.style.format({"Riesgo_%": "{:.1f}%", "Ratio_AC": "{:.2f}", "HSR_7d": "{:.0f} m"}).map(color_riesgo, subset=['Riesgo_%']), use_container_width=True, hide_index=True)
