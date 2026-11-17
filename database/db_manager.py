import streamlit as st
from supabase import create_client
import base64
import unicodedata
import numpy as np

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def asegurar_sesion_supabase():
    if "access_token" in st.session_state and st.session_state.access_token:
        try:
            supabase.postgrest.auth(st.session_state.access_token)
        except Exception:
            pass
        if "refresh_token" in st.session_state and st.session_state.refresh_token:
            try:
                sesion_actual = supabase.auth.get_session()
                if not sesion_actual:
                    res = supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
                    if res and res.session:
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        supabase.postgrest.auth(res.session.access_token)
            except Exception:
                pass

asegurar_sesion_supabase()

def sanitizar_para_supabase(obj):
    """Convierte tipos de NumPy/Pandas y limpia NaN/Inf para que PostgreSQL JSONB nunca rechace el guardado."""
    if isinstance(obj, dict):
        return {str(k): sanitizar_para_supabase(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitizar_para_supabase(x) for x in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif obj is None:
        return None
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj

def limpiar_nombre_archivo(texto):
    texto_limpio = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_limpio.replace(' ', '_').lower()

def _fetch_all_tabla(tabla, equipo_id):
    """Descarga todas las filas ordenadas cronológicamente por ID sin el límite de 1.000 filas de Supabase."""
    rows = []
    offset = 0
    step = 1000
    while True:
        try:
            res = supabase.table(tabla).select("*").eq("equipo_id", equipo_id).order("id", desc=False).range(offset, offset + step - 1).execute()
        except Exception:
            res = supabase.table(tabla).select("*").eq("equipo_id", equipo_id).range(offset, offset + step - 1).execute()
        batch = res.data if res and res.data else []
        rows.extend(batch)
        if len(batch) < step:
            break
        offset += step
    return rows

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_datos_equipo_supabase(equipo_id):
    asegurar_sesion_supabase()
    res_eq = supabase.table("equipos").select("*").eq("id", equipo_id).execute()
    plan_data = _fetch_all_tabla("plantilla", equipo_id)
    ses_data = _fetch_all_tabla("sesiones", equipo_id)
    les_data = _fetch_all_tabla("lesiones_historial", equipo_id)
    ant_data = _fetch_all_tabla("antropometria_historial", equipo_id)
    res_cfg = supabase.table("configuracion_equipo").select("*").eq("equipo_id", equipo_id).execute()
    return res_eq.data, plan_data, ses_data, les_data, ant_data, res_cfg.data

def _score_completitud_sesion(s):
    """Calcula la riqueza de datos de una sesión para no perder nunca informes, stats ni disponibilidad."""
    score = 0
    if s.get("informe_generado") and s.get("datos_informe"):
        score += 100 + len(s.get("datos_informe", []))
    if s.get("estadisticas_partido") and len(s.get("estadisticas_partido", {})) > 0:
        score += 50 + len(s.get("estadisticas_partido", {}))
    if s.get("disponibilidad") and len(s.get("disponibilidad", {})) > 0:
        score += 20
    if s.get("goles_favor") is not None or s.get("goles_contra") is not None:
        score += 10
    if s.get("clima"):
        score += 5
    return score

def cargar_datos_equipo(equipo_id):
    try:
        eq_data, plan_data, ses_data, les_data, ant_data, cfg_data = fetch_datos_equipo_supabase(equipo_id)
        if eq_data:
            eq = eq_data[0]
            st.session_state.equipo_creado = True
            st.session_state.equipo_id = equipo_id
            st.session_state.nombre_equipo = eq.get("nombre", "")
            st.session_state.categoria_equipo = eq.get("categoria", "")
            st.session_state.division_equipo = eq.get("division", "")
            st.session_state.temporada_equipo = eq.get("temporada", "")
            st.session_state.escudo_equipo = eq.get("escudo_base64", None) 
            st.session_state.color_sidebar = eq.get("color_sidebar", "#f1f5f9")
            
            plantilla = []
            for p in plan_data:
                plantilla.append({
                    "JUGADOR": p["jugador"], "POS": p["pos"], "pos_1": p["pos_1"],
                    "pos_2": p["pos_2"], "edad": p["edad"], "dorsal": p["dorsal"],
                    "altura": p["altura"], "lateralidad": p["lateralidad"],
                    "foto": p["foto_url"]
                })
            st.session_state.plantilla = plantilla

            sesiones = []
            for s in ses_data:
                sesiones.append({
                    "fecha": s["fecha"], "tipo": s["tipo"], "descripcion": s["descripcion"],
                    "competicion": s["competicion"], "rival": s["rival"], "condicion": s["condicion"],
                    "ciudad_manual": s["ciudad_manual"], "goles_favor": s["goles_favor"],
                    "goles_contra": s["goles_contra"], "clima": s["clima"],
                    "disponibilidad": s["disponibilidad"] or {}, "estadisticas_partido": s["estadisticas_partido"] or {},
                    "estadisticas_invitados": s["estadisticas_invitados"] or [], "informe_generado": bool(s["informe_generado"]),
                    "datos_informe": s["datos_informe"] or []
                })
            st.session_state.sesiones = sesiones
            st.session_state.lesiones = les_data
            st.session_state.antropometria = [a["datos"] for a in ant_data if isinstance(a.get("datos"), dict)]

            # --- DEDUPLICACIÓN INTELIGENTE CON FUSIÓN DE CAMPOS ---
            mapa_ses = {}
            for s in st.session_state.sesiones:
                uid = f"{s['fecha']}_{s['tipo']}_{s.get('descripcion','')}_{s.get('rival','')}"
                if uid not in mapa_ses:
                    mapa_ses[uid] = s
                else:
                    prev = mapa_ses[uid]
                    # Fusionar campos valiosos si una copia tiene stats y la otra tiene informe GPS
                    merged = s.copy() if _score_completitud_sesion(s) >= _score_completitud_sesion(prev) else prev.copy()
                    if not (merged.get("informe_generado") and merged.get("datos_informe")) and (prev.get("informe_generado") and prev.get("datos_informe")):
                        merged["informe_generado"] = True
                        merged["datos_informe"] = prev["datos_informe"]
                    if not merged.get("estadisticas_partido") and prev.get("estadisticas_partido"):
                        merged["estadisticas_partido"] = prev["estadisticas_partido"]
                        if merged.get("goles_favor") is None: merged["goles_favor"] = prev.get("goles_favor")
                        if merged.get("goles_contra") is None: merged["goles_contra"] = prev.get("goles_contra")
                    if not merged.get("disponibilidad") and prev.get("disponibilidad"):
                        merged["disponibilidad"] = prev["disponibilidad"]
                    if not merged.get("estadisticas_invitados") and prev.get("estadisticas_invitados"):
                        merged["estadisticas_invitados"] = prev["estadisticas_invitados"]
                    mapa_ses[uid] = merged
            st.session_state.sesiones = list(mapa_ses.values())
            
            mapa_plan = {}
            for p in st.session_state.plantilla:
                mapa_plan[p["JUGADOR"]] = p
            st.session_state.plantilla = list(mapa_plan.values())

            mapa_les = {}
            for l in st.session_state.lesiones:
                uid_les = f"{l.get('id_sesion','')}_{l.get('jugador','')}_{l.get('tipo','')}"
                mapa_les[uid_les] = l
            st.session_state.lesiones = list(mapa_les.values())

            mapa_ant = {}
            for a in st.session_state.antropometria:
                uid_ant = f"{a.get('fecha','')}_{a.get('jugador','')}"
                mapa_ant[uid_ant] = a
            st.session_state.antropometria = list(mapa_ant.values())

            cfg = cfg_data[0] if cfg_data else {}
            st.session_state.val_inicial = cfg.get("val_inicial", [])
            st.session_state.val_rom = cfg.get("val_rom", [])
            st.session_state.val_1rm = cfg.get("val_1rm", [])
            st.session_state.ubicacion_local = cfg.get("ubicacion_local", "Santiago de Compostela")
            st.session_state.rivales_guardados = cfg.get("rivales_guardados", {})
            if cfg.get("lapreferente_comp_id"):
                st.session_state.lapreferente_comp_id = cfg.get("lapreferente_comp_id")
            if cfg.get("lapreferente_copa_id"):
                st.session_state.lapreferente_copa_id = cfg.get("lapreferente_copa_id")
            
            st.session_state.config_mapeo = cfg.get("config_mapeo", {})
            if not st.session_state.config_mapeo:
                st.session_state.config_mapeo = {
                    "wellness": {"nombre": "Nombre", "fecha": "Marca temporal", "tqr": "TQR", "fatiga": "W_Fatiga", "sueno": "W_Sueño", "dolor": "W_Dolor", "estres": "W_Estres", "humor": "W_Humor"},
                    "rpe": {"nombre": "Nombre", "fecha": "Marca temporal", "minutos": "MIN", "rpe": "RPE"},
                    "gps": {
                        "nombre": "Player Name", "fecha": "Activity Date",
                        "min_gps": "Time Played", "dis": "Distance (km)", "v_med": "Avg Speed (km/h)", "v_max": "Max Speed (km/h)",
                        "hid_21": "HID distance (> 21.00 km/h)", "hid_24": "HID distance (> 24.00 km/h)", 
                        "spr_24": "# of Sprints (> 24.00 km/h)", "spr_27": "# of Sprints (> 30.00 km/h)",
                        "acc_max": "ACC. MÁXIMA", "acc_2": "# of Accelerations (> 2.00 m/s²)", "acc_3": "# of Accelerations (> 3.00 m/s²)", "acc_4": "# of Accelerations (> 4.00 m/s²)",
                        "dcc_2": "# of Decelerations (> 2.00 m/s²)", "dcc_3": "# of Decelerations (> 3.00 m/s²)", "dcc_4": "# of Decelerations (> 4.00 m/s²) ",
                        "r_0_7": "Distance Speed Range (0 - 7 km)", "r_7_14": "Distance Speed Range (7 - 14 km)", "r_14_21": "Distance Speed Range (14 - 21 km)",
                        "r_21_24": "Distance Speed Range (21 - 24 km)", "r_24_27": "Distance Speed Range (24 - 27 km)", "r_27_30": "Distance Speed Range (27 - 30 km)", "r_30_45": "Distance Speed Range (30 - 45 km)"
                    }
                }
            st.session_state.datos_cargados = True
            reconstruir_dataframes_globales()
            return True
    except Exception as e:
        st.error(f"Error al cargar desde Supabase: {e}")
    return False

def guardar_datos(modulo="todo"):
    if "equipo_id" not in st.session_state: return False
    eq_id = st.session_state.equipo_id
    asegurar_sesion_supabase()

    def safe_sync(tabla, datos_nuevos):
        if "equipo_id" not in st.session_state: return
        eq_id = st.session_state.equipo_id
        
        # 1. Obtener todas las filas existentes (incluso si superaron las 1.000)
        filas_existentes = _fetch_all_tabla(tabla, eq_id)
        ids_existentes = [row["id"] for row in filas_existentes if "id" in row]
        backup = [
            {k: v for k, v in row.items() if k not in ("id", "created_at")}
            for row in filas_existentes
        ]
        try:
            # 2. Deduplicar en memoria y sanitizar tipos para PostgreSQL JSONB
            mapa_limpios = {}
            for idx_item, item in enumerate(datos_nuevos or []):
                item_clean = sanitizar_para_supabase(item)
                if tabla == "sesiones":
                    uid = f"{item_clean.get('fecha')}_{item_clean.get('tipo')}_{item_clean.get('descripcion','')}_{item_clean.get('rival','')}"
                elif tabla == "plantilla":
                    uid = str(item_clean.get("jugador", "")).strip().lower()
                elif tabla == "lesiones_historial":
                    uid = f"{item_clean.get('id_sesion','')}_{item_clean.get('jugador','')}_{item_clean.get('tipo','')}"
                elif tabla == "antropometria_historial":
                    uid = f"{item_clean.get('fecha','')}_{item_clean.get('jugador','')}"
                else:
                    uid = f"{idx_item}_{str(item_clean)}"
                mapa_limpios[uid] = item_clean

            datos_limpios = list(mapa_limpios.values())

            # 3. Borrado completo por equipo_id y por lotes de IDs
            supabase.table(tabla).delete().eq("equipo_id", eq_id).execute()
            if ids_existentes:
                for i in range(0, len(ids_existentes), 100):
                    supabase.table(tabla).delete().in_("id", ids_existentes[i:i+100]).execute()

            # 4. Inserción en lotes seguros
            batch_size = 20 if tabla == "sesiones" else 50
            if datos_limpios:
                for i in range(0, len(datos_limpios), batch_size):
                    supabase.table(tabla).insert(datos_limpios[i:i+batch_size]).execute()
        except Exception as e:
            print(f"Error crítico en {tabla}: {e}. Restaurando backup...")
            if backup:
                supabase.table(tabla).delete().eq("equipo_id", eq_id).execute()
                for i in range(0, len(backup), 20):
                    supabase.table(tabla).insert(backup[i:i+20]).execute()
            raise e

    try:
        # 1. GUARDAR EQUIPO Y CONFIGURACIÓN
        if modulo in ["todo", "equipo", "configuracion"]:
            escudo_actual = st.session_state.get("escudo_equipo")
            if escudo_actual and not str(escudo_actual).startswith("http") and len(escudo_actual) > 1000:
                try:
                    b64_clean = escudo_actual.split(",")[1] if escudo_actual.startswith("data:image") else escudo_actual
                    img_bytes = base64.b64decode(b64_clean)
                    nombre_arch = f"{eq_id}/escudo_club.jpg"
                    supabase.storage.from_("loadlab_media").upload(nombre_arch, img_bytes, file_options={"content-type": "image/jpeg", "upsert": "true"})
                    import time
                    url_base = supabase.storage.from_("loadlab_media").get_public_url(nombre_arch)
                    escudo_actual = f"{url_base}?t={int(time.time())}"
                    st.session_state.escudo_equipo = escudo_actual
                except Exception as e:
                    print(f"Error subiendo escudo: {e}")

            supabase.table("equipos").update({
                "nombre": st.session_state.nombre_equipo, "categoria": st.session_state.categoria_equipo,
                "division": st.session_state.division_equipo, "temporada": st.session_state.temporada_equipo,
                "escudo_base64": escudo_actual 
            }).eq("id", eq_id).execute()

            supabase.table("configuracion_equipo").upsert({
                "equipo_id": eq_id, "ubicacion_local": st.session_state.get("ubicacion_local", "Santiago de Compostela"),
                "color_sidebar": st.session_state.get("color_sidebar", "#f1f5f9"), "rivales_guardados": st.session_state.get("rivales_guardados", {}),
                "config_mapeo": st.session_state.get("config_mapeo", {}), "val_inicial": st.session_state.get("val_inicial", []),
                "val_rom": st.session_state.get("val_rom", []), "val_1rm": st.session_state.get("val_1rm", [])
            }).execute()

        # 2. GUARDAR PLANTILLA
        if modulo in ["todo", "plantilla"]:
            plantilla_db = []
            for p in st.session_state.plantilla:
                foto_url = p.get("foto")
                if foto_url and not str(foto_url).startswith("http") and len(foto_url) > 1000:
                    try:
                        b64_clean = foto_url.split(",")[1] if foto_url.startswith("data:image") else foto_url
                        img_bytes = base64.b64decode(b64_clean)
                        nombre_arch = f"{eq_id}/jugadores/{limpiar_nombre_archivo(p['JUGADOR'])}.jpg"
                        supabase.storage.from_("loadlab_media").upload(nombre_arch, img_bytes, file_options={"content-type": "image/jpeg", "x-upsert": "true"})
                        import time
                        url_base = supabase.storage.from_("loadlab_media").get_public_url(nombre_arch)
                        foto_url = f"{url_base}?t={int(time.time())}"
                        p["foto"] = foto_url
                    except Exception as e:
                        print(f"Error subiendo foto al guardar: {e}")
                
                plantilla_db.append({
                    "equipo_id": eq_id, "jugador": p.get("JUGADOR"), "pos": p.get("POS"),
                    "pos_1": p.get("pos_1"), "pos_2": p.get("pos_2"), "edad": p.get("edad"),
                    "dorsal": p.get("dorsal"), "altura": p.get("altura"),
                    "lateralidad": p.get("lateralidad"), "foto_url": foto_url
                })
            safe_sync("plantilla", plantilla_db)

        # 3. GUARDAR SESIONES
        if modulo in ["todo", "sesiones"]:
            sesiones_db = []
            for s in st.session_state.sesiones:
                sesiones_db.append({
                    "equipo_id": eq_id, "fecha": s.get("fecha"), "tipo": s.get("tipo"), "descripcion": s.get("descripcion"),
                    "competicion": s.get("competicion"), "rival": s.get("rival"), "condicion": s.get("condicion"),
                    "ciudad_manual": s.get("ciudad_manual"), "goles_favor": s.get("goles_favor"), "goles_contra": s.get("goles_contra"),
                    "clima": s.get("clima") or {}, "disponibilidad": s.get("disponibilidad") or {}, "estadisticas_partido": s.get("estadisticas_partido") or {},
                    "estadisticas_invitados": s.get("estadisticas_invitados") or [], "informe_generado": bool(s.get("informe_generado", False)),
                    "datos_informe": s.get("datos_informe") or []
                })
            safe_sync("sesiones", sesiones_db)

        # 4. GUARDAR LESIONES
        if modulo in ["todo", "lesiones"]:
            lesiones_db = []
            for l in st.session_state.lesiones:
                lesiones_db.append({
                    "equipo_id": eq_id, "fecha_registro": l.get("fecha_registro"), "id_sesion": l.get("id_sesion"),
                    "tipo_sesion": l.get("tipo_sesion"), "jugador": l.get("jugador"), "tipo": l.get("tipo"),
                    "zona": l.get("zona"), "lado": l.get("lado"), "lateralidad": l.get("lateralidad"),
                    "contacto": l.get("contacto"), "cesped": l.get("cesped"), "recidiva": l.get("recidiva"),
                    "estado": l.get("estado"), "dias_baja": l.get("dias_baja"), "comentarios": l.get("comentarios")
                })
            safe_sync("lesiones_historial", lesiones_db)

        # 5. GUARDAR ANTROPOMETRÍA
        if modulo in ["todo", "antropometria"]:
            antro_db = [{"equipo_id": eq_id, "fecha": a.get("fecha"), "jugador": a.get("jugador"), "datos": a} for a in st.session_state.antropometria]
            safe_sync("antropometria_historial", antro_db)

        fetch_datos_equipo_supabase.clear()
        reconstruir_dataframes_globales()
        return True
            
    except Exception as e:
        st.error(f"🚨 Error crítico al guardar en Supabase ({modulo}): {e}")
        st.stop()
        return False

import pandas as pd

def reconstruir_dataframes_globales():
    """Construye todos los DataFrames pesados una sola vez en la RAM listos para usar"""
    
    # 1. DATAFRAME DE PLANTILLA
    if "plantilla" in st.session_state and st.session_state.plantilla:
        st.session_state.df_plantilla = pd.DataFrame(st.session_state.plantilla)
    else:
        st.session_state.df_plantilla = pd.DataFrame()

    # 2. DATAFRAME DE LESIONES
    if "lesiones" in st.session_state and st.session_state.lesiones:
        st.session_state.df_lesiones = pd.DataFrame(st.session_state.lesiones)
    else:
        st.session_state.df_lesiones = pd.DataFrame()

    # 3. DATAFRAME DE ANTROPOMETRÍA
    if "antropometria" in st.session_state and st.session_state.antropometria:
        st.session_state.df_antropometria = pd.DataFrame(st.session_state.antropometria)
    else:
        st.session_state.df_antropometria = pd.DataFrame()

    # 4. DATAFRAME DE SESIONES (Ligero, solo el calendario)
    if "sesiones" in st.session_state and st.session_state.sesiones:
        sesiones_ligero = []
        for s in st.session_state.sesiones:
            # Copiamos la sesión pero omitimos la lista pesada de 'datos_informe'
            ses_copy = {k: v for k, v in s.items() if k != 'datos_informe'}
            sesiones_ligero.append(ses_copy)
        st.session_state.df_sesiones = pd.DataFrame(sesiones_ligero)
    else:
        st.session_state.df_sesiones = pd.DataFrame()

    # 5. EL MAESTRO: GPS, Carga, Wellness y ESTADO
    datos_completos = []
    if "sesiones" in st.session_state:
        for s in st.session_state.sesiones:
            if s.get("informe_generado") and s.get("datos_informe"):
                disp_s = s.get("disponibilidad", {})
                disp_clean = {str(k).strip().lower(): v for k, v in disp_s.items()}
                
                for d in s["datos_informe"]:
                    row = d.copy() 
                    row["FECHA"] = s.get("fecha")
                    row["TIPO_SESION"] = s.get("tipo")
                    row["MD"] = "MD" if "Partido" in str(s.get("tipo", "")) else s.get("descripcion", "")
                    row["COMPETICION"] = s.get("competicion", "")
                    row["RIVAL"] = s.get("rival", "")
                    
                    jug_key = str(d["JUGADOR"]).strip().lower()
                    estado_default = "Titular" if "Partido" in s.get("tipo", "") else "Disponible"
                    row["ESTADO"] = disp_clean.get(jug_key, estado_default)
                    
                    datos_completos.append(row)
                    
    if datos_completos:
        df_master = pd.DataFrame(datos_completos)
        
        # --- PARCHE DE COMPATIBILIDAD HISTÓRICA (+60 SESIONES ANTIGUAS) ---
        # Unifica las nomenclaturas antiguas (Excel) con las variables de cálculo EWMA
        if 'DIS AI' not in df_master.columns: df_master['DIS AI'] = np.nan
        if 'HID >21' in df_master.columns: df_master['DIS AI'] = df_master['DIS AI'].fillna(df_master['HID >21'])
        
        if 'ACC' not in df_master.columns: df_master['ACC'] = np.nan
        if 'ACC >3' in df_master.columns: df_master['ACC'] = df_master['ACC'].fillna(df_master['ACC >3'])
        
        # Blindaje matemático: forzar conversión a números para evitar que un string ("") rompa el EWMA
        for c in ['CARGA', 'DIS AI', 'ACC']:
            if c in df_master.columns:
                df_master[c] = pd.to_numeric(df_master[c], errors='coerce').fillna(0.0)
        # ------------------------------------------------------------------
        
        # --- CÁLCULO VECTORIZADO DEL RATIO A/C (EWMA) ---
        df_master['FECHA_DT'] = pd.to_datetime(df_master['FECHA'])
        
        # Integración de la Carga de Compensación Post-Partido
        if 'COMP_DIS_AI' not in df_master.columns: df_master['COMP_DIS_AI'] = 0.0
        if 'COMP_ACC' not in df_master.columns: df_master['COMP_ACC'] = 0.0
        
        df_master['EWMA_DIS_AI'] = pd.to_numeric(df_master['DIS AI'], errors='coerce').fillna(0.0) + pd.to_numeric(df_master['COMP_DIS_AI'], errors='coerce').fillna(0.0)
        df_master['EWMA_ACC'] = pd.to_numeric(df_master['ACC'], errors='coerce').fillna(0.0) + pd.to_numeric(df_master['COMP_ACC'], errors='coerce').fillna(0.0)
        
        # Mapeo de columnas objetivo y sus sufijos para el DataFrame Maestro
        metricas_ewma = {'CARGA': '', 'EWMA_DIS_AI': ' HSR', 'EWMA_ACC': ' ACC'}
        
        # Eliminar las columnas estáticas si vienen del JSON de Supabase para evitar conflictos de sufijos
        columnas_dinamicas = ['EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C', 'EWMA AGUDA HSR', 'EWMA CRÓNICA HSR', 'RATIO A/C HSR', 'EWMA AGUDA ACC', 'EWMA CRÓNICA ACC', 'RATIO A/C ACC']
        df_master.drop(columns=[col for col in columnas_dinamicas if col in df_master.columns], inplace=True, errors='ignore')
        
        # Detectar únicamente días pre-sesión (solo Wellness matutino cargado, CARGA total del equipo == 0)
        df_carga_eq = df_master.groupby('FECHA_DT')['CARGA'].sum() if 'CARGA' in df_master.columns else pd.Series(dtype=float)
        fechas_pendientes_carga = df_carga_eq[df_carga_eq == 0].index

        for col_metrica, sufijo in metricas_ewma.items():
            if col_metrica not in df_master.columns: continue
                
            df_pivot = df_master.pivot_table(index='FECHA_DT', columns='JUGADOR', values=col_metrica, aggfunc='sum').fillna(0)
            
            if not df_pivot.empty:
                fechas_pendientes = df_pivot.index.intersection(fechas_pendientes_carga)
                rango_fechas = pd.date_range(start=df_pivot.index.min() - pd.Timedelta(days=7), end=df_pivot.index.max(), freq='D')
                df_pivot = df_pivot.reindex(rango_fechas, fill_value=0)
                
                for col in df_pivot.columns:
                    s_cargas = df_pivot[col]
                    primer_dia_valido = s_cargas[s_cargas > 0].first_valid_index()
                    if primer_dia_valido:
                        ventana_ini = s_cargas.loc[primer_dia_valido : primer_dia_valido + pd.Timedelta(days=6)]
                        media_ini = ventana_ini.sum() / 7.0 if len(ventana_ini) >= 7 else ventana_ini.mean()
                        inicio_semilla = primer_dia_valido - pd.Timedelta(days=7)
                        df_pivot.loc[:inicio_semilla - pd.Timedelta(days=1), col] = np.nan
                        df_pivot.loc[inicio_semilla : primer_dia_valido - pd.Timedelta(days=1), col] = media_ini
                
                # Cálculo Uncoupled EWMA con estabilizador de carga crónica y límite fisiológico (4.0)
                aguda = df_pivot.ewm(span=7, adjust=False).mean() * 7
                cronica = df_pivot.shift(7).ewm(span=21, adjust=False).mean() * 7
                
                if len(fechas_pendientes) > 0:
                    aguda.loc[fechas_pendientes] = np.nan
                    cronica.loc[fechas_pendientes] = np.nan
                    aguda = aguda.ffill()
                    cronica = cronica.ffill()
                c_min = 10.0 if col_metrica == 'CARGA' else 1.0
                cronica_segura = cronica.clip(lower=c_min).where(cronica > 0, np.nan)
                ratio = (aguda / cronica_segura).clip(upper=4.0)
                
                a_melt = aguda.reset_index().melt(id_vars='index', var_name='JUGADOR', value_name=f'EWMA AGUDA{sufijo}')
                c_melt = cronica.reset_index().melt(id_vars='index', var_name='JUGADOR', value_name=f'EWMA CRÓNICA{sufijo}')
                r_melt = ratio.reset_index().melt(id_vars='index', var_name='JUGADOR', value_name=f'RATIO A/C{sufijo}')
                
                for df_melt in [a_melt, c_melt, r_melt]:
                    df_melt.rename(columns={'index': 'FECHA_DT'}, inplace=True)
                
                df_master = df_master.merge(a_melt, on=['FECHA_DT', 'JUGADOR'], how='left')
                df_master = df_master.merge(c_melt, on=['FECHA_DT', 'JUGADOR'], how='left')
                df_master = df_master.merge(r_melt, on=['FECHA_DT', 'JUGADOR'], how='left')
                
                df_master[f'RATIO A/C{sufijo}'] = df_master[f'RATIO A/C{sufijo}'].fillna(1.0)
                df_master[f'EWMA AGUDA{sufijo}'] = df_master[f'EWMA AGUDA{sufijo}'].fillna(0.0)
                df_master[f'EWMA CRÓNICA{sufijo}'] = df_master[f'EWMA CRÓNICA{sufijo}'].fillna(0.0)
                
        df_master.drop(columns=['FECHA_DT'], inplace=True, errors='ignore')
        st.session_state.df_master_informes = df_master
    else:
        st.session_state.df_master_informes = pd.DataFrame()
