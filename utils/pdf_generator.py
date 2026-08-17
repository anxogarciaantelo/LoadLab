import os
import tempfile
from fpdf import FPDF
import pandas as pd

def generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, dict_figs):
    # Formato horizontal (Landscape)
    pdf = FPDF(orientation='L', unit='mm', format='A4') 
    pdf.set_auto_page_break(auto=True, margin=15)

    # CORRECCIÓN EMOJIS: 'ignore' elimina los caracteres especiales sin dejar '?'
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()

    # Paleta de colores
    C_PRIMARY = (41, 128, 185)
    C_BG_KPI = (240, 240, 240)
    C_BG_TAB_H = (220, 220, 220)
    C_BG_TAB_R = (248, 248, 248)

    # Guardar temporalmente las imágenes
    img_paths = {}
    for name, fig in dict_figs.items():
        if fig is not None:
            # 1. Forzar fondo blanco sólido
            fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            
            # 2. Cambiar a JPG para que FPDF no pierda los colores por la transparencia
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=750, height=450, format="jpg")
            img_paths[name] = tmp.name

    pdf.add_page()

    # --- PORTADA Y TÍTULO ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_txt(f"INFORME DE SESIÓN | {sesion['fecha']} | {sesion.get('tipo', '')}"), ln=True, align='C')
    pdf.ln(5)

    # --- KPIs GLOBALES ---
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi = 277 / 4 
    
    tqr_m = df_para_medias['TQR'].mean() if not df_para_medias.empty else 0
    well_m = df_para_medias['WELLNESS'].mean() if not df_para_medias.empty else 0
    rpe_m = df_para_medias['RPE'].mean() if not df_para_medias.empty else 0
    carga_m = df_para_medias['CARGA'].mean() if not df_para_medias.empty else 0

    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"TQR Medio (Recuperación)\n{tqr_m:.1f} / 10"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Wellness Medio (Fatiga)\n{well_m:.1f} pts"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"RPE Medio (Esfuerzo)\n{rpe_m:.1f} / 10"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Carga Media Sesión\n{carga_m:.0f} UA"), border=1, align='C', fill=True)
    pdf.ln(8)

    # --- SECCIÓN 1: BIENESTAR ---
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("1. Bienestar y Recuperación"), ln=True)
    pdf.set_text_color(0, 0, 0)

    y_img = pdf.get_y()
    if "Desglose de Wellness" in img_paths:
        pdf.image(img_paths["Desglose de Wellness"], x=10, y=y_img, w=135)
    if "Calidad de Recuperación (TQR)" in img_paths:
        pdf.image(img_paths["Calidad de Recuperación (TQR)"], x=150, y=y_img, w=135)
    
    # --- SECCIÓN 2: CARGA INTERNA ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("2. Carga Interna (RPE & Acumulada)"), ln=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi3 = 277 / 3
    y_kpi = pdf.get_y()
    min_m = df_para_medias['MIN'].mean() if not df_para_medias.empty else 0
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"Minutos Sesión (Media)\n{min_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi3, y_kpi)
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"RPE Medio\n{rpe_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi3*2, y_kpi)
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"Carga Media (UA)\n{carga_m:.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_img = pdf.get_y()
    if "Carga de Sesión" in img_paths:
        pdf.image(img_paths["Carga de Sesión"], x=10, y=y_img, w=135)
    if "Riesgo de Lesión (Ratio A/C)" in img_paths:
        pdf.image(img_paths["Riesgo de Lesión (Ratio A/C)"], x=150, y=y_img, w=135)
    
    # Salto de página para la primera tabla
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    cols_ci = ['JUGADOR', 'POS', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']
    widths_ci = [45, 15, 25, 20, 15, 20, 30, 32, 25] 
    
    offset_x = (297 - sum(widths_ci)) / 2
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_ci):
        pdf.cell(widths_ci[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    row_count = 0
    for _, row in df_graficos.iterrows():
        pdf.set_x(offset_x)
        if row_count % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_ci):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:20]
            pdf.cell(widths_ci[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()
        row_count += 1

    # --- SECCIÓN 3: CARGA EXTERNA ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("3. Carga Externa (GPS) - Solo jugadores con GPS > 0m"), ln=True)
    pdf.set_text_color(0, 0, 0)

    df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0]
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi5 = 277 / 5
    y_kpi = pdf.get_y()
    
    dis_m = df_para_medias_gps['DIS'].mean() if not df_para_medias_gps.empty else 0
    hsr_m = df_para_medias_gps['DIS AI'].mean() if not df_para_medias_gps.empty else 0
    spr_m = df_para_medias_gps['Nº SPR'].mean() if not df_para_medias_gps.empty else 0
    acc_m = df_para_medias_gps['ACC'].mean() if not df_para_medias_gps.empty else 0
    dcc_m = df_para_medias_gps['DCC'].mean() if not df_para_medias_gps.empty else 0

    pdf.multi_cell(w_kpi5, 6, clean_txt(f"Distancia (km)\n{dis_m:.2f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"HSR (>21 km/h)\n{hsr_m:.2f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*2, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"Nº SPRINTS (>24)\n{spr_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*3, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"ACC (>3 m/s²)\n{acc_m:.0f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*4, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"DCC (>3 m/s²)\n{dcc_m:.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_img = pdf.get_y()
    if "Volumen vs Intensidad" in img_paths:
        pdf.image(img_paths["Volumen vs Intensidad"], x=10, y=y_img, w=135)
    if "ACC vs DCC" in img_paths:
        pdf.image(img_paths["ACC vs DCC"], x=150, y=y_img, w=135)
    
    # Salto de página para la segunda tabla
    pdf.add_page()
    
    if 'HID >21' not in df_graficos.columns:
        df_graficos['HID >21'] = df_graficos.get('DIS AI', 0.0)

    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    cols_ce = ['JUGADOR', 'POS', 'ESTADO', 'DIS', 'HID >21', 'Nº SPR', 'ACC', 'DCC', 'VMAX']
    widths_ce = [45, 15, 25, 20, 25, 20, 20, 20, 20]
    
    offset_x = (297 - sum(widths_ce)) / 2
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_ce):
        pdf.cell(widths_ce[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    row_count = 0
    for _, row in df_graficos.iterrows():
        pdf.set_x(offset_x)
        if row_count % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_ce):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:20]
            pdf.cell(widths_ce[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()
        row_count += 1

    # --- SECCIÓN 4: ALERTAS MÉDICAS ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, clean_txt("Alertas de Rendimiento y Riesgo"), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)

    if not alertas_multi and not alertas_rec and not alertas_car:
        pdf.cell(0, 6, clean_txt("Todo en parámetros normales."), ln=True)
    else:
        if alertas_multi:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, clean_txt("RIESGO MULTIFACTORIAL (2 o más alertas simultáneas):"), ln=True)
            pdf.set_font("Arial", '', 10)
            for al in alertas_multi: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
            pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, clean_txt("Recuperación (1 alerta):"), ln=True)
        pdf.set_font("Arial", '', 10)
        if alertas_rec:
            for al in alertas_rec: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
        else:
            pdf.cell(0, 6, clean_txt("Sin alertas individuales."), ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, clean_txt("Carga (1 alerta):"), ln=True)
        pdf.set_font("Arial", '', 10)
        if alertas_car:
            for al in alertas_car: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
        else:
            pdf.cell(0, 6, clean_txt("Sin alertas individuales."), ln=True)

    # Limpieza de imágenes temporales
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

import tempfile
import os
from fpdf import FPDF

def generar_pdf_microciclo(nombre_micro, df_diario, df_indiv, kpis_globales, dict_figs):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    C_PRIMARY = (41, 128, 185)
    C_BG_KPI = (240, 240, 240)
    C_BG_TAB_H = (220, 220, 220)
    C_BG_TAB_R = (248, 248, 248)

    # Exportar gráficos de Plotly a JPG temporales
    img_paths = {}
    for name, fig in dict_figs.items():
        if fig is not None:
            fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=750, height=450, format="jpg")
            img_paths[name] = tmp.name

    pdf.add_page()

    # TÍTULO
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_txt(f"INFORME DE MICROCICLO | {nombre_micro}"), ln=True, align='C')
    pdf.ln(5)

    # BLOQUE DE KPIs
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi = 277 / 5
    
    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Wellness Medio\n{kpis_globales.get('Wellness', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"TQR Medio\n{kpis_globales.get('TQR', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"RPE Medio\n{kpis_globales.get('RPE', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Minutos Totales\n{kpis_globales.get('Minutos', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*4, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Carga Total (UA)\n{kpis_globales.get('Carga', 0):.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Distancia Total\n{kpis_globales.get('DIS', 0):.2f} km"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"HSR Total\n{kpis_globales.get('HSR', 0):.2f} m"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Sprints Totales\n{kpis_globales.get('SPR', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"ACC Totales\n{kpis_globales.get('ACC', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*4, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"DCC Totales\n{kpis_globales.get('DCC', 0):.1f}"), border=1, align='C', fill=True)
    pdf.ln(10)

    # TABLA: RESUMEN POR DÍA
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Resumen por Día"), ln=True)
    pdf.set_text_color(0, 0, 0)
    
    cols_dia = ['DIA', 'WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_dia = [25, 25, 20, 20, 20, 25, 25, 25, 25, 25, 25] 
    offset_x = (297 - sum(widths_dia)) / 2
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_dia):
        pdf.cell(widths_dia[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    for r_idx, row in df_diario.iterrows():
        pdf.set_x(offset_x)
        if r_idx % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_dia):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            pdf.cell(widths_dia[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()

    # SECCIÓN: GRÁFICOS DE BIENESTAR
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Bienestar"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    if "TQR" in img_paths: pdf.image(img_paths["TQR"], x=10, y=y_img, w=135)
    if "Wellness" in img_paths: pdf.image(img_paths["Wellness"], x=150, y=y_img, w=135)

    # SECCIÓN: GRÁFICOS DE CARGA INTERNA
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Carga Interna"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    w_img3 = 277 / 3
    if "Minutos" in img_paths: pdf.image(img_paths["Minutos"], x=10, y=y_img, w=w_img3)
    if "RPE" in img_paths: pdf.image(img_paths["RPE"], x=10 + w_img3, y=y_img, w=w_img3)
    if "Carga" in img_paths: pdf.image(img_paths["Carga"], x=10 + w_img3*2, y=y_img, w=w_img3)

    # SECCIÓN: GRÁFICOS DE CARGA EXTERNA
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Carga Externa (Solo datos GPS > 0m)"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    if "ACC_DCC" in img_paths: pdf.image(img_paths["ACC_DCC"], x=10, y=y_img, w=w_img3)
    if "DIS" in img_paths: pdf.image(img_paths["DIS"], x=10 + w_img3, y=y_img, w=w_img3)
    if "DIS_AI" in img_paths: pdf.image(img_paths["DIS_AI"], x=10 + w_img3*2, y=y_img, w=w_img3)

    # TABLA: RESUMEN SEMANAL POR JUGADOR
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Resumen Semanal por Jugador"), ln=True)
    pdf.set_text_color(0, 0, 0)
    
    cols_indiv = ['JUGADOR', 'POS', 'MIN', 'TQR', 'WELLNESS', 'RPE', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_indiv = [40, 15, 15, 15, 22, 15, 20, 20, 20, 20, 20, 20] 
    offset_x_indiv = (297 - sum(widths_indiv)) / 2
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    pdf.set_x(offset_x_indiv)
    for i, col in enumerate(cols_indiv):
        pdf.cell(widths_indiv[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    for r_idx, row in df_indiv.iterrows():
        pdf.set_x(offset_x_indiv)
        if r_idx % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_indiv):
            val = row.get(col, 0)
            if isinstance(val, float):
                val_str = f"{val:.1f}" if col in ['TQR', 'WELLNESS', 'RPE', 'Nº SPR', 'ACC', 'DCC'] else f"{val:.2f}" if col in ['DIS', 'DIS AI'] else f"{val:.0f}"
            else:
                val_str = str(val)[:20]
            pdf.cell(widths_indiv[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()

    # LIMPIEZA ARCHIVOS TEMPORALES
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

import base64
import tempfile
import os
from fpdf import FPDF

def generar_pdf_antropometria_jugador(jugador_nombre, jugador_info, fecha_pesaje, kpis_pesaje, kpis_perimetros, kpis_asimetrias, dict_figs, df_historial, escudo_b64, foto_b64):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    C_PRIMARY = (41, 128, 185)
    C_BG_TAB_H = (0, 0, 0)
    C_BG_TAB_R = (248, 248, 248)
    
    img_paths = {}
    
    if escudo_b64:
        tmp_esc = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp_esc.write(base64.b64decode(escudo_b64))
        tmp_esc.close()
        img_paths['escudo'] = tmp_esc.name
        
    if foto_b64:
        tmp_foto = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp_foto.write(base64.b64decode(foto_b64))
        tmp_foto.close()
        img_paths['foto'] = tmp_foto.name
        
    for name, fig in dict_figs.items():
        if fig is not None:
            # Aumentamos márgenes (Izquierdo 'l' e Inferior 'b') para evitar superposiciones y recortes
            fig.update_layout(
                paper_bgcolor="white", 
                plot_bgcolor="white", 
                font=dict(color="black"), 
                margin=dict(l=70, r=20, t=40, b=70)
            )
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=800, height=350, format="jpg")
            img_paths[name] = tmp.name
            
    pdf.add_page()
    
    # --- HEADER: FOTO, NOMBRE, ESCUDO (CENTRADO) ---
    if 'foto' in img_paths:
        pdf.image(img_paths['foto'], x=20, y=10, w=25)
    if 'escudo' in img_paths:
        pdf.image(img_paths['escudo'], x=252, y=10, w=25)
        
    pdf.set_xy(0, 15)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(297, 10, clean_txt(jugador_nombre), ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(297, 6, clean_txt(jugador_info), ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    
    pdf.ln(10)
    
    # --- KPIs PESAJE ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(297, 8, clean_txt(f"Pesaje ({fecha_pesaje})"), ln=True, align='C')
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(120, 120, 120)
    
    w_pesaje = 35
    offset_pesaje = (297 - (w_pesaje * 4)) / 2
    pdf.set_x(offset_pesaje)
    for title in ["Peso", "% Graso (Yuhasz)", "Masa Magra", "Sumatorio Pliegues"]:
        pdf.cell(w_pesaje, 5, clean_txt(title), align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(offset_pesaje)
    for key in ['Peso', 'Grasa', 'Magra', 'Pliegues']:
        pdf.cell(w_pesaje, 8, clean_txt(kpis_pesaje.get(key, '-')), align='C')
    pdf.ln(8)
    
    # --- KPIs PERÍMETROS ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(297, 8, clean_txt("Perimetros"), ln=True, align='C')
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(120, 120, 120)
    
    cols_per = ["Pecho", "Cintura", "Cadera", "Muslo", "Pierna", "Biceps"]
    w_per = 30
    offset_per = (297 - (w_per * 6)) / 2
    pdf.set_x(offset_per)
    for c in cols_per: 
        pdf.cell(w_per, 5, clean_txt(c), align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(offset_per)
    for c in cols_per: 
        pdf.cell(w_per, 8, clean_txt(kpis_perimetros.get(c, '-')), align='C')
    pdf.ln(8)
    
    # --- KPIs ASIMETRÍAS ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(297, 8, clean_txt("Asimetrias Perimetrales"), ln=True, align='C')
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(120, 120, 120)
    
    cols_asim = ["Muslo (D - I)", "Pierna (D - I)", "Biceps (D - I)"]
    w_asim = 50
    offset_asim = (297 - (w_asim * 3)) / 2
    pdf.set_x(offset_asim)
    for c in cols_asim: 
        pdf.cell(w_asim, 5, clean_txt(c), align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(offset_asim)
    for k in ['Muslo', 'Pierna', 'Biceps']:
        pdf.cell(w_asim, 8, clean_txt(kpis_asimetrias.get(k, '-')), align='C')
    pdf.ln(12)
    
    # --- TABLA HISTORIAL PÁGINA 1 ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(297, 8, clean_txt("Historial Completo"), ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 7)
    pdf.set_fill_color(*C_BG_TAB_H)
    pdf.set_text_color(255, 255, 255)
    
    # Anchos calculados al milímetro para que quede centrado
    widths = [17, 11, 13, 16, 16, 15, 15, 15, 16, 16, 19, 16, 16, 19, 16, 16, 19]
    cols = list(df_historial.columns)
    offset_x = (297 - sum(widths)) / 2
    
    pdf.set_x(offset_x)
    for i, col in enumerate(cols):
        clean_c = clean_txt(col.replace('Σ', 'Sum.'))
        pdf.cell(widths[i], 8, clean_c, border=1, fill=True, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', 7)
    pdf.set_text_color(0, 0, 0)
    for r_idx, row in df_historial.iterrows():
        pdf.set_x(offset_x)
        pdf.set_fill_color(*C_BG_TAB_R) if r_idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols):
            val = row.get(col, "-")
            
            # Lógica para forzar 1 decimal en el PDF sin tocar la fecha ni los guiones
            if pd.isna(val) or val == "-":
                val_str = "-"
            else:
                try:
                    val_str = f"{float(val):.1f}"
                except ValueError:
                    val_str = str(val)
                    
            pdf.cell(widths[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()

    # --- GRÁFICOS PÁGINA 2 (TODOS EN UNA HOJA) ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(297, 10, clean_txt("Evolucion Historica: Peso, % Graso y Perimetros"), ln=True, align='C')
    
    w_chart = 135
    h_chart = 55
    offset_c1 = (297 - (w_chart * 2)) / 3  # Espaciado dinámico para centrar 2 columnas
    x1 = offset_c1
    x2 = offset_c1 * 2 + w_chart
    
    y_row1 = 25
    y_row2 = 85
    y_row3 = 145
    
    if 'peso' in img_paths: pdf.image(img_paths['peso'], x=x1, y=y_row1, w=w_chart, h=h_chart)
    if 'grasa' in img_paths: pdf.image(img_paths['grasa'], x=x2, y=y_row1, w=w_chart, h=h_chart)
    
    if 'per1' in img_paths: pdf.image(img_paths['per1'], x=x1, y=y_row2, w=w_chart, h=h_chart)
    if 'per2' in img_paths: pdf.image(img_paths['per2'], x=x2, y=y_row2, w=w_chart, h=h_chart)
    
    if 'per3' in img_paths: pdf.image(img_paths['per3'], x=x1, y=y_row3, w=w_chart, h=h_chart)
    if 'per4' in img_paths: pdf.image(img_paths['per4'], x=x2, y=y_row3, w=w_chart, h=h_chart)
    
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)
        
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)
