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
    dict_edad = {limpiar_nombre(p["JUGADOR"]): safe_float(p.get("edad", 25)) for p in st.session_state.get("plantilla", [])}
    
    for s in sesiones:
        if not s.get("informe_generado"): continue
            
        es_partido = "Partido" in s.get("tipo", "")
        disp_dict = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
        
        datos_gps_validos = []
        for d in s.get("datos_informe", []):
            # CORRECCIÓN: Convertir explícitamente los KM a METROS multiplicando por 1000
            dis_val = safe_float(d.get("DIS")) * 1000.0
            min_val = safe_float(d.get("MIN", 0))
            
            if dis_val > 0 and min_val > 0:
                jug_limpio = limpiar_nombre(d["JUGADOR"])
                hsr_val = safe_float(d.get("DIS AI", d.get("HID >21", 0)))
                
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
            
            dis_jug = safe_float(d.get("DIS")) * 1000.0
            hsr_jug = safe_float(d.get("DIS AI", d.get("HID >21", 0)))
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
        group['Edad'] = dict_edad.get(limpiar_nombre(jug), 25.0)
        def calcular_lesiones_previas(fecha_fila, nombre_jugador):
            count = 0
            for l in lesiones:
                if l['jugador'] == nombre_jugador and l.get('tipo') in ["Muscular", "Tendinosa"]:
                    if pd.to_datetime(l['id_sesion']) < fecha_fila:
                        count += 1
            return count
            
        group['Lesiones_Previas'] = group.apply(lambda r: calcular_lesiones_previas(r.name, r['JUGADOR']), axis=1)
        
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
    from utils.math_helpers import render_estado_vacio
    render_estado_vacio(
        icono="🧠", 
        titulo="El oráculo necesita datos", 
        descripcion="Para que el algoritmo pueda calcular el riesgo lesional, necesita un volumen mínimo de entrenamientos procesados con minutos, RPE o GPS.",
        accion_sugerida="Vuelve a la pestaña 'Entrenamientos' y carga los datos físicos de tus sesiones."
    )
    st.stop()

# Extracción de la fotografía actual
df_hoy = df_master.loc[df_master.groupby('JUGADOR')['FECHA'].idxmax()].copy()

# EXCLUSIÓN DE JUGADORES LESIONADOS ACTUALMENTE
lesionados_activos = [l['jugador'] for l in st.session_state.lesiones if l.get('estado') == 'Activa']
df_hoy = df_hoy[~df_hoy['JUGADOR'].isin(lesionados_activos)]

MIN_LESIONES_REQUERIDAS = 10
lesiones_musculares_validas = [l for l in st.session_state.lesiones if l.get('tipo') in ["Muscular", "Tendinosa"] and l.get('contacto') == "No"]
total_lesiones_reales = len(lesiones_musculares_validas)

predictores = ['Ratio_AC', 'Carga_Aguda', 'HSR_7d', 'Sprints_7d', 'ACC_7d', 'DCC_7d', 'Wellness_3d', 'Sueno_3d', 'Edad', 'Lesiones_Previas']
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
    # MOTOR HEURÍSTICO AVANZADO (Basado en T. Gabbett y Banister)
    def calcular_riesgo_cientifico(row):
        riesgo = 5.0 # Riesgo base fisiológico
        
        # 1. Ratio A/C (The Sweet Spot Model)
        if row['Ratio_AC'] > 1.5: riesgo += 40.0
        elif row['Ratio_AC'] > 1.3: riesgo += 20.0
        elif row['Ratio_AC'] < 0.8: riesgo += 15.0 # Under-training risk
        
        # 2. Carga Aguda Extrema (Spike)
        if row['Carga_Aguda'] > 3000: riesgo += 10.0
        
        # 3. Wellness y Sueño (Recuperación del SNC)
        if row['Sueno_3d'] >= 5: riesgo += 15.0
        if row['Wellness_3d'] >= 24: riesgo += 15.0 
        elif row['Wellness_3d'] >= 18: riesgo += 5.0 
        
        # 4. Historial clínico (La mayor predictibilidad de lesión es una lesión previa)
        riesgo_previo = 0.0
        for l in st.session_state.lesiones:
            if l['jugador'] == row['JUGADOR']:
                fecha_l = datetime.strptime(l['id_sesion'], "%Y-%m-%d")
                if (datetime.today() - fecha_l).days <= 60:
                    tipo_lesion = l.get('tipo', '')
                    if tipo_lesion in ["Muscular", "Tendinosa"]: riesgo_previo = max(riesgo_previo, 25.0) 
                    elif tipo_lesion == "Artículo-ligamentosa": riesgo_previo = max(riesgo_previo, 10.0)
                        
        riesgo += riesgo_previo
        return min(riesgo, 95.0)

    df_hoy['Riesgo_%'] = df_hoy.apply(calcular_riesgo_cientifico, axis=1)

