import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importar las herramientas visuales
from utils.math_helpers import *
from database.db_manager import *

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning(":material/warning: La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    st.stop()

st.title(":material/query_stats: Estadísticas de Rendimiento")

aplicar_color_sidebar()

from datetime import date
hoy_stats_str = str(date.today())
partidos_totales = [
    s for s in st.session_state.sesiones 
    if "Partido" in s.get("tipo", "") and (
        bool(s.get("estadisticas_partido")) or 
        s.get("informe_generado", False) or 
        (s.get("fecha", "9999-12-31") < hoy_stats_str and (s.get("goles_favor") is not None or s.get("goles_contra") is not None))
    )
]

# ==========================================
# 1. FUNCIONES AUXILIARES
# ==========================================
def filtrar_partidos(competicion):
    if competicion == "Global":
        return partidos_totales
    elif competicion == "Amistosos":
        return [p for p in partidos_totales if p.get("tipo") == "Partido Amistoso"]
    else:
        return [p for p in partidos_totales if p.get("tipo") == "Partido Oficial" and p.get("competicion") == competicion]

tab_equipo, tab_pizarra, tab_jugadores, tab_rivales = st.tabs([
    ":material/shield: Estadísticas de Equipo", 
    ":material/developer_board: Pizarra Táctica & Sinergias",
    ":material/groups: Estadísticas de Jugadores", 
    ":material/sports_martial_arts: Estadísticas de Rival"
])
# ==========================================
# 🛡️ PESTAÑA 1: ESTADÍSTICAS DE EQUIPO
# ==========================================
with tab_equipo:
    col_comp1_eq, col_comp2_eq = st.columns([1, 3])
    filtro_competicion_eq = col_comp1_eq.selectbox(
        "▪️ Filtro de Competición:", 
        ["Liga", "Copa", "Amistosos", "Global"],
        key="filtro_comp_eq"
    )
    partidos_eq = filtrar_partidos(filtro_competicion_eq)
    
    st.markdown(f"### :material/emoji_events: Balance de Resultados | {filtro_competicion_eq}")
    
    totales = {
        "Casa": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}, 
        "Fuera": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}
    }
    
    for p in partidos_eq:
        cond = p.get("condicion", "Casa")
        if cond not in totales: cond = "Casa"
        
        gf = int(safe_float(p.get("goles_favor", 0)))
        gc = int(safe_float(p.get("goles_contra", 0)))
        
        totales[cond]["P"] += 1
        totales[cond]["GF"] += gf
        totales[cond]["GC"] += gc
        
        if gf > gc: totales[cond]["V"] += 1
        elif gf == gc: totales[cond]["E"] += 1
        else: totales[cond]["D"] += 1
        
    pj = totales["Casa"]["P"] + totales["Fuera"]["P"]
    v = totales["Casa"]["V"] + totales["Fuera"]["V"]
    e = totales["Casa"]["E"] + totales["Fuera"]["E"]
    d = totales["Casa"]["D"] + totales["Fuera"]["D"]
    gf = totales["Casa"]["GF"] + totales["Fuera"]["GF"]
    gc = totales["Casa"]["GC"] + totales["Fuera"]["GC"]
    dif = gf - gc
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Jugados", pj)
    c2.metric("Victorias", v)
    c3.metric("Empates", e)
    c4.metric("Derrotas", d)
    c5.metric("G. Favor", gf)
    c6.metric("G. Contra", gc)
    c7.metric("Dif. Goles", f"+{dif}" if dif > 0 else str(dif))
    
    st.markdown("---")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### :material/home: Rendimiento como Local")
        pj_casa = totales["Casa"]["P"]
        pts_casa = (totales["Casa"]["V"] * 3) + (totales["Casa"]["E"] * 1)
        pts_pp_casa = (pts_casa / pj_casa) if pj_casa > 0 else 0
        gf_pp_casa = (totales["Casa"]["GF"] / pj_casa) if pj_casa > 0 else 0
        gc_pp_casa = (totales["Casa"]["GC"] / pj_casa) if pj_casa > 0 else 0
        
        df_casa = pd.DataFrame([{
            "PJ": pj_casa, "V": totales["Casa"]["V"], "E": totales["Casa"]["E"], "D": totales["Casa"]["D"], 
            "GF": totales["Casa"]["GF"], "GC": totales["Casa"]["GC"], 
            "Pts": pts_casa, "Pts/P": pts_pp_casa,
            "GF/P": gf_pp_casa, "GC/P": gc_pp_casa
        }])
        mostrar_tabla_moderna(df_casa.style.hide(axis="index").format({"Pts/P": "{:.2f}", "GF/P": "{:.2f}", "GC/P": "{:.2f}"}))
        
    with col_t2:
        st.markdown("#### :material/flight_takeoff: Rendimiento como Visitante")
        pj_fuera = totales["Fuera"]["P"]
        pts_fuera = (totales["Fuera"]["V"] * 3) + (totales["Fuera"]["E"] * 1)
        pts_pp_fuera = (pts_fuera / pj_fuera) if pj_fuera > 0 else 0
        gf_pp_fuera = (totales["Fuera"]["GF"] / pj_fuera) if pj_fuera > 0 else 0
        gc_pp_fuera = (totales["Fuera"]["GC"] / pj_fuera) if pj_fuera > 0 else 0
        
        df_fuera = pd.DataFrame([{
            "PJ": pj_fuera, "V": totales["Fuera"]["V"], "E": totales["Fuera"]["E"], "D": totales["Fuera"]["D"], 
            "GF": totales["Fuera"]["GF"], "GC": totales["Fuera"]["GC"],
            "Pts": pts_fuera, "Pts/P": pts_pp_fuera,
            "GF/P": gf_pp_fuera, "GC/P": gc_pp_fuera
        }])
        mostrar_tabla_moderna(df_fuera.style.hide(axis="index").format({"Pts/P": "{:.2f}", "GF/P": "{:.2f}", "GC/P": "{:.2f}"}))
    st.markdown("---")
    # =========================================================================
    # ⏱️ A2. DINÁMICA TEMPORAL DE GOLES (TRAMOS DE 15') Y SOSTENIBILIDAD FINAL
    # =========================================================================
    st.markdown("#### :material/timer: Dinámica Temporal de Goles (Tramos de 15') e Índice de Sostenibilidad")
    st.caption("Analiza en qué tramos del partido el equipo es más letal o vulnerable a partir de los minutos de gol registrados.")

    tramos_labels = ["1-15'", "16-30'", "31-45'+", "46-60'", "61-75'", "76-90'+"]
    gf_tramos = {t: 0 for t in tramos_labels}
    gc_tramos = {t: 0 for t in tramos_labels}

    def asignar_tramo_15(minuto):
        m = int(safe_float(minuto))
        if m <= 15: return "1-15'"
        elif m <= 30: return "16-30'"
        elif m <= 45: return "31-45'+"
        elif m <= 60: return "46-60'"
        elif m <= 75: return "61-75'"
        else: return "76-90'+"

    for p in partidos_eq:
        ev = p.get("estadisticas_partido", {}).get("_eventos_goles", {})
        for mgf in ev.get("gf", []):
            if safe_float(mgf) > 0: gf_tramos[asignar_tramo_15(mgf)] += 1
        for mgc in ev.get("gc", []):
            if safe_float(mgc) > 0: gc_tramos[asignar_tramo_15(mgc)] += 1

    total_gf_ev = sum(gf_tramos.values())
    total_gc_ev = sum(gc_tramos.values())

    if total_gf_ev == 0 and total_gc_ev == 0:
        st.info(":material/info: Registra los minutos exactos de los goles en 'Entrenamiento -> Sesiones -> Stats Partido' para desbloquear la distribución por tramos de 15 minutos.")
    else:
        df_tramos = pd.DataFrame({
            "Tramo": tramos_labels,
            "Goles a Favor": [gf_tramos[t] for t in tramos_labels],
            "Goles en Contra": [gc_tramos[t] for t in tramos_labels]
        })
        df_tramos["Balance"] = df_tramos["Goles a Favor"] - df_tramos["Goles en Contra"]

        tramo_letal = max(gf_tramos, key=gf_tramos.get) if total_gf_ev > 0 else "-"
        tramo_vulnerable = max(gc_tramos, key=gc_tramos.get) if total_gc_ev > 0 else "-"
        gf_ult30 = gf_tramos["61-75'"] + gf_tramos["76-90'+"]
        gc_ult30 = gc_tramos["61-75'"] + gc_tramos["76-90'+"]
        bal_ult30 = gf_ult30 - gc_ult30

        ck_t1, ck_t2, ck_t3, ck_t4 = st.columns(4)
        with ck_t1: render_kpi_elite("Tramo Más Letal", f"{tramo_letal}", subtitulo=f"{gf_tramos.get(tramo_letal, 0)} goles anotados", color_borde="#10b981")
        with ck_t2: render_kpi_elite("Tramo Más Vulnerable", f"{tramo_vulnerable}", subtitulo=f"{gc_tramos.get(tramo_vulnerable, 0)} goles encajados", color_borde="#ef4444")
        with ck_t3: render_kpi_elite("Balance Últimos 30' (61-90')", f"{bal_ult30:+d}", subtitulo=f"{gf_ult30} GF vs {gc_ult30} GC", color_borde="#10b981" if bal_ult30 >= 0 else "#ef4444")
        with ck_t4:
            pct_gc_final = (gc_ult30 / total_gc_ev * 100) if total_gc_ev > 0 else 0.0
            est_sost = "Sólido al final" if pct_gc_final <= 35 else ("Alerta fatiga final" if pct_gc_final > 45 else "Estándar")
            render_kpi_elite("% GC en Últimos 30'", f"{pct_gc_final:.0f}%", subtitulo=est_sost, color_borde="#10b981" if pct_gc_final <= 35 else "#f59e0b")

        fig_tramos = go.Figure()
        fig_tramos.add_trace(go.Bar(x=df_tramos["Tramo"], y=df_tramos["Goles a Favor"], name="Goles a Favor", marker_color="#10b981", text=df_tramos["Goles a Favor"], textposition="outside"))
        fig_tramos.add_trace(go.Bar(x=df_tramos["Tramo"], y=df_tramos["Goles en Contra"], name="Goles en Contra", marker_color="#ef4444", text=df_tramos["Goles en Contra"], textposition="outside"))
        fig_tramos.update_layout(barmode="group", height=320, title="Distribución de Goles por Tramos de 15 Minutos", yaxis_title="Nº de Goles", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_tramos, use_container_width=True)

    st.markdown("---")
    # =========================================================================
    # 🧬 B3 & B7. ADN FÍSICO DE LA VICTORIA Y RENDIMIENTO CLIMATOLÓGICO
    # =========================================================================
    col_adn, col_clima_st = st.columns(2)

    with col_adn:
        st.markdown("#### :material/biotech: ADN Físico del Resultado (GPS vs. Marcador)")
        st.caption("Exigencia física media del equipo (normalizada a 90') según el resultado obtenido.")
        registros_adn = []
        for p in partidos_eq:
            gf_p = int(safe_float(p.get("goles_favor", 0)))
            gc_p = int(safe_float(p.get("goles_contra", 0)))
            res_p = "Victoria" if gf_p > gc_p else ("Empate" if gf_p == gc_p else "Derrota")
            
            datos_inf = [d for d in p.get("datos_informe", []) if d.get("POS") != "POR" and safe_float(d.get("DIS", 0)) > 0]
            if datos_inf:
                min_sum = sum(safe_float(d.get("MIN_GPS", d.get("MIN", 0))) for d in datos_inf)
                if min_sum > 0:
                    registros_adn.append({
                        "Resultado": res_p,
                        "DIS (km/90')": (sum(safe_float(d.get("DIS", 0)) for d in datos_inf) / min_sum) * 90.0,
                        "HSR (m/90')": (sum(safe_float(d.get("DIS AI", d.get("HID >21", 0))) for d in datos_inf) / min_sum) * 90.0,
                        "Sprints (/90')": (sum(safe_float(d.get("Nº SPR", d.get("SPR >24", 0))) for d in datos_inf) / min_sum) * 90.0,
                        "ACC+DCC (/90')": (sum(safe_float(d.get("ACC", 0)) + safe_float(d.get("DCC", 0)) for d in datos_inf) / min_sum) * 90.0
                    })
        if registros_adn:
            df_adn = pd.DataFrame(registros_adn).groupby("Resultado").agg(
                Partidos=("DIS (km/90')", "count"),
                DIS_km=("DIS (km/90')", "mean"),
                HSR_m=("HSR (m/90')", "mean"),
                Sprints=("Sprints (/90')", "mean"),
                ACC_DCC=("ACC+DCC (/90')", "mean")
            ).reindex(["Victoria", "Empate", "Derrota"]).dropna(how="all").reset_index()
            df_adn = df_adn.rename(columns={"DIS_km": "DIS (km)", "HSR_m": "HSR (m)", "ACC_DCC": "ACC+DCC"})
            mostrar_tabla_moderna(df_adn.style.hide(axis="index").format({"Partidos": "{:.0f}", "DIS (km)": "{:.2f}", "HSR (m)": "{:.0f}", "Sprints": "{:.1f}", "ACC+DCC": "{:.0f}"}).background_gradient(subset=["HSR (m)", "DIS (km)"], cmap="Blues"))
        else:
            st.info("Procesa datos GPS en los partidos para correlacionar el despliegue físico con las victorias.")

    with col_clima_st:
        st.markdown("#### :material/partly_cloudy_day: Rendimiento Contextual y Climatológico")
        st.caption("Balance competitivo y puntos por partido (Pts/P) según la meteorología registrada.")
        reg_clima = []
        for p in partidos_eq:
            gf_p = int(safe_float(p.get("goles_favor", 0)))
            gc_p = int(safe_float(p.get("goles_contra", 0)))
            pts_p = 3 if gf_p > gc_p else (1 if gf_p == gc_p else 0)
            cl = p.get("clima") or {}
            estado_cl = cl.get("estado", "Sin datos") if isinstance(cl, dict) else "Sin datos"
            temp_cl = safe_float(cl.get("temp", 0)) if isinstance(cl, dict) else 0
            reg_clima.append({"Clima": estado_cl, "PJ": 1, "V": 1 if pts_p==3 else 0, "E": 1 if pts_p==1 else 0, "D": 1 if pts_p==0 else 0, "GF": gf_p, "GC": gc_p, "Pts": pts_p, "Temp": temp_cl})
        if reg_clima:
            df_cl = pd.DataFrame(reg_clima).groupby("Clima").agg(
                PJ=("PJ", "sum"), V=("V", "sum"), E=("E", "sum"), D=("D", "sum"),
                GF=("GF", "sum"), GC=("GC", "sum"), Pts=("Pts", "sum"), Temp_Media=("Temp", "mean")
            ).reset_index()
            df_cl["Pts/P"] = df_cl["Pts"] / df_cl["PJ"]
            df_cl = df_cl.rename(columns={"Temp_Media": "Temp. Media (°C)"})
            mostrar_tabla_moderna(df_cl[["Clima", "PJ", "V", "E", "D", "GF", "GC", "Pts/P", "Temp. Media (°C)"]].style.hide(axis="index").format({"Pts/P": "{:.2f}", "Temp. Media (°C)": "{:.1f}°C"}))
        else:
            st.info("No hay partidos suficientes para evaluar el impacto climatológico.")
            
    # WIDGETS DE LIGA
    if filtro_competicion_eq == "Liga":
        comp_id = st.session_state.get("lapreferente_comp_id", "26710")
        st.markdown("---")
        st.markdown("### :material/analytics: Jornada y Clasificación en Vivo (Liga)")
        
        col_widget1, col_widget2 = st.columns(2)
        with col_widget1:
            st.markdown("#### :material/list_alt: Clasificación")
            url_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="570" src="{url_clasif}"></iframe>', 
                height=590, scrolling=True
            )
        with col_widget2:
            st.markdown("#### :material/sports_soccer: Resultados y Próxima Jornada")
            url_res_actual = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            url_res_prox = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&proximaJornada=1&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            
            st.components.v1.html(f'<iframe style="border:0px; width:100%; margin-bottom: -15px;" height="340" src="{url_res_actual}" scrolling="no"></iframe>', height=345, scrolling=False)
            st.components.v1.html(f'<iframe style="border:0px; width:100%;" height="340" src="{url_res_prox}" scrolling="no"></iframe>', height=345, scrolling=False)

    # WIDGETS DE COPA
    if filtro_competicion_eq == "Copa":
        copa_comp_id = st.session_state.get("lapreferente_copa_id", "")
        st.markdown("---")
        st.markdown("### :material/emoji_events: Información de Copa en Vivo")
        
        if not copa_comp_id:
            st.info(":material/lightbulb: No hay configurado ningún ID de competición para la Copa. Añádelo abajo en la sección de configuración.")
        else:
            col_copa1, col_copa2 = st.columns(2)
            with col_copa1:
                st.markdown("#### :material/list_alt: Cuadro / Clasificación de Copa")
                url_copa_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
                st.components.v1.html(f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_clasif}"></iframe>', height=590, scrolling=True)
            with col_copa2:
                st.markdown("#### :material/sports_soccer: Resultados de Copa")
                url_copa_res = f"https://www.lapreferente.com/widgetResultados.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
                st.components.v1.html(f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_res}"></iframe>', height=590, scrolling=True)

    # CONFIGURACIONES DE LIGA/COPA
    if filtro_competicion_eq in ["Liga", "Copa"]:
        st.markdown("---")
        with st.expander(f":material/settings: Configurar ID de Competición para: {filtro_competicion_eq}"):
            if filtro_competicion_eq == "Liga":
                comp_id_default = st.session_state.get("lapreferente_comp_id", "26710")
                nuevo_comp_id = st.text_input("ID de Competición de Liga (LaPreferente):", value=comp_id_default)
                if nuevo_comp_id != comp_id_default:
                    st.session_state["lapreferente_comp_id"] = nuevo_comp_id
                    guardar_datos(modulo="configuracion")
                    st.success(":material/check_circle: ID de Liga actualizado correctamente.")
            elif filtro_competicion_eq == "Copa":
                copa_id_default = st.session_state.get("lapreferente_copa_id", "")
                nuevo_copa_id = st.text_input("ID de Competición de Copa (LaPreferente):", value=copa_id_default)
                if nuevo_copa_id != copa_id_default:
                    st.session_state["lapreferente_copa_id"] = nuevo_copa_id
                    guardar_datos(modulo="configuracion")
                    st.success(":material/check_circle: ID de Copa actualizado correctamente.")
