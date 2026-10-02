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

def tarjeta_kpi(titulo, valor, subtitulo="", tooltip=""):
                tt_html = f" title='{tooltip}'" if tooltip else ""
                icon = " ℹ️" if tooltip else ""
                cursor = "help" if tooltip else "default"
                st.markdown(f"""
                <div{tt_html} style='background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #dc2626; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e4e4e7; cursor: {cursor};'>
                    <div style='font-size: 0.80em; color: #64748b; font-weight: 800; text-transform: uppercase;'>{titulo}{icon}</div>
                    <div style='font-size: 1.4em; font-weight: 800; color: #0a0a0a;'>{valor}</div>
                    {f"<div style='font-size: 0.8em; color: #64748b; margin-top: 4px;'>{subtitulo}</div>" if subtitulo else ""}
                </div>
                """, unsafe_allow_html=True)

def tarjeta_kpi_doble(titulo, val_d, val_i, lbl_d="Der", lbl_i="Izq", tooltip=""):
    tt_html = f" title='{tooltip}'" if tooltip else ""
    icon = " ℹ️" if tooltip else ""
    cursor = "help" if tooltip else "default"
    st.markdown(f"""
    <div{tt_html} style='background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1c1c1e; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e4e4e7; cursor: {cursor};'>
        <div style='font-size: 0.80em; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 8px;'>{titulo}{icon}</div>
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
            
            sh_bi = safe_float(v_data.get('sh_bi', v_data.get('sj_bi', 0))) # Fallback para registros antiguos
            cmj_bi = safe_float(v_data.get('cmj_bi', 0))
            cmj_d, cmj_i = v_data.get('cmj_uni_d', 0), v_data.get('cmj_uni_i', 0)
            sh_d, sh_i = v_data.get('sh_d', 0), v_data.get('sh_i', 0)
            
            with cs1: tarjeta_kpi("Salto Horiz. Bilateral", f"{sh_bi} cm")
            with cs2: tarjeta_kpi("CMJ Bilateral", f"{cmj_bi} cm")
            with cs3: tarjeta_kpi_doble("CMJ Unilateral", f"{cmj_d} cm", f"{cmj_i} cm")
            with cs4: tarjeta_kpi_doble("Salto Horiz. Unilateral", f"{sh_d} cm", f"{sh_i} cm")
            
            asi_cmj = calc_asimetria(cmj_d, cmj_i)
            asi_sh = calc_asimetria(sh_d, sh_i)
            
            cmj_uni_sum = safe_float(cmj_d) + safe_float(cmj_i)
            dbl = round(100 * (cmj_bi / cmj_uni_sum) - 100, 1) if cmj_uni_sum > 0 else 0
            
            if dbl < -10: dbl_txt = "🟢 Facilitación Bilateral Óptima"
            elif dbl < 0: dbl_txt = "🟡 Adecuado"
            else: dbl_txt = "🔴 Déficit Bilateral"
            
            ratio_vectores = round(sh_bi / cmj_bi, 2) if cmj_bi > 0 else 0
            if ratio_vectores > 4.5: perfil_vector = "🏃 Dominancia Horizontal (Acelerador)"
            elif ratio_vectores >= 3.5 and ratio_vectores <= 4.5: perfil_vector = "⚖️ Perfil Equilibrado"
            elif ratio_vectores > 0 and ratio_vectores < 3.5: perfil_vector = "🚀 Dominancia Vertical (Velocidad Punta)"
            else: perfil_vector = "Datos insuficientes"

            ca1, ca2, ca3, ca4 = st.columns(4)
            with ca1: tarjeta_kpi("Asimetría Vertical", f"{asi_cmj:.1f}%", badge_asi_detallado(asi_cmj, cmj_d, cmj_i).split(' ', 1)[1])
            with ca2: tarjeta_kpi("Asimetría Horizontal", f"{asi_sh:.1f}%", badge_asi_detallado(asi_sh, sh_d, sh_i).split(' ', 1)[1])
            with ca3: tarjeta_kpi("Déficit Bilateral (BLD)", f"{dbl}%", dbl_txt, tooltip="Óptimo: < -10% | Adecuado: < 0% | Déficit: > 0%")
            with ca4: tarjeta_kpi("Ratio Vectores (H/V)", str(ratio_vectores), perfil_vector, tooltip="Dom. Vertical: < 3.5 | Equilibrado: 3.5 - 4.5 | Dom. Horizontal: > 4.5")

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
            with cr1: tarjeta_kpi("Isq/Cuád (D)", badge_hq(ratio_hq_d).split(' ', 1)[0], badge_hq(ratio_hq_d).split(' ', 1)[1], tooltip="Óptimo: > 0.60 (Previene lesiones de isquiosurales)")
            with cr2: tarjeta_kpi("Isq/Cuád (I)", badge_hq(ratio_hq_i).split(' ', 1)[0], badge_hq(ratio_hq_i).split(' ', 1)[1], tooltip="Óptimo: > 0.60 (Previene lesiones de isquiosurales)")
            with cf_rel1: tarjeta_kpi("Cuádriceps (D/I)", f"{f_rel_ext_d:.1f} | {f_rel_ext_i:.1f} N/kg", tooltip="Óptimo: > 4.5 N/kg (Previene patología rotuliana y LCA)")
            with cf_rel2: tarjeta_kpi("Isquiosural (D/I)", f"{f_rel_flx_d:.1f} | {f_rel_flx_i:.1f} N/kg", tooltip="Óptimo: > 3.5 N/kg")

            st.markdown("---")
            st.markdown("#### 🏋️‍♂️ Fuerza Máxima (Sentadilla)")
            sq_rm = safe_float(v_data.get('rm_sq', v_data.get('rm_sentadilla', 0)))
            f_rel_sq = round(sq_rm / peso_actual, 2) if peso_actual > 0 else 0
            
            crm1, crm2, crm3 = st.columns(3)
            with crm1: tarjeta_kpi("1RM Sentadilla (VMP 0.3 m/s)", f"{sq_rm} kg")
            with crm2: tarjeta_kpi("Fuerza Relativa Sentadilla", f"{f_rel_sq}x Peso", tooltip="Élite: > 2.0x | Óptimo: > 1.8x | Bueno: > 1.5x")
            with crm3:
                ratio_fuerza_salto = round(cmj_bi / f_rel_sq, 1) if f_rel_sq > 0 else 0
                if ratio_fuerza_salto > 25: diag_ratio = "🔴 Déficit de Fuerza"
                elif ratio_fuerza_salto > 0 and ratio_fuerza_salto < 18: diag_ratio = "🟡 Déficit de Potencia"
                elif ratio_fuerza_salto >= 18 and ratio_fuerza_salto <= 25: diag_ratio = "🟢 Transferencia Óptima"
                else: diag_ratio = "Sin datos"
                tarjeta_kpi("Ratio Fuerza-Salto", str(ratio_fuerza_salto), diag_ratio, tooltip="Déficit de Potencia: < 18 | Óptimo: 18 - 25 | Déficit de Fuerza: > 25")

            p_sq_data = v_data.get('perfil_sq', {})
            kgs_barra = np.array([k for k, v in zip(p_sq_data.get('kg', []), p_sq_data.get('vel', [])) if k > 0 and v > 0])
            vels = np.array([v for k, v in zip(p_sq_data.get('kg', []), p_sq_data.get('vel', [])) if k > 0 and v > 0])
            
            if len(kgs_barra) > 1:
                # 1. Fuerza real del sistema (Barra + Peso corporal parcial)
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
                
                # Fuerza Relativa en Newtons (N/kg) para diagnóstico
                f0_rel_N = (f0_kg_sistema * 9.81) / peso_actual if peso_actual > 0 else 0
                
                # 3. DIAGNÓSTICO DE FUERZA (Basado en umbrales, sin línea óptima)
                # Umbrales estándar en sentadilla: F0 > 25 N/kg | V0 > 1.5 m/s
                if f0_rel_N >= 25.0 and v0 >= 1.5:
                    cuadrante = "🟢 Perfil F-V Equilibrado"
                    pauta_fv = "Mantenimiento general."
                elif f0_rel_N < 25.0 and v0 >= 1.5:
                    cuadrante = "🔴 Déficit de Fuerza"
                    pauta_fv = "Priorizar cargas pesadas (>80% 1RM) y fuerza máxima."
                elif f0_rel_N >= 25.0 and v0 < 1.5:
                    cuadrante = "🟡 Déficit de Velocidad"
                    pauta_fv = "Priorizar trabajo de potencia, balísticos y pliometría."
                else:
                    cuadrante = "🔴 Déficit Global"
                    pauta_fv = "Requiere mejora integral de fuerza y velocidad."

                # 4. GRÁFICO LIMPIO (Desde el Origen 0,0)
                fig_sq = px.scatter(x=kgs_sistema, y=vels, labels={'x': 'Carga del Sistema (kg)', 'y': 'Velocidad (m/s)'}, title="Perfil F-V (Masa del Sistema)")
                fig_sq.update_traces(marker=dict(size=10, color='#dc2626'))
                
                # Línea real (hasta su F0 en kg)
                x_trend_real = np.linspace(0, f0_kg_sistema, 50)
                fig_sq.add_scatter(x=x_trend_real, y=p(x_trend_real), mode='lines', name='Tendencia Real', line=dict(color='#1c1c1e', width=2))
                
                # Ajuste de ejes para que nazca en 0,0
                fig_sq.update_xaxes(range=[0, f0_kg_sistema * 1.05], zeroline=True, zerolinewidth=1, zerolinecolor='#e4e4e7')
                fig_sq.update_yaxes(range=[0, v0 * 1.05], zeroline=True, zerolinewidth=1, zerolinecolor='#e4e4e7')
                
                fig_sq.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20), legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99))
                
                c_fig1, c_fig2 = st.columns([1.2, 1])
                with c_fig1:
                    st.plotly_chart(fig_sq, use_container_width=True)
                with c_fig2:
                    fiabilidad_sq = "🟢 Excelente" if r2 >= 0.95 else ("🟡 Aceptable" if r2 >= 0.90 else "🔴 Pobre (Falta intención)")
                    st.info(f"**Diagnóstico:** {cuadrante}\n\n**V0:** {round(v0, 2)} m/s | **F0 (Barra):** {round(f0_kg_barra, 1)} kg\n\n**F0 Relativa:** {round(f0_rel_N, 1)} N/kg\n\n**Fiabilidad del test ($R^2$):** {round(r2, 3)} ({fiabilidad_sq})\n\n*{pauta_fv}*")

            st.markdown("---")
            st.markdown("#### 🧭 Perfil Evolutivo y Asimetrías")
            
            col_rad, col_tor = st.columns(2)
            with col_rad:
                opciones_baseline = ["Media del Equipo"]
                if len(vals_jugador) > 1:
                    opciones_baseline.extend([f"Val. {v['num_cronologico']} ({v['fecha']})" for v in vals_jugador if v['id'] != val_sel_id])
                
                baseline_sel = st.selectbox("Comparar evolución actual contra:", opciones_baseline)
                
                # Función auxiliar para unificar la extracción de KPIs para el radar
                def extraer_kpis_radar(v_obj, peso_ref):
                    c = safe_float(v_obj.get('cmj_bi', 0))
                    sh = safe_float(v_obj.get('sh_bi', v_obj.get('sj_bi', 0)))
                    sq = safe_float(v_obj.get('rm_sq', v_obj.get('rm_sentadilla', 0))) / peso_ref if peso_ref > 0 else 0
                    isq = ((safe_float(v_obj.get('iso_flx_d', 0)) + safe_float(v_obj.get('iso_flx_i', 0))) / 2) / peso_ref if peso_ref > 0 else 0
                    add = ((safe_float(v_obj.get('iso_add_d', 0)) + safe_float(v_obj.get('iso_add_i', 0))) / 2) / peso_ref if peso_ref > 0 else 0
                    ext = ((safe_float(v_obj.get('iso_ext_d', 0)) + safe_float(v_obj.get('iso_ext_i', 0))) / 2) / peso_ref if peso_ref > 0 else 0
                    return c, sh, sq, ext, isq, add

                if baseline_sel == "Media del Equipo":
                    df_eq = pd.DataFrame(valoraciones)
                    val_ref = {}
                    for col in ['peso_corporal', 'cmj_bi', 'sh_bi', 'sj_bi', 'rm_sq', 'rm_sentadilla', 'iso_ext_d', 'iso_ext_i', 'iso_flx_d', 'iso_flx_i', 'iso_add_d', 'iso_add_i']:
                        if col in df_eq.columns:
                            val_ref[col] = df_eq[col].apply(safe_float).mean()
                        else:
                            val_ref[col] = 0.0
                    peso_ini = val_ref['peso_corporal'] if val_ref['peso_corporal'] > 0 else 70.0
                    label_ref = "Media del Equipo"
                else:
                    val_ref = next(v for v in vals_jugador if f"Val. {v['num_cronologico']} ({v['fecha']})" == baseline_sel)
                    peso_ini = safe_float(val_ref.get('peso_corporal', 70))
                    if peso_ini == 0: peso_ini = 70.0
                    label_ref = baseline_sel

                cmj_ref, sh_ref, sq_ref, ext_ref, isq_ref, add_ref = extraer_kpis_radar(val_ref, peso_ini)
                cmj_act, sh_act, sq_act, ext_act, isq_act, add_act = extraer_kpis_radar(v_data, peso_actual)

                max_cmj, max_sh = max(cmj_ref, cmj_act, 1), max(sh_ref, sh_act, 1)
                max_sq, max_ext = max(sq_ref, sq_act, 0.1), max(ext_ref, ext_act, 0.1)
                max_isq, max_add = max(isq_ref, isq_act, 0.1), max(add_ref, add_act, 0.1)

                p_ref = [(cmj_ref/max_cmj)*100, (sh_ref/max_sh)*100, (sq_ref/max_sq)*100, (ext_ref/max_ext)*100, (isq_ref/max_isq)*100, (add_ref/max_add)*100]
                p_act = [(cmj_act/max_cmj)*100, (sh_act/max_sh)*100, (sq_act/max_sq)*100, (ext_act/max_ext)*100, (isq_act/max_isq)*100, (add_act/max_add)*100]
                
                df_radar = pd.DataFrame({
                    'Métrica': ['CMJ', 'Salto Horiz.', '1RM SQ', 'F. Cuádriceps', 'F. Isquios', 'F. Aductores'] * 2,
                    'Valor': p_ref + p_act,
                    'Test': [label_ref] * 6 + ['Actual'] * 6
                })
                
                fig_rad = px.line_polar(df_radar, r='Valor', theta='Métrica', color='Test', line_close=True, color_discrete_map={label_ref: '#1c1c1e', 'Actual': '#dc2626'})
                fig_rad.update_traces(fill='toself', opacity=0.4)
                fig_rad.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 100])), height=350, margin=dict(l=20, r=20, t=30, b=20), legend=dict(yanchor="top", y=-0.1, xanchor="center", x=0.5, orientation="h"))
                st.plotly_chart(fig_rad, use_container_width=True)

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
                with cs1: sh_bi = st.number_input("Salto Horiz. Bi", min_value=0.0, value=0.0, step=1.0)
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
                        "sh_bi": sh_bi, "cmj_bi": cmj_bi, "cmj_uni_d": cmj_ud, "cmj_uni_i": cmj_ui, "sh_d": sh_d, "sh_i": sh_i,
                        "iso_ext_d": iso_ext_d, "iso_ext_i": iso_ext_i, "iso_flx_d": iso_flx_d, "iso_flx_i": iso_flx_i, "iso_add_d": iso_add_d, "iso_add_i": iso_add_i,
                        "rm_sq": float(rm_sq), "perfil_sq": {"kg": p_sq, "vel": v_sq}, "comentarios": comentarios
                    }
                    st.session_state.val_rom.append(nuevo_test)
                    guardar_datos(modulo="configuracion")
                    st.success("¡Valoración guardada correctamente!")
                    st.rerun()

        else:
            st.markdown("#### 📁 Importación Masiva (Excel)")
            st.info("⚠️ El Excel debe tener la Fila 1 de encabezados y a partir de la Fila 2 los datos en **este orden exacto** (33 columnas):\n\nJugador | Fecha | Lesión (Sí/No) | Peso | Rot. Ext D | Rot. Ext I | Rot. Int D | Rot. Int I | Dorsiflexión D | Dorsiflexión I | Salto Horiz. Bi | CMJ Bi | CMJ Uni D | CMJ Uni I | Salto Horiz. D | Salto Horiz. I | Iso Ext D | Iso Ext I | Iso Flx D | Iso Flx I | Iso Add D | Iso Add I | S1(kg) | S1(m/s) | S2(kg) | S2(m/s) | S3(kg) | S3(m/s) | S4(kg) | S4(m/s) | S5(kg) | S5(m/s) | Comentarios")

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
                            "sh_bi": s(row.iloc[10]), "cmj_bi": s(row.iloc[11]), "cmj_uni_d": s(row.iloc[12]), "cmj_uni_i": s(row.iloc[13]),
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
            'sh_bi': 'Salto Horiz Bi', 'cmj_bi': 'CMJ Bi', 'cmj_uni_d': 'CMJ Uni D', 'cmj_uni_i': 'CMJ Uni I', 'sh_d': 'Salto Horiz D', 'sh_i': 'Salto Horiz I',
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