# ==========================================
# 3. DASHBOARD TÁCTICO ÉLITE
# ==========================================
st.markdown("### 🧠 Sistema de Alerta Temprana (Prevención de Lesiones)")

if df_hoy.empty:
    st.success("✅ No hay jugadores activos a evaluar o faltan datos recientes.")
    st.stop()

df_hoy = df_hoy.sort_values(by="Riesgo_%", ascending=False)
alto_riesgo = df_hoy[df_hoy['Riesgo_%'] >= 55]

# --- 1. CABECERA DE ESTADO (Compacta y Profesional) ---
estado_txt = "Motor de IA Predictivo (XGBoost)" if modo_ia else "Motor Algorítmico Científico (Gabbett & Banister)"
st.caption(f"**Motor Activo:** {estado_txt} | Análisis a 7 días vista basado en fatiga residual, EWMA y cinemática.")

c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
from utils.math_helpers import render_kpi_elite
with c_kpi1: render_kpi_elite("Jugadores en Riesgo Crítico", f"{len(alto_riesgo)}", color_borde="#ef4444" if len(alto_riesgo)>0 else "#10b981")
with c_kpi2: render_kpi_elite("Riesgo Medio Plantilla", f"{df_hoy['Riesgo_%'].mean():.1f}%", color_borde="#f59e0b" if df_hoy['Riesgo_%'].mean()>30 else "#3b82f6")
with c_kpi3: render_kpi_elite("Ratio A/C Medio", f"{df_hoy['Ratio_AC'].mean():.2f}", color_borde="#10b981" if 0.8 <= df_hoy['Ratio_AC'].mean() <= 1.3 else "#ef4444")

st.markdown("---")

# --- 2. MATRIZ DE RIESGO Y ALARMAS INMINENTES ---
c_graf, c_alertas = st.columns([2, 1])

with c_graf:
    st.markdown("#### 🎯 Matriz de Carga (Sweet Spot)")
    # Gráfico profesional de dispersión cruzando Carga vs A/C
    fig_matrix = px.scatter(
        df_hoy, x='Ratio_AC', y='Carga_Aguda', color='Riesgo_%', 
        hover_name='JUGADOR', text='JUGADOR',
        color_continuous_scale="RdYlGn_r", range_color=[0, 100],
        labels={"Ratio_AC": "Ratio Agudo/Crónico (A/C)", "Carga_Aguda": "Carga Aguda Acumulada (UA)"}
    )
    
    fig_matrix.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
    
    # Dibujar la "Sweet Spot Zone" (Zona segura de Gabbett)
    max_carga = df_hoy['Carga_Aguda'].max() * 1.2 if df_hoy['Carga_Aguda'].max() > 0 else 4000
    fig_matrix.add_shape(type="rect", x0=0.8, x1=1.3, y0=0, y1=max_carga, fillcolor="#10b981", opacity=0.15, line_width=0, layer="below")
    fig_matrix.add_annotation(x=1.05, y=max_carga*0.9, text="ZONA SEGURA (SWEET SPOT)", showarrow=False, font=dict(color="#10b981", size=12, weight="bold"))
    
    # Dibujar "Danger Zone"
    fig_matrix.add_shape(type="rect", x0=1.5, x1=max(df_hoy['Ratio_AC'].max()*1.1, 2.0), y0=0, y1=max_carga, fillcolor="#ef4444", opacity=0.1, line_width=0, layer="below")
    fig_matrix.add_annotation(x=1.75, y=max_carga*0.9, text="ZONA DE PELIGRO", showarrow=False, font=dict(color="#ef4444", size=12, weight="bold"))

    fig_matrix.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_matrix, use_container_width=True)

