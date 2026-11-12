import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler
except ImportError:
    st.error(":material/cancel: Faltan librerías. Añade 'xgboost' y 'scikit-learn' a tu archivo requirements.txt.")
    st.stop()

from utils.math_helpers import *
from database.db_manager import *

if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning(":material/warning: La sesión ha expirado o no se ha seleccionado un equipo.")
    st.stop()

aplicar_color_sidebar()

st.title(":material/psychology: Oráculo: Predicción de Riesgo Lesional")
st.caption("Sistema Híbrido: Combina algoritmos científicos de prevención deportiva con Machine Learning adaptativo (XGBoost) para tu plantilla.")

# ==========================================
# 1. CONSTRUCCIÓN DEL DATASET TEMPORAL (CON IMPUTACIÓN Y AJUSTE A METROS)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def construir_dataset_entrenamiento(df_master, lesiones, plantilla):
    if df_master.empty: return pd.DataFrame()
    
    dict_edad = {limpiar_nombre(p["JUGADOR"]): safe_float(p.get("edad", 25)) for p in plantilla}
    
    # 1. Base utilizando la BBDD Maestra + Carga Compensatoria de Suplentes
    df_base = df_master[['FECHA', 'JUGADOR', 'CARGA', 'WELLNESS', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].copy()
    for c_base, c_comp in [('DIS', 'COMP_DIS'), ('DIS AI', 'COMP_DIS_AI'), ('Nº SPR', 'COMP_SPR'), ('ACC', 'COMP_ACC'), ('DCC', 'COMP_DCC')]:
        if c_comp in df_master.columns:
            df_base[c_base] = pd.to_numeric(df_base[c_base], errors='coerce').fillna(0.0) + pd.to_numeric(df_master[c_comp], errors='coerce').fillna(0.0)
            
    df_base['FECHA'] = pd.to_datetime(df_base['FECHA'])
    fechas_sin_carga_eq = df_base.groupby('FECHA')['CARGA'].sum()
    fechas_pendientes_ia = fechas_sin_carga_eq[fechas_sin_carga_eq == 0].index
    
    features = []
    for jug, group in df_base.groupby("JUGADOR"):
        # 2. Resample diario para mantener la continuidad temporal del EWMA y Monotonía
        group = group.set_index("FECHA").resample('D').sum().fillna(0)
        
        # --- ACUMULADOS 7 DÍAS (MECÁNICA Y HSR PARA EL MODELO) ---
        group['HSR_7d'] = group['DIS AI'].rolling(window=7, min_periods=1).sum()
        group['Sprints_7d'] = group['Nº SPR'].rolling(window=7, min_periods=1).sum()
        group['ACC_7d'] = group['ACC'].rolling(window=7, min_periods=1).sum()
        group['DCC_7d'] = group['DCC'].rolling(window=7, min_periods=1).sum()
        
        # --- CARGAS Y RATIOS (EWMA Uncoupled con Semilla de Microciclo Inicial) ---
        for col_m, pref in [('CARGA', 'Carga'), ('DIS AI', 'HSR'), ('ACC', 'ACC')]:
            s_val = group[col_m].copy()
            p_idx = s_val[s_val > 0].first_valid_index()
            if p_idx:
                v_ini = s_val.loc[p_idx : p_idx + pd.Timedelta(days=6)]
                m_ini = v_ini.sum() / 7.0 if len(v_ini) >= 7 else v_ini.mean()
                idx_seed = pd.date_range(start=p_idx - pd.Timedelta(days=7), end=p_idx - pd.Timedelta(days=1), freq='D')
                s_seed = pd.Series(m_ini, index=idx_seed)
                s_calc = pd.concat([s_seed, s_val.loc[p_idx:]])
                ag = (s_calc.ewm(span=7, adjust=False).mean() * 7).reindex(group.index, fill_value=0.0)
                cr = (s_calc.shift(7).ewm(span=21, adjust=False).mean() * 7).reindex(group.index, fill_value=0.0)
                f_pend_jug = group.index.intersection(fechas_pendientes_ia)
                if len(f_pend_jug) > 0:
                    ag.loc[f_pend_jug] = np.nan
                    cr.loc[f_pend_jug] = np.nan
                    ag = ag.ffill().fillna(0.0)
                    cr = cr.ffill().fillna(0.0)
            else:
                ag = pd.Series(0.0, index=group.index)
                cr = pd.Series(0.0, index=group.index)
            c_min = 10.0 if col_m == 'CARGA' else 1.0
            cr_seg = cr.clip(lower=c_min).where(cr > 0, np.nan)
            suf_r = '' if pref == 'Carga' else f'_{pref}'
            group[f'{pref}_Aguda'] = ag
            group[f'{pref}_Cronica'] = cr
            group[f'Ratio_AC{suf_r}'] = (ag / cr_seg).clip(upper=4.0).fillna(1.0)
        
        # --- MONOTONÍA Y STRAIN ---
        carga_7d = group['CARGA'].rolling(window=7, min_periods=1)
        group['Media_Carga_7d'] = carga_7d.mean()
        group['Std_Carga_7d'] = carga_7d.std(ddof=1).fillna(0)
        group['Std_Carga_7d_Segura'] = np.where(group['Std_Carga_7d'] > 0, group['Std_Carga_7d'], 1.0)
        group['Monotonia_7d'] = np.where(group['Media_Carga_7d'] > 0, group['Media_Carga_7d'] / group['Std_Carga_7d_Segura'], 0.0)
        group['Monotonia_7d'] = group['Monotonia_7d'].clip(upper=3.0)
        group['Strain_7d'] = group['Media_Carga_7d'] * 7 * group['Monotonia_7d']
        
        # --- Z-SCORE WELLNESS (Línea base de 28 días previos, sin contaminar con ceros) ---
        well_clean = group['WELLNESS'].replace(0, np.nan)
        well_28d = well_clean.shift(1).rolling(window=28, min_periods=1)
        group['Well_Mean'] = well_28d.mean().fillna(0)
        group['Well_Std'] = well_28d.std(ddof=1).replace(0, 1.0).fillna(1.0)
        group['Z_Wellness'] = np.where(
            (group['WELLNESS'] > 0) & (group['Well_Mean'] > 0),
            (group['WELLNESS'] - group['Well_Mean']) / group['Well_Std'],
            0.0
        )
        group['Z_Wellness'] = pd.Series(group['Z_Wellness'], index=group.index).replace(0.0, np.nan).ffill(limit=2).fillna(0.0)
        
        # --- VACUNA DE VELOCIDAD (Días sin alcanzar el 85% de VMax) ---
        vmax_historica = group['VMAX'].max()
        if vmax_historica > 25.0:
            group['Es_Pico_VMax'] = group['VMAX'] >= (vmax_historica * 0.85)
            # Transformamos explícitamente el índice a Series para habilitar el .ffill()
            group['Ultimo_Pico'] = group.index.to_series().where(group['Es_Pico_VMax']).ffill()
            group['Dias_Sin_VMax'] = (group.index - group['Ultimo_Pico']).dt.days.fillna(14.0)
        else:
            group['Dias_Sin_VMax'] = 0.0
            
        group['JUGADOR'] = jug
        group['Edad'] = dict_edad.get(limpiar_nombre(jug), 25.0)
        
        # --- LESIONES PREVIAS ---
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
    
    # 3. Target: Lesiones MUSCULARES/TENDINOSAS SIN CONTACTO
    df_features['Lesion_Target'] = 0
    fechas_lesiones = [
        (l['jugador'], pd.to_datetime(l['id_sesion'])) 
        for l in lesiones 
        if l.get('tipo') in ["Muscular", "Tendinosa"] and l.get('contacto') == "No"
    ]
    
    mask_bajas_global = pd.Series(False, index=df_features.index)
    for jug, fecha_lesion in fechas_lesiones:
        mask_riesgo = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion - pd.Timedelta(days=7)) & (df_features['FECHA'] < fecha_lesion)
        df_features.loc[mask_riesgo, 'Lesion_Target'] = 1
        
        mask_baja_jugador = (df_features['JUGADOR'] == jug) & (df_features['FECHA'] >= fecha_lesion) & (df_features['FECHA'] <= fecha_lesion + pd.Timedelta(days=21))
        mask_bajas_global = mask_bajas_global | mask_baja_jugador
        
    return df_features[~mask_bajas_global].copy()

