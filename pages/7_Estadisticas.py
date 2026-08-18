import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importar las herramientas visuales
from utils.math_helpers import *

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    st.stop()

st.title("📈 Estadísticas de Rendimiento")

partidos_totales = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")]

# ==========================================
# 1. SELECTOR DE COMPETICIÓN
# ==========================================
col_comp1, col_comp2 = st.columns([1, 3])
filtro_competicion = col_comp1.selectbox(
    "🏆 Competición:", 
    ["Liga", "Copa", "Amistosos", "Global (Todas)"]
)

# Filtrar partidos sin bloquear la pantalla si están a cero
if filtro_competicion == "Global (Todas)":
    partidos = partidos_totales
elif filtro_competicion == "Amistosos":
    partidos = [p for p in partidos_totales if p.get("tipo") == "Partido Amistoso"]
else:
    partidos = [p for p in partidos_totales if p.get("tipo") == "Partido Oficial" and p.get("competicion") == filtro_competicion]

tab_equipo, tab_jugadores = st.tabs(["🛡️ Estadísticas de Equipo", "👤 Estadísticas de Jugadores"])

# ==========================================
# 🛡️ PESTAÑA 1: ESTADÍSTICAS DE EQUIPO
# ==========================================
with tab_equipo:
    st.markdown(f"### 🏆 Balance de Resultados | {filtro_competicion}")
    
    totales = {
        "Casa": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}, 
        "Fuera": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}
    }
    
    for p in partidos:
        cond = p.get("condicion", "Casa")
        if cond not in totales: cond = "Casa"
        
        gf = p.get("goles_favor", 0)
        gc = p.get("goles_contra", 0)
        
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
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Partidos Jugados", pj)
    c2.metric("Victorias", v)
    c3.metric("Empates", e)
    c4.metric("Derrotas", d)
    c5.metric("Diferencia Goles", f"+{dif}" if dif > 0 else str(dif))
    
    st.markdown("---")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🏠 Rendimiento como Local")
        pj_casa = totales["Casa"]["P"]
        gf_pp_casa = (totales["Casa"]["GF"] / pj_casa) if pj_casa > 0 else 0
        gc_pp_casa = (totales["Casa"]["GC"] / pj_casa) if pj_casa > 0 else 0
        
        df_casa = pd.DataFrame([{
            "PJ": pj_casa, "V": totales["Casa"]["V"], "E": totales["Casa"]["E"], "D": totales["Casa"]["D"], 
            "GF": totales["Casa"]["GF"], "GC": totales["Casa"]["GC"], 
            "GF/P": gf_pp_casa, "GC/P": gc_pp_casa
        }])
        mostrar_tabla_moderna(df_casa.style.hide(axis="index").format({"GF/P": "{:.2f}", "GC/P": "{:.2f}"}))
        
    with col_t2:
        st.markdown("#### ✈️ Rendimiento como Visitante")
        pj_fuera = totales["Fuera"]["P"]
        gf_pp_fuera = (totales["Fuera"]["GF"] / pj_fuera) if pj_fuera > 0 else 0
        gc_pp_fuera = (totales["Fuera"]["GC"] / pj_fuera) if pj_fuera > 0 else 0
        
        df_fuera = pd.DataFrame([{
            "PJ": pj_fuera, "V": totales["Fuera"]["V"], "E": totales["Fuera"]["E"], "D": totales["Fuera"]["D"], 
            "GF": totales["Fuera"]["GF"], "GC": totales["Fuera"]["GC"],
            "GF/P": gf_pp_fuera, "GC/P": gc_pp_fuera
        }])
        mostrar_tabla_moderna(df_fuera.style.hide(axis="index").format({"GF/P": "{:.2f}", "GC/P": "{:.2f}"}))

    # ==========================================
    # WIDGETS DE LIGA (Clasificación + Resultados actuales y próxima jornada)
    # ==========================================
    if filtro_competicion == "Liga":
        comp_id = st.session_state.get("lapreferente_comp_id", "26710")
        st.markdown("---")
        st.markdown("### 📊 Jornada y Clasificación en Vivo (Liga)")
        
        col_widget1, col_widget2 = st.columns(2)
        
        with col_widget1:
            st.markdown("#### 📋 Clasificación")
            url_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="570" src="{url_clasif}"></iframe>', 
                height=590,
                scrolling=True
            )
            
        with col_widget2:
            st.markdown("#### ⚽ Resultados y Próxima Jornada")
            url_res_actual = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            url_res_prox = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&proximaJornada=1&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="275" src="{url_res_actual}"></iframe>', 
                height=350,
                scrolling=True
            )
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="275" src="{url_res_prox}"></iframe>', 
                height=350,
                scrolling=True
            )

    # ==========================================
    # WIDGETS DE COPA (Permite añadir otro ID diferente)
    # ==========================================
    if filtro_competicion == "Copa":
        copa_comp_id = st.session_state.get("lapreferente_copa_id", "")
        st.markdown("---")
        st.markdown("### 🏆 Información de Copa en Vivo")
        
        if not copa_comp_id:
            st.info("💡 No hay configurado ningún ID de competición para la Copa. Añádelo abajo en la sección de configuración.")
        else:
            col_copa1, col_copa2 = st.columns(2)
            with col_copa1:
                st.markdown("#### 📋 Cuadro / Clasificación de Copa")
                url_copa_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
                st.components.v1.html(
                    f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_clasif}"></iframe>', 
                    height=590,
                    scrolling=True
                )
            with col_copa2:
                st.markdown("#### ⚽ Resultados de Copa")
                url_copa_res = f"https://www.lapreferente.com/widgetResultados.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
                st.components.v1.html(
                    f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_res}"></iframe>', 
                    height=590,
                    scrolling=True
                )