# ==========================================
# 📋 PESTAÑA NUEVA: PIZARRA TÁCTICA 2D & SINERGIAS
# ==========================================
with tab_pizarra:
    st.markdown("### :material/developer_board: Pizarra Táctica Inteligente: Once Ideal de la Semana")
    st.caption("Algoritmo de recomendación semanal: cruza Readiness (35%), Estado de Carga ACWR Sweet Spot (30%) e Impacto Competitivo +/- por 90' (35%), descartando automáticamente lesionados, jugadores en RTP y sancionados.")

    c_sis1, c_sis2, c_sis3 = st.columns([1.2, 1.2, 1.6])
    sistema_elegido = c_sis1.selectbox("1. Sistema Táctico:", ["1-4-3-3", "1-4-2-3-1", "1-4-4-2", "1-3-5-2"], key="sel_sis_tactico")
    comp_pizarra = c_sis2.selectbox("2. Contexto Competitivo:", ["Liga", "Global", "Copa"], key="sel_comp_pizarra")
    prioridad_alg = c_sis3.radio("3. Enfoque del Algoritmo:", ["Equilibrado (Élite)", "Máxima Frescura Física", "Máximo Rendimiento (+/-)"], horizontal=True, key="rad_prio_piz")

    partidos_piz = filtrar_partidos(comp_pizarra)
    
    # 1. Identificar bajas médicas, readaptación y sancionados
    ses_pasadas_piz = sorted([s for s in st.session_state.sesiones if s["fecha"] <= hoy_stats_str], key=lambda x: x["fecha"])
    entrenos_piz = [s for s in ses_pasadas_piz if s.get("tipo") == "Entrenamiento"]
    disp_ult_piz = {limpiar_nombre(k): v for k, v in ses_pasadas_piz[-1].get("disponibilidad", {}).items()} if ses_pasadas_piz else {}
    disp_ent_piz = {limpiar_nombre(k): v for k, v in entrenos_piz[-1].get("disponibilidad", {}).items()} if entrenos_piz else {}
    les_act_piz = {limpiar_nombre(l["jugador"]) for l in st.session_state.get("lesiones", []) if l.get("estado") == "Activa"}

    # Sancionados en el último partido oficial
    partidos_liga_ord = sorted(filtrar_partidos("Liga"), key=lambda x: x.get("fecha", ""))
    stats_ult_liga = partidos_liga_ord[-1].get("estadisticas_partido", {}) if partidos_liga_ord else {}
    acum_ta = {}
    for p_l in partidos_liga_ord:
        for j_k, v_k in p_l.get("estadisticas_partido", {}).items():
            if isinstance(v_k, dict):
                acum_ta[limpiar_nombre(j_k)] = acum_ta.get(limpiar_nombre(j_k), 0) + int(safe_float(v_k.get("Amarillas", 0)))

    sancionados_set = set()
    for j_k, v_k in stats_ult_liga.items():
        if isinstance(v_k, dict):
            jc = limpiar_nombre(j_k)
            if int(safe_float(v_k.get("Rojas", 0))) > 0:
                sancionados_set.add(jc)
            elif int(safe_float(v_k.get("Amarillas", 0))) > 0 and acum_ta.get(jc, 0) > 0 and acum_ta.get(jc, 0) % 5 == 0:
                sancionados_set.add(jc)

    # 2. Extraer Readiness y EWMA actual
    ult_rd_map = {}
    for s_p in ses_pasadas_piz:
        if s_p.get("informe_generado") and s_p.get("datos_informe"):
            for d_p in s_p["datos_informe"]:
                t_val, w_val = safe_float(d_p.get("TQR", 0)), safe_float(d_p.get("WELLNESS", 0))
                if t_val > 0 and w_val > 0:
                    ult_rd_map[limpiar_nombre(d_p["JUGADOR"])] = ((t_val / 10.0) * 50.0) + (((35.0 - w_val) / 30.0) * 50.0)

    fecha_ewma_piz = ses_pasadas_piz[-1]["fecha"] if ses_pasadas_piz else hoy_stats_str
    ewma_piz_dict = calcular_ewma_historico(st.session_state.sesiones, fecha_ewma_piz)
    ewma_clean_map = {limpiar_nombre(k): v for k, v in ewma_piz_dict.items()}

    # 3. Impacto competitivo por jugador
    comp_map = {}
    for p_m in partidos_piz:
        st_p = p_m.get("estadisticas_partido", {})
        for j_m, v_m in st_p.items():
            if j_m == "_eventos_goles" or not isinstance(v_m, dict): continue
            jm_c = limpiar_nombre(j_m)
            if jm_c not in comp_map: comp_map[jm_c] = {"min": 0.0, "g": 0, "a": 0, "gf_c": 0, "gc_c": 0}
            comp_map[jm_c]["min"] += safe_float(v_m.get("Minutos", 0))
            comp_map[jm_c]["g"] += int(safe_float(v_m.get("Goles", 0)))
            comp_map[jm_c]["a"] += int(safe_float(v_m.get("Asistencias", 0)))
            comp_map[jm_c]["gf_c"] += int(safe_float(v_m.get("GF_Campo", 0)))
            comp_map[jm_c]["gc_c"] += int(safe_float(v_m.get("GC_Campo", 0)))

    max_min_eq = max([v["min"] for v in comp_map.values()], default=90.0)
    if max_min_eq <= 0: max_min_eq = 90.0

    # 4. Evaluar plantilla disponible
    candidatos = []
    no_aptos_info = []
    for p in st.session_state.plantilla:
        j_nom = p["JUGADOR"]
        jc = limpiar_nombre(j_nom)
        est_g = disp_ult_piz.get(jc, "Disponible")
        est_e = disp_ent_piz.get(jc, "Disponible")
        
        if jc in les_act_piz or est_g == "Lesionado" or est_e == "Lesionado":
            no_aptos_info.append(f"🔴 **{j_nom}** (Lesionado)")
            continue
        if est_e == "Readaptación":
            no_aptos_info.append(f"🟡 **{j_nom}** (En Readaptación RTP)")
            continue
        if jc in sancionados_set:
            no_aptos_info.append(f"🟥 **{j_nom}** (Sancionado)")
            continue

        rd_score = ult_rd_map.get(jc, 78.0)
        ac_ratio = ewma_clean_map.get(jc, {}).get("RATIO A/C", 1.0)
        if 0.80 <= ac_ratio <= 1.30: ac_score = 100.0
        elif 1.30 < ac_ratio <= 1.50 or 0.65 <= ac_ratio < 0.80: ac_score = 68.0
        else: ac_score = 35.0

        c_st = comp_map.get(jc, {"min": 0.0, "g": 0, "a": 0, "gf_c": 0, "gc_c": 0})
        mins_j = c_st["min"]
        bal_90 = ((c_st["gf_c"] - c_st["gc_c"]) / mins_j * 90.0) if mins_j > 0 else 0.0
        ga_90 = ((c_st["g"] + c_st["a"]) / mins_j * 90.0) if mins_j > 0 else 0.0
        part_pct = min((mins_j / max_min_eq) * 100.0, 100.0)
        imp_score = min(max(50.0 + (bal_90 * 12.0) + (ga_90 * 18.0) + (part_pct * 0.25), 20.0), 100.0)

        if prioridad_alg == "Máxima Frescura Física":
            score_total = (rd_score * 0.50) + (ac_score * 0.35) + (imp_score * 0.15)
        elif prioridad_alg == "Máximo Rendimiento (+/-)":
            score_total = (rd_score * 0.20) + (ac_score * 0.20) + (imp_score * 0.60)
        else:
            score_total = (rd_score * 0.35) + (ac_score * 0.30) + (imp_score * 0.35)

        candidatos.append({
            "JUGADOR": j_nom, "dorsal": p.get("dorsal", 99), "POS": p.get("POS", "DEF"),
            "pos_1": p.get("pos_1", p.get("POS", "Central")), "pos_2": p.get("pos_2", "Ninguna"),
            "lat": p.get("lateralidad", "Diestro"), "Score": round(score_total, 1),
            "Readiness": round(rd_score, 0), "ACWR": round(ac_ratio, 2), "Impacto": round(imp_score, 0),
            "Minutos": int(mins_j), "Bal_90": round(bal_90, 2)
        })

    # 5. Plantillas de coordenadas (X: 0-100 ancho, Y: 0-100 largo de portería propia a rival)
    sistemas_coords = {
        "1-4-3-3": [
            ("POR", "Portero", "C", 50, 8),
            ("LD", "Lateral", "D", 84, 26), ("DFC_D", "Central", "D", 62, 22), ("DFC_I", "Central", "I", 38, 22), ("LI", "Lateral", "I", 16, 26),
            ("MCD", "Mediocentro", "C", 50, 45), ("MC_D", "Mediocentro", "D", 70, 56), ("MC_I", "Mediocentro", "I", 30, 56),
            ("ED", "Extremo", "D", 82, 78), ("DC", "Delantero", "C", 50, 84), ("EI", "Extremo", "I", 18, 78)
        ],
        "1-4-2-3-1": [
            ("POR", "Portero", "C", 50, 8),
            ("LD", "Lateral", "D", 84, 26), ("DFC_D", "Central", "D", 62, 22), ("DFC_I", "Central", "I", 38, 22), ("LI", "Lateral", "I", 16, 26),
            ("MCD_D", "Mediocentro", "D", 64, 44), ("MCD_I", "Mediocentro", "I", 36, 44),
            ("ED", "Extremo", "D", 82, 68), ("MCO", "Mediapunta", "C", 50, 66), ("EI", "Extremo", "I", 18, 68),
            ("DC", "Delantero", "C", 50, 85)
        ],
        "1-4-4-2": [
            ("POR", "Portero", "C", 50, 8),
            ("LD", "Lateral", "D", 84, 26), ("DFC_D", "Central", "D", 62, 22), ("DFC_I", "Central", "I", 38, 22), ("LI", "Lateral", "I", 16, 26),
            ("MD", "Extremo", "D", 82, 54), ("MC_D", "Mediocentro", "D", 62, 50), ("MC_I", "Mediocentro", "I", 38, 50), ("MI", "Extremo", "I", 18, 54),
            ("DC_D", "Delantero", "D", 62, 82), ("DC_I", "Delantero", "I", 38, 82)
        ],
        "1-3-5-2": [
            ("POR", "Portero", "C", 50, 8),
            ("DFC_D", "Central", "D", 74, 23), ("DFC_C", "Central", "C", 50, 20), ("DFC_I", "Central", "I", 26, 23),
            ("CAD_D", "Lateral", "D", 86, 52), ("MC_D", "Mediocentro", "D", 66, 50), ("MCD", "Mediocentro", "C", 50, 42), ("MC_I", "Mediocentro", "I", 34, 50), ("CAD_I", "Lateral", "I", 14, 52),
            ("DC_D", "Delantero", "D", 62, 82), ("DC_I", "Delantero", "I", 38, 82)
        ]
    }

    mapa_gen = {"Portero": "POR", "Central": "DEF", "Lateral": "DEF", "Mediocentro": "MED", "Mediapunta": "MED", "Extremo": "ATA", "Delantero": "ATA"}
    usados = set()
    once_titular = []

    for rol_cod, pos_req, lado_req, x_pos, y_pos in sistemas_coords[sistema_elegido]:
        mejor_cand = None
        mejor_val = -999.0
        for c in candidatos:
            if c["JUGADOR"] in usados: continue
            if pos_req == "Portero" and c["POS"] != "POR": continue
            if pos_req != "Portero" and c["POS"] == "POR": continue
            
            if c["pos_1"] == pos_req: bonus_pos = 25.0
            elif c["pos_2"] == pos_req: bonus_pos = 14.0
            elif c["POS"] == mapa_gen.get(pos_req, ""): bonus_pos = 4.0
            else: bonus_pos = -25.0

            bonus_lat = 0.0
            if lado_req == "I" and c["lat"] in ["Zurdo", "Ambidiestro"]: bonus_lat = 6.0
            elif lado_req == "D" and c["lat"] in ["Diestro", "Ambidiestro"]: bonus_lat = 4.0

            val_final = c["Score"] + bonus_pos + bonus_lat
            if val_final > mejor_val:
                mejor_val = val_final
                mejor_cand = c

        if mejor_cand:
            usados.add(mejor_cand["JUGADOR"])
            once_titular.append({"Rol_Pizarra": rol_cod, "X": x_pos, "Y": y_pos, **mejor_cand})

    suplentes_rec = sorted([c for c in candidatos if c["JUGADOR"] not in usados], key=lambda x: x["Score"], reverse=True)[:5]

    col_campo, col_banq = st.columns([1.55, 1], gap="large")
    with col_campo:
        fig_pitch = go.Figure()
        # Césped y líneas reglamentarias
        fig_pitch.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, fillcolor="#0d2818", line=dict(color="#C5A059", width=2), layer="below")
        fig_pitch.add_shape(type="line", x0=0, y0=50, x1=100, y1=50, line=dict(color="rgba(255,255,255,0.35)", width=1.5), layer="below")
        fig_pitch.add_shape(type="circle", x0=36, y0=40, x1=64, y1=60, line=dict(color="rgba(255,255,255,0.35)", width=1.5), layer="below")
        fig_pitch.add_shape(type="rect", x0=22, y0=0, x1=78, y1=16, line=dict(color="rgba(255,255,255,0.35)", width=1.5), layer="below")
        fig_pitch.add_shape(type="rect", x0=22, y0=84, x1=78, y1=100, line=dict(color="rgba(255,255,255,0.35)", width=1.5), layer="below")

        if once_titular:
            df_once = pd.DataFrame(once_titular)
            colores_nodo = ["#10b981" if r >= 78 else ("#C5A059" if r >= 65 else "#f59e0b") for r in df_once["Score"]]
            textos_nodo = [f"<b>#{r['dorsal']} {r['JUGADOR'].split()[0]}</b><br><span style='font-size:10px;'>{r['Rol_Pizarra']} | {r['Score']:.0f} pts</span>" for _, r in df_once.iterrows()]
            
            fig_pitch.add_trace(go.Scatter(
                x=df_once["X"], y=df_once["Y"], mode="markers+text",
                marker=dict(size=28, color=colores_nodo, line=dict(width=2.5, color="#0b0e14")),
                text=textos_nodo, textposition="bottom center",
                textfont=dict(color="#f8fafc", size=11, family="Plus Jakarta Sans"),
                hovertemplate="<b>%{customdata[0]}</b> (#%{customdata[1]})<br>Demarcación: %{customdata[2]}<br>Score Total: %{customdata[3]} pts<br>Readiness: %{customdata[4]}% | ACWR: %{customdata[5]}<extra></extra>",
                customdata=df_once[["JUGADOR", "dorsal", "pos_1", "Score", "Readiness", "ACWR"]].values
            ))

        fig_pitch.update_layout(
            height=580, margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(range=[-4, 104], visible=False, fixedrange=True),
            yaxis=dict(range=[-6, 104], visible=False, fixedrange=True),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            title=dict(text=f"<b>ONCE RECOMENDADO ({sistema_elegido})</b>", x=0.5, font=dict(color="#C5A059", size=14))
        )
        st.plotly_chart(fig_pitch, use_container_width=True)

    with col_banq:
        st.markdown("#### :material/bolt: Banquillo de Impacto (Top 5)")
        for s_j in suplentes_rec:
            st.markdown(f"""
            <div style="background: #111318; border: 1px solid rgba(255,255,255,0.06); border-left: 4px solid #C5A059; padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #f8fafc; font-size: 0.92rem;">#{s_j['dorsal']} {s_j['JUGADOR']}</strong>
                    <span style="color: #94a3b8; font-size: 0.75rem; display: block;">{s_j['pos_1']} ({s_j['lat']}) | ACWR: {s_j['ACWR']} | RD: {s_j['Readiness']:.0f}%</span>
                </div>
                <span class="font-mono-hud" style="background: rgba(197,160,89,0.15); color: #C5A059; font-weight: 800; padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;">{s_j['Score']:.1f} pts</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### :material/block: Descartados para la Convocatoria")
        if no_aptos_info:
            for na in no_aptos_info:
                st.markdown(f"<div style='font-size: 0.82rem; color: #cbd5e1; margin-bottom: 4px;'>{na}</div>", unsafe_allow_html=True)
        else:
            st.success(":material/check_circle: Toda la plantilla está disponible y sin sanciones.")

    st.markdown("---")
    # =========================================================================
    # 🤝 B5. SINERGIAS Y "SOCIEDADES DE ORO" (PAREJAS EN EL CÉSPED)
    # =========================================================================
    st.markdown("#### :material/handshake: Sinergias y 'Sociedades de Oro' (Parejas Titulares)")
    st.caption("Identifica qué parejas de futbolistas logran mayor promedio de puntos (Pts/P) y menor tasa de goles encajados (GC/P) cuando salen juntos de inicio.")
    
    linea_sin = st.radio("Filtrar sinergia por línea:", ["Parejas Defensivas (DEF)", "Sociedades en Mediocampo (MED)", "Sociedades Ofensivas (ATA/MED)", "Cualquier Pareja de Campo"], horizontal=True, key="rad_sinergia")
    pos_map_sin = {p["JUGADOR"]: p.get("POS", "DEF") for p in st.session_state.plantilla}

    from itertools import combinations
    parejas_stats = {}
    for p_s in partidos_piz:
        disp_p = {limpiar_nombre(k): v for k, v in p_s.get("disponibilidad", {}).items()}
        gf_s = int(safe_float(p_s.get("goles_favor", 0)))
        gc_s = int(safe_float(p_s.get("goles_contra", 0)))
        pts_s = 3 if gf_s > gc_s else (1 if gf_s == gc_s else 0)

        titulares_p = []
        for pl in st.session_state.plantilla:
            jn = pl["JUGADOR"]
            pos_j = pl.get("POS", "DEF")
            if pos_j == "POR": continue
            if disp_p.get(limpiar_nombre(jn)) == "Titular":
                if linea_sin == "Parejas Defensivas (DEF)" and pos_j != "DEF": continue
                if linea_sin == "Sociedades en Mediocampo (MED)" and pos_j != "MED": continue
                if linea_sin == "Sociedades Ofensivas (ATA/MED)" and pos_j not in ["ATA", "MED"]: continue
                titulares_p.append(jn)

        for j1, j2 in combinations(sorted(titulares_p), 2):
            par_key = f"{j1} + {j2}"
            if par_key not in parejas_stats:
                parejas_stats[par_key] = {"Pareja": par_key, "PJ Juntos": 0, "V": 0, "GF": 0, "GC": 0, "Pts": 0}
            parejas_stats[par_key]["PJ Juntos"] += 1
            parejas_stats[par_key]["GF"] += gf_s
            parejas_stats[par_key]["GC"] += gc_s
            parejas_stats[par_key]["Pts"] += pts_s
            if pts_s == 3: parejas_stats[par_key]["V"] += 1

    if parejas_stats:
        df_par = pd.DataFrame(list(parejas_stats.values()))
        min_pj_par = 2 if df_par["PJ Juntos"].max() >= 2 else 1
        df_par = df_par[df_par["PJ Juntos"] >= min_pj_par].copy()
        df_par["Pts/P"] = df_par["Pts"] / df_par["PJ Juntos"]
        df_par["GF/P"] = df_par["GF"] / df_par["PJ Juntos"]
        df_par["GC/P"] = df_par["GC"] / df_par["PJ Juntos"]
        df_par["% Vict."] = (df_par["V"] / df_par["PJ Juntos"]) * 100.0
        df_par = df_par.sort_values(by=["Pts/P", "PJ Juntos", "GC/P"], ascending=[False, False, True]).head(10)
        mostrar_tabla_moderna(df_par[["Pareja", "PJ Juntos", "% Vict.", "Pts/P", "GF/P", "GC/P"]].style.hide(axis="index").format({"% Vict.": "{:.0f}%", "Pts/P": "{:.2f}", "GF/P": "{:.2f}", "GC/P": "{:.2f}"}).background_gradient(subset=["Pts/P"], cmap="Greens").background_gradient(subset=["GC/P"], cmap="Reds"))
    else:
        st.info("No hay suficientes partidos con titulares registrados para calcular sinergias.")


# ==========================================
# 👤 PESTAÑA 2: ESTADÍSTICAS DE JUGADORES
# ==========================================
with tab_jugadores:
    col_comp1_jug, col_comp2_jug = st.columns([1, 3])
    filtro_competicion_jug = col_comp1_jug.selectbox(
        "▪️ Filtro de Competición:", 
        ["Liga", "Copa", "Amistosos", "Global"],
        key="filtro_comp_jug"
    )
    partidos_jug = filtrar_partidos(filtro_competicion_jug)

    st.markdown(f"### :material/list_alt: Rendimiento Individual | {filtro_competicion_jug}")
    
    fotos_plantilla = {}
    for p in st.session_state.plantilla:
        fotos_plantilla[p["JUGADOR"].strip().lower()] = p.get("FOTO", p.get("foto", ""))

    datos_jugadores = {}
    for p in st.session_state.plantilla:
        datos_jugadores[p["JUGADOR"]] = {
            "POS": p["POS"], "Convocatorias": 0, "Partidos Jugados": 0,
            "Minutos": 0.0, "Goles": 0, "Asistencias": 0, 
            "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0,
            "GF_Campo": 0, "GC_Campo": 0
        }
    
    for p in partidos_jug:
        stats = p.get("estadisticas_partido", {})
        disp = p.get("disponibilidad", {})
        invitados = p.get("estadisticas_invitados", [])
        eventos_g = stats.get("_eventos_goles", {})
        lista_gf_p = eventos_g.get("gf", [])
        lista_gc_p = eventos_g.get("gc", [])
        
        disp_clean = {k.strip().lower(): v for k, v in disp.items()}
        for jug in datos_jugadores.keys():
            jug_clean = jug.strip().lower()
            if disp_clean.get(jug_clean) in ["Titular", "Suplente"]:
                datos_jugadores[jug]["Convocatorias"] += 1
                
        for jug, vals in stats.items():
            if jug == "_eventos_goles" or not isinstance(vals, dict):
                continue
            if jug in datos_jugadores:
                mins = safe_float(vals.get("Minutos", 0))
                rol_j = disp_clean.get(jug.strip().lower(), "Titular" if mins >= 45 else "Suplente")
                datos_jugadores[jug]["Minutos"] += mins
                datos_jugadores[jug]["Goles"] += int(safe_float(vals.get("Goles", 0)))
                datos_jugadores[jug]["Goles Encajados"] += int(safe_float(vals.get("Goles Encajados", 0)))
                datos_jugadores[jug]["Asistencias"] += int(safe_float(vals.get("Asistencias", 0)))
                datos_jugadores[jug]["Amarillas"] += int(safe_float(vals.get("Amarillas", 0)))
                datos_jugadores[jug]["Rojas"] += int(safe_float(vals.get("Rojas", 0)))
                
                if "GF_Campo" in vals or "GC_Campo" in vals:
                    gf_c = int(safe_float(vals.get("GF_Campo", 0)))
                    gc_c = int(safe_float(vals.get("GC_Campo", 0)))
                elif lista_gf_p or lista_gc_p:
                    gf_c = sum(1 for mg in lista_gf_p if mins > 0 and (mg <= mins if rol_j == "Titular" else mg > (90 - mins)))
                    gc_c = sum(1 for mg in lista_gc_p if mins > 0 and (mg <= mins if rol_j == "Titular" else mg > (90 - mins)))
                else:
                    gf_c, gc_c = 0, 0
                    
                datos_jugadores[jug]["GF_Campo"] += gf_c
                datos_jugadores[jug]["GC_Campo"] += gc_c
                if mins > 0: datos_jugadores[jug]["Partidos Jugados"] += 1
                    
        for inv in invitados:
            n_inv = inv["JUGADOR"]
            if n_inv not in datos_jugadores:
                datos_jugadores[n_inv] = {
                    "POS": inv.get("POS", "CANTERA"), "Convocatorias": 1, "Partidos Jugados": 0,
                    "Minutos": 0.0, "Goles": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0,
                    "GF_Campo": 0, "GC_Campo": 0
                }
            else:
                datos_jugadores[n_inv]["Convocatorias"] += 1
                
            mins = safe_float(inv.get("Minutos", 0))
            datos_jugadores[n_inv]["Minutos"] += mins
            datos_jugadores[n_inv]["Goles"] += int(safe_float(inv.get("Goles", 0)))
            datos_jugadores[n_inv]["Goles Encajados"] += int(safe_float(inv.get("Goles Encajados", 0)))
            datos_jugadores[n_inv]["Asistencias"] += int(safe_float(inv.get("Asistencias", 0)))
            datos_jugadores[n_inv]["Amarillas"] += int(safe_float(inv.get("Amarillas", 0)))
            datos_jugadores[n_inv]["Rojas"] += int(safe_float(inv.get("Rojas", 0)))
            datos_jugadores[n_inv]["GF_Campo"] += int(safe_float(inv.get("GF_Campo", 0)))
            datos_jugadores[n_inv]["GC_Campo"] += int(safe_float(inv.get("GC_Campo", 0)))
            if mins > 0: datos_jugadores[n_inv]["Partidos Jugados"] += 1

    if filtro_competicion_jug in ["Liga", "Global"]:
        apercibidos = []
        sancionados = []
        
        partidos_jug_ord = sorted(partidos_jug, key=lambda x: x.get("fecha", ""))
        stats_ult_partido = partidos_jug_ord[-1].get("estadisticas_partido", {}) if partidos_jug_ord else {}
        
        for jug, d in datos_jugadores.items():
            tarjetas = d["Amarillas"]
            st_ult_j = stats_ult_partido.get(jug, {}) if isinstance(stats_ult_partido.get(jug), dict) else {}
            vio_amarilla_ult = int(safe_float(st_ult_j.get("Amarillas", 0))) > 0
            vio_roja_ult = int(safe_float(st_ult_j.get("Rojas", 0))) > 0
            
            if vio_roja_ult:
                sancionados.append(f"{jug} (Tarjeta Roja)")
            elif tarjetas > 0 and tarjetas % 5 == 0 and vio_amarilla_ult:
                sancionados.append(f"{jug} ({tarjetas} TA - Cumple ciclo)")
            elif tarjetas > 0 and tarjetas % 5 == 4:
                apercibidos.append(f"{jug} ({tarjetas} TA)")
                    
        if apercibidos or sancionados:
            st.markdown("#### :material/balance: Alertas Disciplinarias (Ciclos de 5 Amarillas)")
            c_al1, c_al2 = st.columns(2)
            with c_al1:
                if sancionados:
                    for s in sancionados: st.error(f":material/block: **SANCIONADO:** {s}")
                else:
                    st.success(":material/check_circle: Ningún jugador cumple ciclo.")
            with c_al2:
                if apercibidos:
                    for a in apercibidos: st.warning(f":material/warning: **APERCIBIDO:** {a}")
                else:
                    st.info(":material/check_circle: Ningún jugador apercibido.")
            st.markdown("---")

    lista_stats = []
    pj_jug = len(partidos_jug)
    minutos_posibles = pj_jug * 90 if pj_jug > 0 else 0
    
    for jug, d in datos_jugadores.items():
        mins = d["Minutos"]
        goles = d["Goles"]
        asistencias = d["Asistencias"]
        gf_c = d["GF_Campo"]
        gc_c = d["GC_Campo"]
        bal_c = gf_c - gc_c
        
        min_por_gol = (mins / goles) if goles > 0 else 0
        min_por_asist = (mins / asistencias) if asistencias > 0 else 0
        porc_mins = (mins / minutos_posibles * 100) if minutos_posibles > 0 else 0
        
        gf_90 = (gf_c / mins * 90.0) if mins > 0 else 0.0
        gc_90 = (gc_c / mins * 90.0) if mins > 0 else 0.0
        bal_90 = (bal_c / mins * 90.0) if mins > 0 else 0.0
        
        lista_stats.append({
            "JUGADOR": jug, "POS": d["POS"], "Conv.": d["Convocatorias"], "PJ": d["Partidos Jugados"],
            "MIN": int(mins), "% MIN": porc_mins, "G": goles, "A": asistencias,
            "Min/Gol": min_por_gol, "Min/Asist": min_por_asist, "GE": d["Goles Encajados"],
            "GF Campo": gf_c, "GC Campo": gc_c, "+/- Campo": bal_c,
            "GF/90'": gf_90, "GC/90'": gc_90, "+/- 90'": bal_90,
            "TA": d["Amarillas"], "TR": d["Rojas"]
        })
        
    df_jugadores = pd.DataFrame(lista_stats)
    
    if not df_jugadores.empty:
        df_jugadores = df_jugadores.sort_values(by="MIN", ascending=False)
        
        st.markdown("#### :material/workspace_premium: Destacados")
        
        def render_tarjeta_top3(titulo_categoria, df_sub, columna_valor, sufijo=""):
            st.markdown(f"<strong style='color:#f8fafc;'>{titulo_categoria}</strong>", unsafe_allow_html=True)
            if not df_sub.empty:
                for idx, row in df_sub.reset_index(drop=True).iterrows():
                    val = row[columna_valor]
                    val_str = f"{val:.1f}{sufijo}" if isinstance(val, float) else f"{val}{sufijo}"
                    nombre_jugador = row['JUGADOR']
                    
                    foto_b64 = fotos_plantilla.get(nombre_jugador.strip().lower(), "")
                    if foto_b64:
                        img_src = foto_b64 if str(foto_b64).startswith("http") else f"data:image/jpeg;base64,{foto_b64}"
                        avatar_html = f'<img src="{img_src}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 10px; border: 1px solid #1c1f26;">'
                    else:
                        avatar_html = '<span class="material-symbols-rounded" style="font-size: 20px; color: #64748b; margin-right: 10px; vertical-align: middle;">person</span>'

                    st.markdown(
                        f"""
                        <div style="background-color: #111318; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border: 1px solid #1c1f26; border-left: 4px solid #C5A059; display: flex; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                            {avatar_html}
                            <div style="overflow: hidden; width: 100%;">
                                <strong style="font-size: 0.85em; color: #94a3b8; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-transform: uppercase;">{nombre_jugador}</strong>
                                <span style="color: #f8fafc; font-weight: 800; font-size: 1.1em;">{val_str}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("Sin datos.")

        col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
        
        with col_d1:
            df_g = df_jugadores[df_jugadores["G"] > 0].sort_values(by="G", ascending=False).head(3)
            render_tarjeta_top3(":material/sports_soccer: Goles", df_g, "G")
    
        with col_d2:
            df_a = df_jugadores[df_jugadores["A"] > 0].sort_values(by="A", ascending=False).head(3)
            render_tarjeta_top3(":material/my_location: Asistencias", df_a, "A")
            
        with col_d3:
            df_m = df_jugadores.sort_values(by="MIN", ascending=False).head(3)
            render_tarjeta_top3(":material/timer: Minutos", df_m, "MIN", " min")
            
        with col_d4:
            df_mg = df_jugadores[df_jugadores["Min/Gol"] > 0].sort_values(by="Min/Gol", ascending=True).head(3)
            render_tarjeta_top3(":material/bolt: Min / Gol", df_mg, "Min/Gol", "'")
            
        with col_d5:
            df_ma = df_jugadores[df_jugadores["Min/Asist"] > 0].sort_values(by="Min/Asist", ascending=True).head(3)
            render_tarjeta_top3(":material/my_location: Min / Asist", df_ma, "Min/Asist", "'")

        st.markdown("---")

        # ==========================================
        # 📊 GRÁFICO: MINUTOS ACUMULADOS (Vertical ordenado por POR, DEF, MED, ATA)
        # ==========================================
        st.markdown("#### :material/bar_chart: Gráfico de Minutos Acumulados por Jugador")
        
        # Definir el orden jerárquico de las posiciones
        orden_posiciones = ["POR", "DEF", "MED", "ATA", "CANTERA"]
        df_jugadores["POS"] = pd.Categorical(df_jugadores["POS"], categories=orden_posiciones, ordered=True)
        
        # Ordenar primero por posición y luego por minutos de mayor a menor dentro de cada posición
        df_jugadores_sorted = df_jugadores.sort_values(by=["POS", "MIN"], ascending=[True, False])

        fig_mins = px.bar(
            df_jugadores_sorted,
            x="JUGADOR",
            y="MIN",
            color="POS",
            orientation="v",
            labels={"MIN": "Minutos Jugados", "JUGADOR": "Jugador", "POS": "Posición"},
            title="Participación de la Plantilla (Minutos totales)"
        )
        fig_mins.update_layout(
            height=450, 
            xaxis={'tickangle': -45, 'categoryorder': 'array', 'categoryarray': df_jugadores_sorted["JUGADOR"].tolist()}, 
            margin=dict(l=20, r=20, t=40, b=80)
        )
        st.plotly_chart(fig_mins, use_container_width=True)

        st.markdown("---")
        c_f1, c_f2 = st.columns(2)
        filtro_pos = c_f1.selectbox("Filtro Rápido (Posición):", ["TODOS", "POR", "DEF", "MED", "ATA", "CANTERA"])
        
        if filtro_pos != "TODOS":
            df_mostrar = df_jugadores[df_jugadores["POS"] == filtro_pos]
        else:
            df_mostrar = df_jugadores
            
        st.markdown("##### :material/shield_with_heart: Impacto Colectivo con el Jugador en el Campo (Goles Anotados vs Encajados)")
        st.caption("Analiza con qué futbolistas en el césped el equipo anota más y encaja menos, tanto en volumen total como ponderado por cada 90 minutos jugados.")
        
        c_imp_f1, c_imp_f2 = st.columns([1, 2])
        min_umbral_imp = c_imp_f1.slider("Mínimo de minutos jugados para el ranking /90':", min_value=0, max_value=max(int(df_jugadores["MIN"].max()), 90), value=min(90, int(df_jugadores["MIN"].max())), step=15, key="sl_min_imp")
        
        df_imp_valid = df_mostrar[df_mostrar["MIN"] >= max(min_umbral_imp, 1)].copy()
        if not df_imp_valid.empty:
            ci_1, ci_2, ci_3, ci_4 = st.columns(4)
            with ci_1:
                df_top_gf90 = df_imp_valid.sort_values(by=["GF/90'", "GF Campo"], ascending=[False, False]).head(3)
                render_tarjeta_top3(":material/trending_up: Más Anotan / 90'", df_top_gf90, "GF/90'", " GF/90'")
            with ci_2:
                df_top_gc90 = df_imp_valid.sort_values(by=["GC/90'", "MIN"], ascending=[True, False]).head(3)
                render_tarjeta_top3(":material/security: Menos Encajan / 90'", df_top_gc90, "GC/90'", " GC/90'")
            with ci_3:
                df_top_bal90 = df_imp_valid.sort_values(by=["+/- 90'", "+/- Campo"], ascending=[False, False]).head(3)
                render_tarjeta_top3(":material/balance: Mejor Balance / 90'", df_top_bal90, "+/- 90'", " /90'")
            with ci_4:
                df_top_bal_tot = df_imp_valid.sort_values(by=["+/- Campo", "GF Campo"], ascending=[False, False]).head(3)
                render_tarjeta_top3(":material/emoji_events: Mejor Balance Global", df_top_bal_tot, "+/- Campo", " goles")

        st.markdown("---")
        st.markdown("##### Tabla Detallada de Rendimiento e Impacto en Campo (+/-)")
        estilo_jugadores = (df_mostrar.style
                            .hide(axis="index")
                            .format({
                                "% MIN": "{:.1f}%", 
                                "Min/Gol": lambda x: f"{x:.1f}'" if x > 0 else "-", 
                                "Min/Asist": lambda x: f"{x:.1f}'" if x > 0 else "-",
                                "+/- Campo": lambda x: f"+{int(x)}" if x > 0 else str(int(x)),
                                "GF/90'": "{:.2f}",
                                "GC/90'": "{:.2f}",
                                "+/- 90'": lambda x: f"+{x:.2f}" if x > 0 else f"{x:.2f}"
                            })
                            .background_gradient(subset=["MIN"], cmap="Blues")
                            .background_gradient(subset=["G", "GF/90'"], cmap="Greens")
                            .background_gradient(subset=["GC/90'"], cmap="Reds")
                            .background_gradient(subset=["TA"], cmap="YlOrBr")
                           )
                           
        mostrar_tabla_moderna(estilo_jugadores)
        st.caption("Acrónimos: Conv. (Convocatorias) | PJ (Partidos Jugados) | MIN (Minutos) | G (Goles) | A (Asistencias) | GE (Goles Encajados POR) | GF/GC Campo (Goles del equipo con el jugador en el césped) | GF/90' y GC/90' (Goles a favor y en contra por cada 90 min en el campo).")

        st.markdown("---")
        # =========================================================================
        # ⚡ B4 & B6. FACTOR REVULSIVO Y RANKING JUGADOR TALISMÁN (Δ PUNTOS)
        # =========================================================================
        col_rev, col_tal = st.columns(2)

        with col_rev:
            st.markdown("#### :material/bolt: Impacto desde el Banquillo ('Factor Revulsivo')")
            st.caption("Rendimiento exclusivo actuando como Suplente (Goles, Asistencias y +/- en campo saliendo desde el banquillo).")
            datos_rev = []
            for p_j in st.session_state.plantilla:
                jn = p_j["JUGADOR"]
                jc = limpiar_nombre(jn)
                pj_sup, min_sup, g_sup, a_sup, gf_sup, gc_sup = 0, 0.0, 0, 0, 0, 0
                for part in partidos_jug:
                    disp_map = {limpiar_nombre(k): v for k, v in part.get("disponibilidad", {}).items()}
                    st_map = {limpiar_nombre(k): v for k, v in part.get("estadisticas_partido", {}).items() if isinstance(v, dict)}
                    if disp_map.get(jc) == "Suplente" and jc in st_map:
                        m_s = safe_float(st_map[jc].get("Minutos", 0))
                        if m_s > 0:
                            pj_sup += 1
                            min_sup += m_s
                            g_sup += int(safe_float(st_map[jc].get("Goles", 0)))
                            a_sup += int(safe_float(st_map[jc].get("Asistencias", 0)))
                            gf_sup += int(safe_float(st_map[jc].get("GF_Campo", 0)))
                            gc_sup += int(safe_float(st_map[jc].get("GC_Campo", 0)))
                if pj_sup > 0:
                    ga_90_sup = ((g_sup + a_sup) / min_sup * 90.0) if min_sup > 0 else 0.0
                    datos_rev.append({
                        "JUGADOR": jn, "PJ Sup.": pj_sup, "MIN Sup.": int(min_sup),
                        "G+A Sup.": g_sup + a_sup, "G+A / 90'": ga_90_sup, "+/- Sup.": gf_sup - gc_sup
                    })
            if datos_rev:
                df_rev = pd.DataFrame(datos_rev).sort_values(by=["G+A Sup.", "+/- Sup.", "MIN Sup."], ascending=[False, False, False]).head(8)
                mostrar_tabla_moderna(df_rev.style.hide(axis="index").format({"G+A / 90'": "{:.2f}", "+/- Sup.": lambda x: f"+{int(x)}" if x > 0 else str(int(x))}).background_gradient(subset=["G+A Sup.", "+/- Sup."], cmap="Greens"))
            else:
                st.info("Aún no hay participaciones registradas saliendo desde el banquillo.")

        with col_tal:
            st.markdown("#### :material/workspace_premium: Jugador Talismán (Diferencial de Puntos Con vs. Sin él)")
            st.caption("Compara los Puntos por Partido (Pts/P) que logra el equipo cuando el jugador disputa ≥45' frente a cuando no juega.")
            datos_tal = []
            for p_j in st.session_state.plantilla:
                jn = p_j["JUGADOR"]
                jc = limpiar_nombre(jn)
                pts_con, pj_con, pts_sin, pj_sin = 0, 0, 0, 0
                for part in partidos_jug:
                    gf_t = int(safe_float(part.get("goles_favor", 0)))
                    gc_t = int(safe_float(part.get("goles_contra", 0)))
                    pts_t = 3 if gf_t > gc_t else (1 if gf_t == gc_t else 0)
                    st_map = {limpiar_nombre(k): v for k, v in part.get("estadisticas_partido", {}).items() if isinstance(v, dict)}
                    m_jug = safe_float(st_map.get(jc, {}).get("Minutos", 0))
                    if m_jug >= 45.0:
                        pj_con += 1; pts_con += pts_t
                    else:
                        pj_sin += 1; pts_sin += pts_t
                if pj_con >= 1 and pj_sin >= 1:
                    ppg_con = pts_con / pj_con
                    ppg_sin = pts_sin / pj_sin
                    datos_tal.append({
                        "JUGADOR": jn, "PJ (≥45')": pj_con, "Pts/P CON él": ppg_con,
                        "Pts/P SIN él": ppg_sin, "Δ Impacto Pts": ppg_con - ppg_sin
                    })
            if datos_tal:
                df_tal = pd.DataFrame(datos_tal).sort_values(by=["Δ Impacto Pts", "Pts/P CON él"], ascending=[False, False]).head(8)
                mostrar_tabla_moderna(df_tal.style.hide(axis="index").format({"Pts/P CON él": "{:.2f}", "Pts/P SIN él": "{:.2f}", "Δ Impacto Pts": "{:+.2f}"}).background_gradient(subset=["Δ Impacto Pts"], cmap="RdYlGn"))
            else:
                st.info("Se necesitan más jornadas disputadas para contrastar el diferencial de puntos con/sin cada jugador.")
                
# ==========================================
# 🆚 PESTAÑA 3: ESTADÍSTICAS DE RIVAL
# ==========================================
with tab_rivales:
    st.markdown("### :material/sports_score: Análisis de Equipos Rival (LaPreferente)")
    st.caption("Consulta la plantilla y las estadísticas de tus rivales en la liga. El sistema detectará automáticamente tu próximo enfrentamiento.")

    if "rivales_guardados" not in st.session_state:
        st.session_state["rivales_guardados"] = {}

    rivales_disponibles = list(st.session_state["rivales_guardados"].keys())

    # ==========================================
    # SECCIÓN 1: CONSULTA DEL RIVAL Y AUTO-SELECTOR
    # ==========================================
    from datetime import date
    hoy_str = str(date.today())
    rival_proximo = None
    
    # Buscar el próximo partido en el calendario
    sesiones_futuras = sorted([s for s in st.session_state.sesiones if s["fecha"] >= hoy_str and "Partido" in s["tipo"]], key=lambda x: x["fecha"])
    if sesiones_futuras:
        rival_proximo = sesiones_futuras[0].get("rival", "")

    # Determinar el índice por defecto para el selectbox
    idx_default = 0
    if rival_proximo and rival_proximo in rivales_disponibles:
        idx_default = rivales_disponibles.index(rival_proximo) + 1

    if not rivales_disponibles:
        st.info(":material/lightbulb: Aún no hay ningún equipo rival registrado. Despliega el menú inferior para añadir el primero.")
    else:
        col_sel1, col_sel2 = st.columns([2, 2])
        with col_sel1:
            rival_elegido = st.selectbox("Selecciona un rival guardado:", ["Selecciona un equipo..."] + rivales_disponibles, index=idx_default)
            
        if rival_elegido != "Selecciona un equipo...":
            datos_rival = st.session_state["rivales_guardados"][rival_elegido]
            
            if isinstance(datos_rival, dict):
                id_equipo_final = datos_rival.get("id", "")
            else:
                id_equipo_final = datos_rival
                
            comp_id_actual = st.session_state.get("lapreferente_comp_id", "26710")
            
            st.markdown(f"#### :material/list_alt: Plantilla y Estadísticas de: **{rival_elegido}**")
            
            url_widget_rival = f"https://www.lapreferente.com/widgetEquipo.php?tipo=plantilla&comp={comp_id_actual}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=11&favorito=&IDequipo={id_equipo_final}"
            
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="850" src="{url_widget_rival}" scrolling="yes"></iframe>', 
                height=870,
                scrolling=True
            )
            
            if st.button(f":material/delete: Eliminar a {rival_elegido} de la lista"):
                del st.session_state["rivales_guardados"][rival_elegido]
                guardar_datos(modulo="configuracion")
                st.success(f"Equipo {rival_elegido} eliminado.")
                st.rerun()

    st.markdown("---")

    # ==========================================
    # SECCIÓN 2: AÑADIR NUEVO EQUIPO RIVAL (Movido abajo)
    # ==========================================
    with st.expander(":material/add_moderator: Añadir o Registrar un Nuevo Equipo Rival"):
        with st.form("form_nuevo_rival"):
            col_fn1, col_fn2, col_fn3, col_fn4 = st.columns([2, 1.5, 1.5, 1])
            with col_fn1:
                nombre_nuevo_rival = st.text_input("Nombre del Equipo Rival:")
            with col_fn2:
                id_nuevo_rival = st.text_input("ID LaPreferente:")
            with col_fn3:
                ciudad_rival = st.text_input("Ciudad (Para Clima):")
            with col_fn4:
                st.markdown("<br>", unsafe_allow_html=True)
                submit_rival = st.form_submit_button(":material/save: Guardar")
            
            if submit_rival:
                if nombre_nuevo_rival:
                    st.session_state["rivales_guardados"][nombre_nuevo_rival.strip()] = {
                        "id": id_nuevo_rival.strip(),
                        "ciudad": ciudad_rival.strip()
                    }
                    from database.db_manager import guardar_datos
                    guardar_datos(modulo="configuracion")
                    st.success(f":material/check_circle: ¡Rival '{nombre_nuevo_rival}' guardado correctamente!")
                    st.rerun()
                else:
                    st.warning(":material/warning: Debes rellenar tanto el nombre como el ID.")