# ==========================================
# 2. SELECCIÓN DEL MOTOR DE IA (HÍBRIDO)
# ==========================================
df_master = construir_dataset_entrenamiento(st.session_state.get("df_master_informes", pd.DataFrame()), st.session_state.lesiones, st.session_state.plantilla)

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

# Se añade la Carga Crónica (factor protector) y las Deceleraciones (daño excéntrico)
predictores = ['Ratio_AC', 'Carga_Aguda', 'Carga_Cronica', 'Ratio_AC_HSR', 'Ratio_AC_ACC', 'DCC_7d', 'Monotonia_7d', 'Strain_7d', 'Z_Wellness', 'Dias_Sin_VMax', 'Edad', 'Lesiones_Previas']
modo_ia = False

if total_lesiones_reales >= MIN_LESIONES_REQUERIDAS:
    modo_ia = True
    with st.spinner("Motor XGBoost Activo: Procesando patrones individuales..."):
        X = df_master[predictores]
        y = df_master['Lesion_Target']
        ratio_desbalanceo = len(y[y == 0]) / len(y[y == 1]) if len(y[y == 1]) > 0 else 1
        
        modelo = xgb.XGBClassifier(
            n_estimators=80, 
            max_depth=2,  # Profundidad mínima para evitar memorización de ruido
            learning_rate=0.01, # Aprendizaje más lento y conservador
            scale_pos_weight=ratio_desbalanceo, 
            min_child_weight=3, # Exige al menos 3 casos para ramificar
            reg_lambda=2.0, # Penalización L2 (Ridge)
            reg_alpha=0.5,  # Penalización L1 (Lasso)
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='logloss'
        )
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
        
        # 1. Ratio A/C Interno y Mecánico
        if row['Ratio_AC'] > 1.5 or row['Ratio_AC_HSR'] > 1.5: riesgo += 35.0
        elif row['Ratio_AC'] > 1.3 or row['Ratio_AC_HSR'] > 1.3: riesgo += 20.0
        elif row['Ratio_AC'] < 0.8: riesgo += 15.0 
        
        # 2. Carga Extrema (Spike), Daño Excéntrico y Strain (Fatiga Residual)
        if row['Carga_Aguda'] > 3000: riesgo += 10.0
        if row['DCC_7d'] > 250: riesgo += 15.0 # Alta acumulación de frenadas
        if row['Strain_7d'] > 4000: riesgo += 10.0
        
        # 3. Factor Protector: Carga Crónica (Suelo aeróbico y robustez)
        if row['Carga_Cronica'] > 2000: riesgo -= 10.0
        elif row['Carga_Cronica'] < 1000: riesgo += 15.0 # Jugador "frágil" por falta de base
        
        # 4. Wellness Z-Score (Deterioro de Readiness: mayor puntuación = mayor fatiga)
        if row['Z_Wellness'] >= 1.5: riesgo += 15.0 
        elif row['Z_Wellness'] >= 1.0: riesgo += 5.0
        
        # 5. Vacuna de Velocidad
        if row['Dias_Sin_VMax'] >= 10: riesgo += 15.0
        
        # 6. Historial clínico
        if row['Lesiones_Previas'] > 0: riesgo += 15.0
                        
        return max(min(riesgo, 95.0), 0.0) # Asegura que el riesgo no baje de 0% por los factores protectores
    df_hoy['Riesgo_%'] = df_hoy.apply(calcular_riesgo_cientifico, axis=1)

