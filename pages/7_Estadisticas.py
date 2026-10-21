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

partidos_totales = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")]

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

tab_equipo, tab_jugadores, tab_rivales = st.tabs([
    ":material/shield: Estadísticas de Equipo", 
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
            "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0
        }
    
    for p in partidos_jug:
        stats = p.get("estadisticas_partido", {})
        disp = p.get("disponibilidad", {})
        invitados = p.get("estadisticas_invitados", [])
        
        disp_clean = {k.strip().lower(): v for k, v in disp.items()}
        for jug in datos_jugadores.keys():
            jug_clean = jug.strip().lower()
            if disp_clean.get(jug_clean) in ["Titular", "Suplente"]:
                datos_jugadores[jug]["Convocatorias"] += 1
                
        for jug, vals in stats.items():
            if jug in datos_jugadores:
                mins = vals.get("Minutos", 0)
                datos_jugadores[jug]["Minutos"] += mins
                datos_jugadores[jug]["Goles"] += vals.get("Goles", 0)
                datos_jugadores[jug]["Goles Encajados"] += vals.get("Goles Encajados", 0)
                datos_jugadores[jug]["Asistencias"] += vals.get("Asistencias", 0)
                datos_jugadores[jug]["Amarillas"] += vals.get("Amarillas", 0)
                datos_jugadores[jug]["Rojas"] += vals.get("Rojas", 0)
                if mins > 0: datos_jugadores[jug]["Partidos Jugados"] += 1
                    
        for inv in invitados:
            n_inv = inv["JUGADOR"]
            if n_inv not in datos_jugadores:
                datos_jugadores[n_inv] = {
                    "POS": inv.get("POS", "CANTERA"), "Convocatorias": 1, "Partidos Jugados": 0,
                    "Minutos": 0.0, "Goles": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0
                }
            else:
                datos_jugadores[n_inv]["Convocatorias"] += 1
                
            mins = inv.get("Minutos", 0)
            datos_jugadores[n_inv]["Minutos"] += mins
            datos_jugadores[n_inv]["Goles"] += inv.get("Goles", 0)
            datos_jugadores[n_inv]["Goles Encajados"] += inv.get("Goles Encajados", 0)
            datos_jugadores[n_inv]["Asistencias"] += inv.get("Asistencias", 0)
            datos_jugadores[n_inv]["Amarillas"] += inv.get("Amarillas", 0)
            datos_jugadores[n_inv]["Rojas"] += inv.get("Rojas", 0)
            if mins > 0: datos_jugadores[n_inv]["Partidos Jugados"] += 1

    if filtro_competicion_jug in ["Liga", "Global"]:
        apercibidos = []
        sancionados = []
        for jug, d in datos_jugadores.items():
            tarjetas = d["Amarillas"]
            if tarjetas > 0:
                if tarjetas % 5 == 4:
                    apercibidos.append(f"{jug} ({tarjetas} TA)")
                elif tarjetas % 5 == 0:
                    sancionados.append(f"{jug} ({tarjetas} TA)")
                    
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
        
        min_por_gol = (mins / goles) if goles > 0 else 0
        min_por_asist = (mins / asistencias) if asistencias > 0 else 0
        porc_mins = (mins / minutos_posibles * 100) if minutos_posibles > 0 else 0
        
        lista_stats.append({
            "JUGADOR": jug, "POS": d["POS"], "Conv.": d["Convocatorias"], "PJ": d["Partidos Jugados"],
            "MIN": int(mins), "% MIN": porc_mins, "G": goles, "A": asistencias,
            "Min/Gol": min_por_gol, "Min/Asist": min_por_asist, "GE": d["Goles Encajados"],
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

        # ==========================================
        # 🗺️ MAPA DE DISTRIBUCIÓN DE MINUTOS POR LÍNEA (Ordenado POR, DEF, MED, ATA)
        # ==========================================
        st.markdown("#### :material/pie_chart: Distribución de Minutos por Demarcación")
        
        # Filtrar las posiciones que realmente existan y ordenarlas según POR, DEF, MED, ATA...
        posiciones_existentes = [p for p in orden_posiciones if p in df_jugadores["POS"].values]
        
        if len(posiciones_existentes) > 0:
            cols_pos = st.columns(min(len(posiciones_existentes), 5))
            for i, pos_val in enumerate(posiciones_existentes):
                df_subset = df_jugadores[df_jugadores["POS"] == pos_val]
                with cols_pos[i]:
                    fig_circle = px.pie(
                        df_subset,
                        names="JUGADOR",
                        values="MIN",
                        title=f"Línea: {pos_val}",
                        hole=0.4
                    )
                    fig_circle.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
                    st.plotly_chart(fig_circle, use_container_width=True)
        else:
            st.info("Registra minutos en los partidos para ver la distribución.")

        st.markdown("---")
        c_f1, c_f2 = st.columns(2)
        filtro_pos = c_f1.selectbox("Filtro Rápido (Posición):", ["TODOS", "POR", "DEF", "MED", "ATA", "CANTERA"])
        
        if filtro_pos != "TODOS":
            df_mostrar = df_jugadores[df_jugadores["POS"] == filtro_pos]
        else:
            df_mostrar = df_jugadores
            
        st.markdown("##### Tabla Detallada de Rendimiento e Individuales")
        estilo_jugadores = (df_mostrar.style
                            .hide(axis="index")
                            .format({
                                "% MIN": "{:.1f}%", 
                                "Min/Gol": lambda x: f"{x:.1f}'" if x > 0 else "-", 
                                "Min/Asist": lambda x: f"{x:.1f}'" if x > 0 else "-"
                            })
                            .background_gradient(subset=["MIN"], cmap="Blues")
                            .background_gradient(subset=["G"], cmap="Greens")
                            .background_gradient(subset=["TA"], cmap="YlOrBr")
                           )
                           
        mostrar_tabla_moderna(estilo_jugadores)
        st.caption("Acrónimos: Conv. (Convocatorias) | PJ (Partidos Jugados) | MIN (Minutos) | G (Goles) | A (Asistencias) | Min/Gol (Minutos necesarios por gol) | GE (Goles Encajados porteros).")
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