# ==========================================
# 👤 PESTAÑA 2: ESTADÍSTICAS DE JUGADORES
# ==========================================
with tab_jugadores:
    st.markdown(f"### 📋 Rendimiento Individual | {filtro_competicion}")
    
    datos_jugadores = {}
    for p in st.session_state.plantilla:
        datos_jugadores[p["JUGADOR"]] = {
            "POS": p["POS"], "Convocatorias": 0, "Partidos Jugados": 0,
            "Minutos": 0.0, "Goles": 0, "Asistencias": 0, 
            "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0
        }
    
    for p in partidos:
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

    # Alertas de tarjetas
    if filtro_competicion in ["Liga", "Global (Todas)"]:
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
            st.markdown("#### ⚖️ Alertas Disciplinarias (Ciclos de 5 Amarillas)")
            c_al1, c_al2 = st.columns(2)
            with c_al1:
                if sancionados:
                    for s in sancionados: st.error(f"🛑 **SANCIONADO (Ciclo Cumplido):** {s}")
                else:
                    st.success("✅ Ningún jugador cumple ciclo.")
            with c_al2:
                if apercibidos:
                    for a in apercibidos: st.warning(f"⚠️ **APERCIBIDO (A una amarilla de sanción):** {a}")
                else:
                    st.info("✅ Ningún jugador apercibido.")
            st.markdown("---")

    lista_stats = []
    minutos_posibles = pj * 90 if pj > 0 else 0
    
    for jug, d in datos_jugadores.items():
        mins = d["Minutos"]
        goles = d["Goles"]
        asistencias = d["Asistencias"]
        
        min_por_gol = (mins / goles) if goles > 0 else 0
        min_por_asist = (mins / asistencias) if asistencias > 0 else 0
        porc_mins = (mins / minutos_posibles * 100) if minutos_posibles > 0 else 0
        
        lista_stats.append({
            "JUGADOR": jug,
            "POS": d["POS"],
            "Conv.": d["Convocatorias"],
            "PJ": d["Partidos Jugados"],
            "MIN": int(mins),
            "% MIN": porc_mins,
            "G": goles,
            "A": asistencias,
            "Min/Gol": min_por_gol,
            "Min/Asist": min_por_asist,
            "GE": d["Goles Encajados"],
            "🟨 TA": d["Amarillas"],
            "🟥 TR": d["Rojas"]
        })
        
    df_jugadores = pd.DataFrame(lista_stats)
    
    if not df_jugadores.empty:
        df_jugadores = df_jugadores.sort_values(by="MIN", ascending=False)
        
        c_f1, c_f2 = st.columns(2)
        filtro_pos = c_f1.selectbox("Filtro Rápido (Posición):", ["TODOS", "POR", "DEF", "MED", "ATA", "CANTERA"])
        
        if filtro_pos != "TODOS":
            df_mostrar = df_jugadores[df_jugadores["POS"] == filtro_pos]
        else:
            df_mostrar = df_jugadores
            
        st.markdown("##### Rendimiento y Minutos")
        estilo_jugadores = (df_mostrar.style
                            .hide(axis="index")
                            .format({
                                "% MIN": "{:.1f}%", 
                                "Min/Gol": lambda x: f"{x:.1f}'" if x > 0 else "-", 
                                "Min/Asist": lambda x: f"{x:.1f}'" if x > 0 else "-"
                            })
                            .background_gradient(subset=["MIN"], cmap="Blues")
                            .background_gradient(subset=["G"], cmap="Greens")
                            .background_gradient(subset=["🟨 TA"], cmap="YlOrBr")
                           )
                           
        mostrar_tabla_moderna(estilo_jugadores)
        st.caption("Acrónimos: Conv. (Convocatorias) | PJ (Partidos Jugados) | MIN (Minutos) | G (Goles) | A (Asistencias) | Min/Gol (Minutos por gol) | GE (Goles Encajados porteros).")

# ==========================================
# ⚙️ CONFIGURACIÓN ABAJO DE TODO EN PANTALLA (Solo si estamos en Liga o Copa)
# ==========================================
if filtro_competicion in ["Liga", "Copa"]:
    st.markdown("---")
    with st.expander(f"⚙️ Configurar ID de Competición para: {filtro_competicion}"):
        if filtro_competicion == "Liga":
            comp_id_default = st.session_state.get("lapreferente_comp_id", "26710")
            nuevo_comp_id = st.text_input("ID de Competición de Liga (LaPreferente):", value=comp_id_default)
            if nuevo_comp_id != comp_id_default:
                st.session_state["lapreferente_comp_id"] = nuevo_comp_id
                st.success("✅ ID de Liga actualizado correctamente.")
        elif filtro_competicion == "Copa":
            copa_id_default = st.session_state.get("lapreferente_copa_id", "")
            nuevo_copa_id = st.text_input("ID de Competición de Copa (LaPreferente):", value=copa_id_default)
            if nuevo_copa_id != copa_id_default:
                st.session_state["lapreferente_copa_id"] = nuevo_copa_id
                st.success("✅ ID de Copa actualizado correctamente.")