# ==========================================
# 3. DASHBOARD TÁCTICO ÉLITE
# ==========================================
st.markdown("### :material/notifications_active: Sistema de Alerta Temprana (Prevención de Lesiones)")

if df_hoy.empty:
    st.success(":material/check_circle: No hay jugadores activos a evaluar o faltan datos recientes.")
    st.stop()

df_hoy = df_hoy.sort_values(by="Riesgo_%", ascending=False)
alto_riesgo = df_hoy[df_hoy['Riesgo_%'] >= 55]

# --- 1. CABECERA DE ESTADO (Compacta y Profesional) ---
estado_txt = "Motor de IA Predictivo (XGBoost)" if modo_ia else "Motor Algorítmico Científico (Gabbett & Banister)"
st.caption(f"**Motor Activo:** {estado_txt} | Análisis a 7 días vista basado en fatiga residual, EWMA y cinemática.")

c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
from utils.math_helpers import render_kpi_elite
with c_kpi1: render_kpi_elite("Jugadores en Riesgo Crítico", f"{len(alto_riesgo)}", color_borde="#ef4444" if len(alto_riesgo)>0 else "#10b981")
with c_kpi2: render_kpi_elite("Riesgo Medio Plantilla", f"{df_hoy['Riesgo_%'].mean():.1f}%", color_borde="#f59e0b" if df_hoy['Riesgo_%'].mean()>30 else "#C5A059")
with c_kpi3: render_kpi_elite("Ratio A/C Medio", f"{df_hoy['Ratio_AC'].mean():.2f}", color_borde="#10b981" if 0.8 <= df_hoy['Ratio_AC'].mean() <= 1.3 else "#ef4444")