with c_alertas:
    st.markdown("#### 🚨 Alertas Inminentes")
    if alto_riesgo.empty:
        st.success("Plantilla fuera de riesgo crítico. Buen trabajo de gestión de cargas.")
    else:
        for _, row in alto_riesgo.head(3).iterrows():
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-left: 4px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #f8fafc; font-size: 1.1rem; text-transform: uppercase;">{row['JUGADOR']}</strong>
                    <span style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.8rem;">{row['Riesgo_%']:.0f}% RIESGO</span>
                </div>
                <div style="font-size: 0.85rem; color: #94a3b8; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                    <div>A/C: <b style="color: #f8fafc;">{row['Ratio_AC']:.2f}</b></div>
                    <div>Carga: <b style="color: #f8fafc;">{row['Carga_Aguda']:.0f}</b></div>
                    <div>Wellness: <b style="color: #f8fafc;">{row['Wellness_3d']:.1f}</b></div>
                    <div>HSR (7d): <b style="color: #f8fafc;">{row['HSR_7d']:.0f}m</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# --- 3. TABLA DE DATOS INTERACTIVA CON BARRAS DE PROGRESO ---
st.markdown("#### 📋 Evaluación Completa de la Plantilla")
st.caption("Ordenado de mayor a menor riesgo lesional. Haz clic en las cabeceras para reordenar.")

# Preparar DataFrame para visualización
df_display = df_hoy[['JUGADOR', 'Riesgo_%', 'Ratio_AC', 'Carga_Aguda', 'Wellness_3d', 'HSR_7d', 'Sprints_7d']].copy()
df_display.rename(columns={
    'Riesgo_%': 'Riesgo Global',
    'Ratio_AC': 'Ratio A/C',
    'Carga_Aguda': 'Carga Aguda (UA)',
    'Wellness_3d': 'Fatiga / Dolor (Pts)',
    'HSR_7d': 'HSR Acum. (m)',
    'Sprints_7d': 'Sprints Acum.'
}, inplace=True)

# Renderizar tabla nativa con configuraciones de columnas espectaculares
st.dataframe(
    df_display,
    column_config={
        "JUGADOR": st.column_config.TextColumn("Deportista", width="medium"),
        "Riesgo Global": st.column_config.ProgressColumn(
            "Riesgo Inminente (%)",
            help="Probabilidad de sufrir una lesión muscular/tendinosa en los próximos 7 días.",
            format="%.0f%%",
            min_value=0,
            max_value=100,
        ),
        "Ratio A/C": st.column_config.NumberColumn("Ratio A/C", format="%.2f"),
        "Carga Aguda (UA)": st.column_config.NumberColumn("Carga (7d)", format="%.0f"),
        "Fatiga / Dolor (Pts)": st.column_config.NumberColumn("Wellness (3d)", format="%.1f"),
        "HSR Acum. (m)": st.column_config.NumberColumn("Alta Intensidad (7d)", format="%.0f m"),
        "Sprints Acum.": st.column_config.NumberColumn("Sprints (7d)", format="%.0f")
    },
    hide_index=True,
    use_container_width=True
)
