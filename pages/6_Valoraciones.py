import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
import uuid
import plotly.express as px
import plotly.graph_objects as go

# Importaciones del ecosistema LoadLab
from utils.math_helpers import safe_float, limpiar_nombre
from database.db_manager import guardar_datos

# --- COMPROBACIÓN DE SEGURIDAD Y SESIÓN ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo.")
    if st.button("Ir al Login principal"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# Funciones de color y CSS global
color_sidebar = st.session_state.get("color_sidebar", "#0a0a0a") 
css_dinamico = f"""
<style>
    [data-testid="stSidebar"] {{
        background-color: {color_sidebar} !important;
        border-right: 1px solid #262626 !important;
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{
        color: #000000 !important;
        font-weight: 800 !important;
    }}
</style>
"""
st.markdown(css_dinamico, unsafe_allow_html=True)
try:
    with open("Style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except:
    pass

def mostrar_tabla_moderna(styler_obj):
    if hasattr(styler_obj, 'data'):
        df_temp = styler_obj.data.copy()
        html_tabla = df_temp.to_html(index=False, classes="modern-table", escape=False)
    else:
        html_tabla = styler_obj.to_html(index=False, classes="modern-table", escape=False)
    css_personalizado = "<style>.modern-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); background-color: white; margin-bottom: 20px; } .modern-table thead tr { background-color: #000000; color: #ffffff; } .modern-table th { padding: 12px 15px; font-weight: bold; text-align: center !important; border-bottom: 2px solid #333333; } .modern-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #eeeeee; } .modern-table tbody tr:hover td { filter: brightness(0.95); }</style>"
    st.markdown(css_personalizado + html_tabla, unsafe_allow_html=True)

st.title("📊 Valoraciones Condicionales")

tab_informes, tab_nuevo, tab_reg = st.tabs(["📈 Informes de valoraciones", "➕ Añadir Nueva Valoración", "📋 Tabla de registros"])

if "val_rom" not in st.session_state:
    st.session_state.val_rom = []

valoraciones = st.session_state.val_rom
jugadores = sorted([j["JUGADOR"] for j in st.session_state.get("plantilla", [])])

# --- FUNCIONES MATEMÁTICAS CIENTÍFICAS ---
def calc_asimetria(der, izq):
    d, i = safe_float(der), safe_float(izq)
    if max(d, i) == 0: return 0.0
    return (abs(d - i) / max(d, i)) * 100

def calcular_rm_cientifico(pesos, vels, peso_corp):
    validas = [(pesos[i], vels[i]) for i in range(len(pesos)) if vels[i] > 0 and pesos[i] > 0]
    if len(validas) > 1:
        kgs_sistema = np.array([x[0] + (peso_corp * 0.89) for x in validas])
        v_array = np.array([x[1] for x in validas])
        z = np.polyfit(kgs_sistema, v_array, 1)
        slope, intercept = z[0], z[1]
        rm_sq_sistema = (0.30 - intercept) / slope if slope < 0 else 0
        rm_sq_barra = round(rm_sq_sistema - (peso_corp * 0.89), 1) if rm_sq_sistema > 0 else 0.0
        return max(rm_sq_barra, 0.0)
    elif len(validas) == 1:
        return round(validas[0][0], 1)
    return 0.0

def tarjeta_kpi(titulo, valor, subtitulo=""):
    st.markdown(f"""
    <div style='background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #dc2626; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e4e4e7;'>
        <div style='font-size: 0.80em; color: #64748b; font-weight: 800; text-transform: uppercase;'>{titulo}</div>
        <div style='font-size: 1.4em; font-weight: 800; color: #0a0a0a;'>{valor}</div>
        {f"<div style='font-size: 0.8em; color: #64748b; margin-top: 4px;'>{subtitulo}</div>" if subtitulo else ""}
    </div>
    """, unsafe_allow_html=True)

def tarjeta_kpi_doble(titulo, val_d, val_i, lbl_d="Der", lbl_i="Izq"):
    st.markdown(f"""
    <div style='background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1c1c1e; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e4e4e7;'>
        <div style='font-size: 0.80em; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 8px;'>{titulo}</div>
        <div style='display: flex; justify-content: space-between;'>
            <div><span style='font-size: 0.85em; color: #64748b;'>{lbl_d}:</span> <span style='font-size: 1.2em; font-weight: 800; color: #dc2626;'>{val_d}</span></div>
            <div><span style='font-size: 0.85em; color: #64748b;'>{lbl_i}:</span> <span style='font-size: 1.2em; font-weight: 800; color: #dc2626;'>{val_i}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def badge_asi_detallado(val, der, izq):
    if val < 10: 
        return f"🟢 {val:.1f}% (Óptimo)"
    else:
        pierna_debil = "Derecha" if safe_float(der) < safe_float(izq) else ("Izquierda" if safe_float(izq) < safe_float(der) else "Ninguna")
        if val <= 15: 
            return f"🟡 {val:.1f}% (Precaución | Débil: {pierna_debil})"
        else: 
            return f"🔴 {val:.1f}% (Riesgo | Débil: {pierna_debil})"

def badge_hq(val): return f"🟢 {val:.2f}" if val >= 0.6 else f"🔴 {val:.2f} (Déficit)"
def badge_nkg_ext(val): return f"🟢 {val:.1f} N/kg" if val >= 4.5 else f"🔴 {val:.1f} N/kg (Débil)"
def badge_nkg_flx(val): return f"🟢 {val:.1f} N/kg" if val >= 3.5 else f"🔴 {val:.1f} N/kg (Débil)"

# ==========================================
# PESTAÑA 1: INFORMES DE VALORACIONES
# ==========================================
with tab_informes:
    st.markdown("### 📈 Informes de Valoraciones y Perfil Individual")
    
    if not jugadores or not valoraciones:
        st.info("No hay datos suficientes para mostrar informes.")
    else:
        cf1, cf2 = st.columns(2)
        
        with cf1:
            jugadores_con_val = sorted(list(set([v.get('jugador') for v in valoraciones])))
            jug_sel = st.selectbox("1. Deportista:", options=jugadores_con_val if jugadores_con_val else ["Sin datos"])
        
        with cf2:
            val_sel_id = None
            if jug_sel and jug_sel != "Sin datos":
                vals_jugador = [v for v in valoraciones if v.get('jugador') == jug_sel]
                vals_jugador = sorted(vals_jugador, key=lambda x: x.get('fecha', ''))
                
                for i, v in enumerate(vals_jugador):
                    v['num_cronologico'] = i + 1
                
                dicc_vals = {row['id']: f"Val. {row['num_cronologico']} ({row['fecha']})" for row in vals_jugador}
                val_sel_id = st.selectbox("2. Nº Valoración:", options=[None] + list(dicc_vals.keys()), format_func=lambda x: dicc_vals[x] if x else "Seleccione informe...")
            else:
                st.selectbox("2. Nº Valoración:", options=["-"])
        
        if val_sel_id is None:
            st.info("👆 Selecciona un deportista y su valoración para desplegar el informe exhaustivo.")
        else:
            v_data = next((v for v in vals_jugador if v['id'] == val_sel_id), None)
            peso_actual = safe_float(v_data.get('peso_corporal', 70.0))
            if peso_actual == 0: peso_actual = 70.0 

            st.markdown("---")
            st.markdown("#### 🤸 Movilidad (Grados)")
            cm1, cm2, cm3 = st.columns(3)
            with cm1: tarjeta_kpi_doble("Rot. Ext. Cadera", v_data.get('mov_rot_ext_d', 0), v_data.get('mov_rot_ext_i', 0))
            with cm2: tarjeta_kpi_doble("Rot. Int. Cadera", v_data.get('mov_rot_int_d', 0), v_data.get('mov_rot_int_i', 0))
            with cm3: tarjeta_kpi_doble("Dorsiflexión Tobillo", v_data.get('mov_dorsi_d', 0), v_data.get('mov_dorsi_i', 0))

            asi_re = calc_asimetria(v_data.get('mov_rot_ext_d', 0), v_data.get('mov_rot_ext_i', 0))
            asi_ri = calc_asimetria(v_data.get('mov_rot_int_d', 0), v_data.get('mov_rot_int_i', 0))
            asi_dor = calc_asimetria(v_data.get('mov_dorsi_d', 0), v_data.get('mov_dorsi_i', 0))

            c_mov1, c_mov2, c_mov3 = st.columns(3)
            c_mov1.info(f"**Asimetría Rot. Ext:** {badge_asi_detallado(asi_re, v_data.get('mov_rot_ext_d', 0), v_data.get('mov_rot_ext_i', 0))}")
            c_mov2.info(f"**Asimetría Rot. Int:** {badge_asi_detallado(asi_ri, v_data.get('mov_rot_int_d', 0), v_data.get('mov_rot_int_i', 0))}")
            c_mov3.info(f"**Asimetría Dorsiflexión:** {badge_asi_detallado(asi_dor, v_data.get('mov_dorsi_d', 0), v_data.get('mov_dorsi_i', 0))}")

            st.markdown("---")
            st.markdown("#### 🦘 Salto y Perfil Vectorial")
            cs1, cs2, cs3, cs4 = st.columns(4)
            with cs1: tarjeta_kpi("SJ Bilateral", f"{v_data.get('sj_bi', 0)} cm")
            with cs2: tarjeta_kpi("CMJ Bilateral", f"{v_data.get('cmj_bi', 0)} cm")
            with cs3: tarjeta_kpi_doble("CMJ Unilateral", f"{v_data.get('cmj_uni_d', 0)} cm", f"{v_data.get('cmj_uni_i', 0)} cm")
            with cs4: tarjeta_kpi_doble("Salto Horizontal", f"{v_data.get('sh_d', 0)} cm", f"{v_data.get('sh_i', 0)} cm")
            
            sj_bi = safe_float(v_data.get('sj_bi', 0))
            cmj_bi = safe_float(v_data.get('cmj_bi', 0))
            cmj_d, cmj_i = v_data.get('cmj_uni_d', 0), v_data.get('cmj_uni_i', 0)
            
            asi_cmj = calc_asimetria(cmj_d, cmj_i)
            cmj_uni_sum = safe_float(cmj_d) + safe_float(cmj_i)
            dbl = round(100 * (cmj_bi / cmj_uni_sum) - 100, 1) if cmj_uni_sum > 0 else 0
            
            if dbl < -10: dbl_txt = f"🟢 {dbl}% (Facilitación Bilateral Óptima)"
            elif dbl < 0: dbl_txt = f"🟡 {dbl}% (Adecuado)"
            else: dbl_txt = f"🔴 {dbl}% (Déficit Bilateral)"
            
            sh_promedio = (safe_float(v_data.get('sh_d', 0)) + safe_float(v_data.get('sh_i', 0))) / 2
            cmj_uni_promedio = cmj_uni_sum / 2
            ratio_vectores = round(sh_promedio / cmj_uni_promedio, 2) if cmj_uni_promedio > 0 else 0
            
            if ratio_vectores > 4.5: perfil_vector = "🏃 Dominancia Horizontal (Acelerador)"
            elif ratio_vectores >= 3.5 and ratio_vectores <= 4.5: perfil_vector = "⚖️ Perfil Equilibrado"
            elif ratio_vectores > 0 and ratio_vectores < 3.5: perfil_vector = "🚀 Dominancia Vertical (Velocidad Punta)"
            else: perfil_vector = "Datos insuficientes"

            eur = round(cmj_bi / sj_bi, 2) if sj_bi > 0 else 0
            if eur > 1.15: eur_txt = f"🟢 {eur} (Excelente elasticidad)"
            elif eur >= 1.05: eur_txt = f"🟡 {eur} (Aceptable)"
            elif eur > 0: eur_txt = f"🔴 {eur} (Déficit elástico)"
            else: eur_txt = "Sin datos"
            
            ca1, ca2, ca3, ca4 = st.columns(4)
            ca1.info(f"**Asimetría Vertical:**\n{badge_asi_detallado(asi_cmj, cmj_d, cmj_i)}")
            ca2.info(f"**Déficit Bilateral (BLD):**\n{dbl_txt}")
            ca3.info(f"**Ratio Vectores (H/V):** {ratio_vectores}\n{perfil_vector}")
            ca4.info(f"**Índice Utilización Excéntrica (EUR):**\n{eur_txt}")

            st.markdown("---")
            st.markdown("#### ⚡ Fuerza Máxima Isométrica y Fuerza Relativa")
            ci1, ci2, ci3 = st.columns(3)
            with ci1: tarjeta_kpi_doble("Extensión (Cuád)", f"{v_data.get('iso_ext_d', 0)} N", f"{v_data.get('iso_ext_i', 0)} N")
            with ci2: tarjeta_kpi_doble("Flexión (Isq)", f"{v_data.get('iso_flx_d', 0)} N", f"{v_data.get('iso_flx_i', 0)} N")
            with ci3: tarjeta_kpi_doble("Aducción", f"{v_data.get('iso_add_d', 0)} N", f"{v_data.get('iso_add_i', 0)} N")
            
            ext_d, ext_i = v_data.get('iso_ext_d', 0), v_data.get('iso_ext_i', 0)
            flx_d, flx_i = v_data.get('iso_flx_d', 0), v_data.get('iso_flx_i', 0)
            add_d, add_i = v_data.get('iso_add_d', 0), v_data.get('iso_add_i', 0)
            
            asi_ext = calc_asimetria(ext_d, ext_i)
            asi_flx = calc_asimetria(flx_d, flx_i)
            asi_add = calc_asimetria(add_d, add_i)
            
            cai1, cai2, cai3 = st.columns(3)
            cai1.info(f"**Asim. Cuádriceps:** {badge_asi_detallado(asi_ext, ext_d, ext_i)}")
            cai2.info(f"**Asim. Isquiosurales:** {badge_asi_detallado(asi_flx, flx_d, flx_i)}")
            cai3.info(f"**Asim. Aducción:** {badge_asi_detallado(asi_add, add_d, add_i)}")
            
            ratio_hq_d = round(safe_float(flx_d) / safe_float(ext_d), 2) if safe_float(ext_d) > 0 else 0
            ratio_hq_i = round(safe_float(flx_i) / safe_float(ext_i), 2) if safe_float(ext_i) > 0 else 0
            f_rel_ext_d = round(safe_float(ext_d) / peso_actual, 2) if peso_actual > 0 else 0
            f_rel_ext_i = round(safe_float(ext_i) / peso_actual, 2) if peso_actual > 0 else 0
            f_rel_flx_d = round(safe_float(flx_d) / peso_actual, 2) if peso_actual > 0 else 0
            f_rel_flx_i = round(safe_float(flx_i) / peso_actual, 2) if peso_actual > 0 else 0
            
            st.markdown("**Ratios Clínicos de Equilibrio y Fuerza Relativa (N/kg)**")
            cr1, cr2, cf_rel1, cf_rel2 = st.columns(4)
            with cr1: st.info(f"**Isq/Cuád (D):** {badge_hq(ratio_hq_d)}")
            with cr2: st.info(f"**Isq/Cuád (I):** {badge_hq(ratio_hq_i)}")
            with cf_rel1: st.info(f"**Cuádriceps (D/I):**\n{badge_nkg_ext(f_rel_ext_d)} | {badge_nkg_ext(f_rel_ext_i)}")
            with cf_rel2: st.info(f"**Isquiosural (D/I):**\n{badge_nkg_flx(f_rel_flx_d)} | {badge_nkg_flx(f_rel_flx_i)}")

            st.markdown("---")
            st.markdown("#### 🏋️‍♂️ Fuerza Máxima (Sentadilla)")
            sq_rm = safe_float(v_data.get('rm_sq'))
            f_rel_sq = round(sq_rm / peso_actual, 2) if peso_actual > 0 else 0
            
            crm1, crm2, crm3 = st.columns(3)
            with crm1: tarjeta_kpi("1RM Sentadilla (VMP 0.3 m/s)", f"{sq_rm} kg")
            with crm2: tarjeta_kpi("Fuerza Relativa Sentadilla", f"{f_rel_sq}x Peso Corporal")
            with crm3:
                ratio_fuerza_salto = round(cmj_bi / f_rel_sq, 1) if f_rel_sq > 0 else 0
                if ratio_fuerza_salto > 25: diag_ratio = "🔴 Déficit de Fuerza"
                elif ratio_fuerza_salto > 0 and ratio_fuerza_salto < 18: diag_ratio = "🟡 Déficit de Potencia"
                elif ratio_fuerza_salto >= 18 and ratio_fuerza_salto <= 25: diag_ratio = "🟢 Transferencia Óptima"
                else: diag_ratio = "Sin datos"
                tarjeta_kpi("Ratio Fuerza-Salto", str(ratio_fuerza_salto), diag_ratio)

            p_sq_data = v_data.get('perfil_sq', {})
            kgs_barra = np.array([k for k, v in zip(p_sq_data.get('kg', []), p_sq_data.get('vel', [])) if k > 0 and v > 0])
            vels = np.array([v for k, v in zip(p_sq_data.get('kg', []), p_sq_data.get('vel', [])) if k > 0 and v > 0])
            
            if len(kgs_barra) > 1:
                # 1. Fuerza real del sistema
                kgs_sistema = kgs_barra + (peso_actual * 0.89)
                z = np.polyfit(kgs_sistema, vels, 1)
                p = np.poly1d(z)
                slope, intercept = z[0], z[1]
                
                # Fiabilidad del test (R^2)
                ss_res = np.sum((vels - p(kgs_sistema))**2)
                ss_tot = np.sum((vels - np.mean(vels))**2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                # 2. Variables teóricas del deportista
                v0 = intercept
                f0_kg_sistema = -intercept / slope if slope < 0 else 0
                f0_kg_barra = max(f0_kg_sistema - (peso_actual * 0.89), 0)
                f0_rel = f0_kg_sistema / peso_actual if peso_actual > 0 else 0
                
                # 3. PERFIL ÓPTIMO DE SAMOZINO Y DESEQUILIBRIO F-V
                pmax_rel = (f0_rel * v0) / 4
                hpo = 0.4  # Distancia de empuje estándar estimada (m) para sentadilla
                
                # Cálculo de la pendiente teórica perfecta para este jugador
                f0_opt = 2 * (pmax_rel / hpo) ** 0.5
                v0_opt = 2 * (pmax_rel * hpo) ** 0.5
                s_fv_opt = -(f0_opt / v0_opt) if v0_opt > 0 else -1
                
                # Pendiente real del jugador (en N/kg/m/s para equiparar a la literatura)
                s_fv_actual = (slope * 9.81) / peso_actual 
                
                # Porcentaje exacto de desequilibrio
                desequilibrio_fv = ((s_fv_actual / s_fv_opt) - 1) * 100 if s_fv_opt != 0 else 0
                
                if desequilibrio_fv < -10:
                    cuadrante = f"🔴 Déficit de Fuerza ({desequilibrio_fv:.1f}%)"
                    pauta_fv = "Priorizar cargas pesadas (>80% 1RM)."
                elif desequilibrio_fv > 10:
                    cuadrante = f"🟡 Déficit de Velocidad (+{desequilibrio_fv:.1f}%)"
                    pauta_fv = "Priorizar trabajo balístico y pliometría pura."
                else:
                    signo = "+" if desequilibrio_fv > 0 else ""
                    cuadrante = f"🟢 Perfil Óptimo ({signo}{desequilibrio_fv:.1f}%)"
                    pauta_fv = "Entrenamiento mixto para desplazar la curva completa."

                # Gráfico
                fig_sq = px.scatter(x=kgs_sistema, y=vels, labels={'x': 'Carga del Sistema (kg)', 'y': 'Velocidad (m/s)'}, title="Perfil F-V (Masa del Sistema)")
                fig_sq.update_traces(marker=dict(size=10, color='#dc2626'))
                x_trend = np.linspace(min(kgs_sistema), max(kgs_sistema), 50)
                fig_sq.add_scatter(x=x_trend, y=p(x_trend), mode='lines', name='Tendencia Real', line=dict(color='#1c1c1e', width=2))
                
                # Añadir la línea óptima teórica para comparación visual
                y_opt = v0_opt + (s_fv_opt / 9.81 * peso_actual) * x_trend
                fig_sq.add_scatter(x=x_trend, y=y_opt, mode='lines', name='Perfil Óptimo', line=dict(dash='dash', color='#10833d', width=2))
                
                fig_sq.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20), legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
                
                c_fig1, c_fig2 = st.columns([1, 1])
                with c_fig1:
                    st.plotly_chart(fig_sq, use_container_width=True)
                with c_fig2:
                    fiabilidad_sq = "🟢 Excelente" if r2 >= 0.95 else ("🟡 Aceptable" if r2 >= 0.90 else "🔴 Pobre (Falta intención)")
                    st.info(f"**Diagnóstico $S_{{fv}}$:** {cuadrante}\n\n**V0:** {round(v0, 2)} m/s (Ópt: {round(v0_opt, 2)})\n**F0 (Barra):** {round(f0_kg_barra, 1)} kg\n\n**Fiabilidad del test ($R^2$):** {round(r2, 3)} ({fiabilidad_sq})\n\n*{pauta_fv}*")

            st.markdown("---")
            st.markdown("#### 🧭 Perfil Evolutivo y Asimetrías")
            
            def obtener_valor_isq(v, p):
                isq_d, isq_i = v.get('iso_flx_d', 0), v.get('iso_flx_i', 0)
                return ((isq_d + isq_i) / 2) / p if p > 0 else 0
            
            def obtener_valor_add(v, p):
                add_d, add_i = v.get('iso_add_d', 0), v.get('iso_add_i', 0)
                return ((add_d + add_i) / 2) / p if p > 0 else 0
                
            def obtener_valor_ext(v, p):
                ext_d, ext_i = v.get('iso_ext_d', 0), v.get('iso_ext_i', 0)
                return ((ext_d + ext_i) / 2) / p if p > 0 else 0
            
            def obtener_valor_sh(v):
                return (safe_float(v.get('sh_d', 0)) + safe_float(v.get('sh_i', 0))) / 2
                
            val_inicial = vals_jugador[0]
            peso_ini = safe_float(val_inicial.get('peso_corporal', 70))
            if peso_ini == 0: peso_ini = 70.0
            
            cmj_ini, cmj_act = safe_float(val_inicial.get('cmj_bi', 0)), safe_float(v_data.get('cmj_bi', 0))
            sh_ini, sh_act = obtener_valor_sh(val_inicial), obtener_valor_sh(v_data)
            sq_ini, sq_act = (safe_float(val_inicial.get('rm_sq', 0)) / peso_ini), (safe_float(v_data.get('rm_sq', 0)) / peso_actual)
            isq_ini, isq_act = obtener_valor_isq(val_inicial, peso_ini), obtener_valor_isq(v_data, peso_actual)
            add_ini, add_act = obtener_valor_add(val_inicial, peso_ini), obtener_valor_add(v_data, peso_actual)
            ext_ini, ext_act = obtener_valor_ext(val_inicial, peso_ini), obtener_valor_ext(v_data, peso_actual)

            max_cmj, max_sh = max(cmj_ini, cmj_act, 1), max(sh_ini, sh_act, 1)
            max_sq, max_ext = max(sq_ini, sq_act, 0.1), max(ext_ini, ext_act, 0.1)
            max_isq, max_add = max(isq_ini, isq_act, 0.1), max(add_ini, add_act, 0.1)

            p_ini = [(cmj_ini/max_cmj)*100, (sh_ini/max_sh)*100, (sq_ini/max_sq)*100, (ext_ini/max_ext)*100, (isq_ini/max_isq)*100, (add_ini/max_add)*100]
            p_act = [(cmj_act/max_cmj)*100, (sh_act/max_sh)*100, (sq_act/max_sq)*100, (ext_act/max_ext)*100, (isq_act/max_isq)*100, (add_act/max_add)*100]
            
            df_radar = pd.DataFrame({
                'Métrica': ['CMJ', 'Salto Horiz.', '1RM SQ', 'F. Cuádriceps', 'F. Isquios', 'F. Aductores'] * 2,
                'Valor': p_ini + p_act,
                'Test': ['Inicial (Base)'] * 6 + ['Actual'] * 6
            })
            
            col_rad, col_tor = st.columns(2)
            with col_rad:
                fig_rad = px.line_polar(df_radar, r='Valor', theta='Métrica', color='Test', line_close=True, color_discrete_map={'Inicial (Base)': '#1c1c1e', 'Actual': '#dc2626'})
                fig_rad.update_traces(fill='toself', opacity=0.4)
                fig_rad.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 100])), height=350, margin=dict(l=20, r=20, t=30, b=20), title="Perfil Evolutivo")
                st.plotly_chart(fig_rad, use_container_width=True)
                
            with col_tor:
                pruebas_uni = [
                    ("Mov: Rot. Ext Cadera", v_data.get('mov_rot_ext_d',0), v_data.get('mov_rot_ext_i',0)),
                    ("Mov: Rot. Int Cadera", v_data.get('mov_rot_int_d',0), v_data.get('mov_rot_int_i',0)),
                    ("Mov: Dorsiflexión", v_data.get('mov_dorsi_d',0), v_data.get('mov_dorsi_i',0)),
                    ("CMJ Unilateral", v_data.get('cmj_uni_d',0), v_data.get('cmj_uni_i',0)),
                    ("Salto Horizontal", v_data.get('sh_d',0), v_data.get('sh_i',0)),
                    ("Fuerza ISO Cuádriceps", v_data.get('iso_ext_d',0), v_data.get('iso_ext_i',0)),
                    ("Fuerza ISO Isquiosurales", v_data.get('iso_flx_d',0), v_data.get('iso_flx_i',0)),
                    ("Fuerza ISO Aductores", v_data.get('iso_add_d',0), v_data.get('iso_add_i',0))
                ]
                
                val_t, txt_t, col_t, pr_t = [], [], [], []
                for n, der, izq in pruebas_uni:
                    d, i_val = safe_float(der), safe_float(izq)
                    max_v = max(d, i_val)
                    if max_v == 0:
                        val_t.append(0); txt_t.append("0%"); col_t.append('#64748b'); pr_t.append(n)
                    else:
                        diff = (abs(d - i_val) / max_v) * 100
                        if d > i_val:
                            val_t.append(diff); txt_t.append(f"{diff:.1f}%"); col_t.append('#10833d'); pr_t.append(n)
                        elif i_val > d:
                            val_t.append(-diff); txt_t.append(f"{diff:.1f}%"); col_t.append('#09274e'); pr_t.append(n)
                        else:
                            val_t.append(0); txt_t.append("0%"); col_t.append('#64748b'); pr_t.append(n)
                            
                df_tor = pd.DataFrame({'Prueba': pr_t, 'Asimetria': val_t, 'Texto': txt_t, 'Color': col_t}).iloc[::-1]
                fig_tor = go.Figure()
                fig_tor.add_trace(go.Bar(y=df_tor['Prueba'], x=df_tor['Asimetria'], orientation='h', marker_color=df_tor['Color'], text=df_tor['Texto'], textposition='outside'))
                max_x = max(abs(df_tor['Asimetria']).max() + 8, 20)
                fig_tor.update_layout(title="Asimetrías Clínicas", xaxis=dict(title="<-- Dom IZQ (Azul)  |  Dom DER (Verde) -->", range=[-max_x, max_x]), height=350, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
                fig_tor.add_vline(x=10, line_width=1.5, line_dash="dash", line_color="#dc2626")
                fig_tor.add_vline(x=-10, line_width=1.5, line_dash="dash", line_color="#dc2626")
                st.plotly_chart(fig_tor, use_container_width=True)

# ==========================================
# PESTAÑA 2: AÑADIR NUEVA VALORACIÓN
# ==========================================
with tab_nuevo:
    if not jugadores:
        st.warning("Primero debes registrar deportistas en la sección de Jugadores.")
    else:
        modo_ingreso = st.radio("Método de registro:", ["📝 Formulario Manual", "📁 Importar desde Excel"], horizontal=True)
        
        if modo_ingreso == "📝 Formulario Manual":
            with st.form("form_nueva_val_detallada"):
                st.markdown("#### ⚙️ Datos Generales")
                cg1, cg2, cg3, cg4 = st.columns(4)
                with cg1: jugador_sel = st.selectbox("Deportista:", options=jugadores)
                with cg2: fecha_test = st.date_input("Fecha:", value=date.today())
                with cg3: lesion = st.radio("¿Lesión activa?", options=["No", "Sí"], horizontal=True, index=0)
                with cg4: peso = st.number_input("Peso (kg):", min_value=30.0, value=70.0, step=0.5)
                
                st.markdown("---")
                st.markdown("#### 🤸 1. Movilidad (Grados)")
                cf1, cf2, cf3, cf4, cf5, cf6 = st.columns(6)
                with cf1: mov_re_d = st.number_input("Rot. Ext. Cadera D", 0.0, 150.0, 0.0)
                with cf2: mov_re_i = st.number_input("Rot. Ext. Cadera I", 0.0, 150.0, 0.0)
                with cf3: mov_ri_d = st.number_input("Rot. Int. Cadera D", 0.0, 150.0, 0.0)
                with cf4: mov_ri_i = st.number_input("Rot. Int. Cadera I", 0.0, 150.0, 0.0)
                with cf5: mov_dor_d = st.number_input("Dorsiflexión D", 0.0, 100.0, 0.0)
                with cf6: mov_dor_i = st.number_input("Dorsiflexión I", 0.0, 100.0, 0.0)

                st.markdown("---")
                st.markdown("#### 🦘 2. Test de Salto (cm)")
                cs1, cs2, cs3, cs4, cs5, cs6 = st.columns(6)
                with cs1: sj_bi = st.number_input("SJ Bilateral", min_value=0.0, value=0.0, step=0.5)
                with cs2: cmj_bi = st.number_input("CMJ Bilateral", min_value=0.0, value=0.0, step=0.5)
                with cs3: cmj_ud = st.number_input("CMJ Uni D.", min_value=0.0, value=0.0, step=0.5)
                with cs4: cmj_ui = st.number_input("CMJ Uni I.", min_value=0.0, value=0.0, step=0.5)
                with cs5: sh_d = st.number_input("Horiz. D", min_value=0.0, value=0.0, step=1.0)
                with cs6: sh_i = st.number_input("Horiz. I", min_value=0.0, value=0.0, step=1.0)

                st.markdown("---")
                st.markdown("#### ⚡ 3. Fuerza Máxima Isométrica (N)")
                ci1, ci2, ci3 = st.columns(3)
                with ci1:
                    st.markdown("**Extensión (Cuád)**")
                    c_ed, c_ei = st.columns(2)
                    with c_ed: iso_ext_d = st.number_input("Der (Ext)", min_value=0.0, value=0.0, step=1.0)
                    with c_ei: iso_ext_i = st.number_input("Izq (Ext)", min_value=0.0, value=0.0, step=1.0)
                with ci2:
                    st.markdown("**Flexión (Isq)**")
                    c_fd, c_fi = st.columns(2)
                    with c_fd: iso_flx_d = st.number_input("Der (Flx)", min_value=0.0, value=0.0, step=1.0)
                    with c_fi: iso_flx_i = st.number_input("Izq (Flx)", min_value=0.0, value=0.0, step=1.0)
                with ci3:
                    st.markdown("**Aducción**")
                    c_ad, c_ai = st.columns(2)
                    with c_ad: iso_add_d = st.number_input("Der (Add)", min_value=0.0, value=0.0, step=1.0)
                    with c_ai: iso_add_i = st.number_input("Izq (Add)", min_value=0.0, value=0.0, step=1.0)

                st.markdown("---")
                st.markdown("#### 🏋️‍♂️ 4. Perfil Carga-Velocidad y 1RM (Sentadilla)")
                c_sq = st.columns(10)
                p_sq, v_sq = [], []
                for s in range(5):
                    with c_sq[s*2]: p_sq.append(st.number_input(f"S{s+1}(kg)", min_value=0.0, step=2.5, key=f"sq_p_{s}"))
                    with c_sq[s*2+1]: v_sq.append(st.number_input(f"S{s+1}(m/s)", min_value=0.0, step=0.01, key=f"sq_v_{s}"))

                rm_sq = calcular_rm_cientifico(p_sq, v_sq, peso)

                st.markdown("---")
                comentarios = st.text_input("Observaciones Generales:")
                
                if st.form_submit_button("💾 Guardar Valoración Completa", use_container_width=True):
                    nuevo_test = {
                        "id": str(uuid.uuid4()), "jugador": jugador_sel, "fecha": str(fecha_test), 
                        "lesion": lesion, "peso_corporal": float(peso),
                        "mov_rot_ext_d": mov_re_d, "mov_rot_ext_i": mov_re_i, "mov_rot_int_d": mov_ri_d, "mov_rot_int_i": mov_ri_i,
                        "mov_dorsi_d": mov_dor_d, "mov_dorsi_i": mov_dor_i,
                        "sj_bi": sj_bi, "cmj_bi": cmj_bi, "cmj_uni_d": cmj_ud, "cmj_uni_i": cmj_ui, "sh_d": sh_d, "sh_i": sh_i,
                        "iso_ext_d": iso_ext_d, "iso_ext_i": iso_ext_i, "iso_flx_d": iso_flx_d, "iso_flx_i": iso_flx_i, "iso_add_d": iso_add_d, "iso_add_i": iso_add_i,
                        "rm_sq": float(rm_sq), "perfil_sq": {"kg": p_sq, "vel": v_sq}, "comentarios": comentarios
                    }
                    st.session_state.val_rom.append(nuevo_test)
                    guardar_datos(modulo="configuracion")
                    st.success("¡Valoración guardada correctamente!")
                    st.rerun()

        else:
            st.markdown("#### 📁 Importación Masiva (Excel)")
            st.info("⚠️ El Excel debe tener la Fila 1 de encabezados y a partir de la Fila 2 los datos en **este orden exacto** (33 columnas):\n\nJugador | Fecha | Lesión (Sí/No) | Peso | Rot. Ext D | Rot. Ext I | Rot. Int D | Rot. Int I | Dorsiflexión D | Dorsiflexión I | SJ Bi | CMJ Bi | CMJ Uni D | CMJ Uni I | Salto Horiz. D | Salto Horiz. I | Iso Ext D | Iso Ext I | Iso Flx D | Iso Flx I | Iso Add D | Iso Add I | S1(kg) | S1(m/s) | S2(kg) | S2(m/s) | S3(kg) | S3(m/s) | S4(kg) | S4(m/s) | S5(kg) | S5(m/s) | Comentarios")

            archivo = st.file_uploader("Sube tu plantilla Excel (.xlsx)", type=["xlsx"])
            
            if archivo and st.button("🚀 Procesar e Importar", type="primary"):
                try:
                    df_import = pd.read_excel(archivo)
                    registros_exitosos = 0
                    
                    for idx, row in df_import.iterrows():
                        nombre_crudo = str(row.iloc[0]).strip()
                        if pd.isna(row.iloc[0]) or not nombre_crudo: continue
                            
                        jug_bd = next((j for j in jugadores if j.lower() == nombre_crudo.lower()), nombre_crudo)
                        
                        fecha_val = str(row.iloc[1])[:10] if not pd.isna(row.iloc[1]) else str(date.today())
                        lesion_val = "Sí" if str(row.iloc[2]).strip().lower() in ["sí", "si", "s", "1", "yes", "y"] else "No"
                        
                        def s(val): return 0.0 if pd.isna(val) else float(val)

                        peso_val = s(row.iloc[3])
                        
                        p_sq = [s(row.iloc[i]) for i in range(22, 32, 2)]
                        v_sq = [s(row.iloc[i]) for i in range(23, 33, 2)]

                        rm_sq = calcular_rm_cientifico(p_sq, v_sq, peso_val)

                        nuevo_test = {
                            "id": str(uuid.uuid4()),
                            "jugador": jug_bd,
                            "fecha": fecha_val,
                            "lesion": lesion_val,
                            "peso_corporal": peso_val,
                            "mov_rot_ext_d": s(row.iloc[4]), "mov_rot_ext_i": s(row.iloc[5]),
                            "mov_rot_int_d": s(row.iloc[6]), "mov_rot_int_i": s(row.iloc[7]),
                            "mov_dorsi_d": s(row.iloc[8]), "mov_dorsi_i": s(row.iloc[9]),
                            "sj_bi": s(row.iloc[10]), "cmj_bi": s(row.iloc[11]), "cmj_uni_d": s(row.iloc[12]), "cmj_uni_i": s(row.iloc[13]),
                            "sh_d": s(row.iloc[14]), "sh_i": s(row.iloc[15]),
                            "iso_ext_d": s(row.iloc[16]), "iso_ext_i": s(row.iloc[17]),
                            "iso_flx_d": s(row.iloc[18]), "iso_flx_i": s(row.iloc[19]),
                            "iso_add_d": s(row.iloc[20]), "iso_add_i": s(row.iloc[21]),
                            "rm_sq": float(rm_sq),
                            "perfil_sq": {"kg": p_sq, "vel": v_sq},
                            "comentarios": str(row.iloc[32]) if len(row.index) > 32 and not pd.isna(row.iloc[32]) else "Importado desde Excel."
                        }
                        st.session_state.val_rom.append(nuevo_test)
                        registros_exitosos += 1
                        
                    if registros_exitosos > 0:
                        guardar_datos(modulo="configuracion")
                        st.success(f"✅ ¡Se han importado {registros_exitosos} valoraciones correctamente!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error general al procesar el Excel. Asegúrate de tener las 33 columnas. Detalle técnico: {e}")

# ==========================================
# PESTAÑA 3: TABLA DE REGISTROS Y GESTIÓN
# ==========================================
with tab_reg:
    st.markdown("### 📋 Tabla de Registros y Gestión")
    
    if not valoraciones:
        st.info("No hay valoraciones registradas todavía.")
    else:
        df_vals = pd.DataFrame(valoraciones)
        
        cf1, cf2 = st.columns(2)
        with cf1:
            lista_jug_unicos = sorted(df_vals['jugador'].dropna().unique())
            filtro_jug = st.selectbox("Filtrar por Deportista:", ["Todos"] + lista_jug_unicos)
            
        df_filtrado = df_vals.copy()
        if filtro_jug != "Todos": df_filtrado = df_filtrado[df_filtrado['jugador'] == filtro_jug]

        renombres = {
            'fecha': 'Fecha', 'jugador': 'Deportista', 'lesion': 'Lesión', 'peso_corporal': 'Peso (kg)',
            'mov_rot_ext_d': 'Rot. Ext D', 'mov_rot_ext_i': 'Rot. Ext I', 'mov_rot_int_d': 'Rot. Int D', 'mov_rot_int_i': 'Rot. Int I', 
            'mov_dorsi_d': 'Dorsi. D', 'mov_dorsi_i': 'Dorsi. I',
            'sj_bi': 'SJ Bi', 'cmj_bi': 'CMJ Bi', 'cmj_uni_d': 'CMJ Uni D', 'cmj_uni_i': 'CMJ Uni I', 'sh_d': 'Salto Horiz D', 'sh_i': 'Salto Horiz I',
            'iso_ext_d': 'Iso Ext D (N)', 'iso_ext_i': 'Iso Ext I (N)', 'iso_flx_d': 'Iso Flex D (N)', 'iso_flx_i': 'Iso Flex I (N)',
            'iso_add_d': 'Iso Add D (N)', 'iso_add_i': 'Iso Add I (N)', 'rm_sq': '1RM Sentadilla (kg)', 'comentarios': 'Comentarios'
        }
        
        cols_base = ['Deportista', 'Fecha', 'Lesión', 'Peso (kg)']
        df_mostrar = df_filtrado.rename(columns=renombres)
        cols_existentes = [c for c in df_mostrar.columns if c in renombres.values()]
        orden_final = cols_base + [c for c in cols_existentes if c not in cols_base]
        
        mostrar_tabla_moderna(df_mostrar[orden_final])

        st.markdown("---")
        st.markdown("#### ⚙️ Gestión: Modificar o Eliminar Registro")
        opciones_gestion = {row['id']: f"{row['jugador']} - {row['fecha']}" for idx, row in df_filtrado.iterrows()}
        val_seleccionada = st.selectbox("Selecciona una valoración para gestionarla:", [None] + list(opciones_gestion.keys()), format_func=lambda x: opciones_gestion[x] if x else "Seleccionar registro...")
        
        if val_seleccionada:
            if st.button("🗑️ Eliminar Registro Definitivamente", type="primary"):
                st.session_state.val_rom = [v for v in st.session_state.val_rom if v['id'] != val_seleccionada]
                guardar_datos(modulo="configuracion")
                st.success("¡Registro eliminado correctamente!")
                st.rerun()