st.markdown("---")

# --- 2. MATRIZ DE RIESGO Y ALARMAS INMINENTES ---
c_graf, c_alertas = st.columns([2, 1])

with c_graf:
    st.markdown("#### :material/track_changes: Matriz de Carga (Sweet Spot)")
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
    st.markdown("#### :material/emergency: Alertas Inminentes")
    if alto_riesgo.empty:
        st.success(":material/check_circle: Plantilla fuera de riesgo crítico. Buen trabajo de gestión de cargas.")
    else:
        for _, row in alto_riesgo.head(3).iterrows():
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #111318, #0b0e14); border: 1px solid #1c1f26; border-left: 4px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center;">
                        <span class="material-symbols-rounded" style="font-size: 1.2rem; color: #ef4444; margin-right: 8px;">warning</span>
                        <strong style="color: #f8fafc; font-size: 1.1rem; text-transform: uppercase;">{row['JUGADOR']}</strong>
                    </div>
                    <span style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 800; font-size: 0.8rem;">{row['Riesgo_%']:.0f}% RIESGO</span>
                </div>
                <div style="font-size: 0.85rem; color: #94a3b8; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                    <div>A/C Int: <b style="color: #f8fafc;">{row['Ratio_AC']:.2f}</b></div>
                    <div>A/C HSR: <b style="color: #f8fafc;">{row['Ratio_AC_HSR']:.2f}</b></div>
                    <div>Strain: <b style="color: #f8fafc;">{row['Strain_7d']:.0f}</b></div>
                    <div>Z-Wellness: <b style="color: #f8fafc;">{row['Z_Wellness']:.1f}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# --- 3. TABLA DE DATOS INTERACTIVA CON BARRAS DE PROGRESO ---
st.markdown("#### :material/list_alt: Evaluación Completa de la Plantilla")
st.caption("Ordenado de mayor a menor riesgo lesional. Haz clic en las cabeceras para reordenar.")

df_display = df_hoy[['JUGADOR', 'Riesgo_%', 'Ratio_AC', 'Ratio_AC_HSR', 'Strain_7d', 'Z_Wellness', 'Dias_Sin_VMax']].copy()
df_display.rename(columns={
    'Riesgo_%': 'Riesgo Global',
    'Ratio_AC': 'A/C (Int)',
    'Ratio_AC_HSR': 'A/C (HSR)',
    'Strain_7d': 'Strain (7d)',
    'Z_Wellness': 'Z-Score Wellness',
    'Dias_Sin_VMax': 'Días sin VMax'
}, inplace=True)

st.dataframe(
    df_display,
    column_config={
        "JUGADOR": st.column_config.TextColumn("Deportista", width="medium"),
        "Riesgo Global": st.column_config.ProgressColumn(
            "Riesgo Inminente (%)",
            help="Probabilidad de sufrir una lesión muscular/tendinosa en los próximos 7 días.",
            format="%.0f%%",
            min_value=0,
            max_value=75, 
        ),
        "A/C (Int)": st.column_config.NumberColumn("A/C (Int)", format="%.2f"),
        "A/C (HSR)": st.column_config.NumberColumn("A/C (HSR)", format="%.2f"),
        "Strain (7d)": st.column_config.NumberColumn("Strain (7d)", format="%.0f UA"),
        "Z-Score Wellness": st.column_config.NumberColumn("Z-Score Wellness", format="%.2f", help="Positivo (+1.5) indica mayor fatiga o peor estado del habitual"),
        "Días sin VMax": st.column_config.NumberColumn("Días sin VMax", format="%.0f d")
    },
    hide_index=True,
    use_container_width=True
)
