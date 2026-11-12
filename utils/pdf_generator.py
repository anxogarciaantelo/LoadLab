import os
import tempfile
import base64
from fpdf import FPDF
import pandas as pd
from datetime import datetime
import re

def generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, dict_figs, escudo_b64=None):
    pdf = FPDF(orientation='L', unit='mm', format='A4') 
    pdf.set_auto_page_break(auto=True, margin=15)

    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()

    # PALETA DE COLORES ÉLITE
    C_DARK = (11, 14, 20)
    C_GOLD = (197, 160, 89)
    C_RED = (239, 68, 68)
    C_GREEN = (16, 185, 129)
    C_GRAY = (148, 163, 184)
    C_TAB_H = (17, 19, 24)
    C_TAB_R1 = (255, 255, 255)
    C_TAB_R2 = (248, 250, 252)

    img_paths = {}
    if escudo_b64:
        tmp_esc = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        if str(escudo_b64).startswith("http"):
            import requests
            r = requests.get(escudo_b64)
            tmp_esc.write(r.content)
        else:
            tmp_esc.write(base64.b64decode(escudo_b64.split(",")[1] if "," in escudo_b64 else escudo_b64))
        tmp_esc.close()
        img_paths['escudo'] = tmp_esc.name

    # --- INYECTOR DE FORMATO PARA PDF (Fuerza color negro y previene cortes) ---
    def adaptar_grafico_para_pdf(fig, title_text):
        if fig is None: return None
        fig.update_layout(
            paper_bgcolor="white", 
            plot_bgcolor="white", 
            font=dict(color="black", family="Arial", size=12),
            title=dict(text=title_text, font=dict(color="black", size=18, family="Arial"), x=0.5, xanchor="center"),
            xaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0", tickangle=-45, automargin=True),
            yaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(font=dict(color="black")),
            margin=dict(b=130, t=60, l=40, r=40) # Margen inferior gigante para nombres largos
        )
        if hasattr(fig.layout, 'polar'):
            fig.update_layout(polar=dict(angularaxis=dict(tickfont=dict(color="black")), radialaxis=dict(tickfont=dict(color="black"))))
        return fig

    for name, fig in dict_figs.items():
        if fig is not None:
            fig = adaptar_grafico_para_pdf(fig, name)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=800, height=530, format="jpg")
            img_paths[name] = tmp.name

    def draw_header(title, subtitle):
        pdf.set_fill_color(*C_DARK)
        pdf.rect(0, 0, 297, 24, 'F')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(0, 24, 297, 1, 'F')
        
        if 'escudo' in img_paths:
            pdf.image(img_paths['escudo'], x=12, y=3, w=18)
            
        pdf.set_xy(35, 5)
        pdf.set_font("Arial", 'B', 15)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(200, 7, clean_txt(title.upper()), ln=1)
        
        pdf.set_xy(35, 13)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(*C_GOLD)
        pdf.cell(200, 6, clean_txt(subtitle.upper()), ln=1)
        pdf.set_y(32)

    def draw_kpi(x, y, w, h, title, val, subtitle="", val_color=C_DARK):
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, w, h, 'DF')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(x, y, w, 2, 'F')
        
        pdf.set_xy(x+3, y+4)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(w-6, 4, clean_txt(title.upper()), align='C')
        
        pdf.set_xy(x+3, y+9)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(*val_color)
        pdf.cell(w-6, 7, clean_txt(str(val)), align='C')
        
        if subtitle:
            pdf.set_xy(x+3, y+16)
            pdf.set_font("Arial", 'B', 7)
            pdf.set_text_color(*C_GOLD)
            pdf.cell(w-6, 4, clean_txt(subtitle), align='C')

    def draw_section_title(txt, y):
        pdf.set_xy(10, y)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(*C_DARK)
        pdf.cell(200, 8, clean_txt(txt), ln=1)
        pdf.set_draw_color(*C_GOLD)
        pdf.line(10, y+8, 287, y+8)
        pdf.set_y(y+12)

    # --- PARSEO INTELIGENTE DE TÍTULOS ---
    try:
        fecha_f = datetime.strptime(sesion['fecha'], "%Y-%m-%d").strftime("%d-%m-%Y")
    except:
        fecha_f = sesion['fecha']
        
    nom_dyn = sesion.get("nombre_dinamico", "")
    num = ''.join(filter(str.isdigit, nom_dyn)) if nom_dyn else "X"
    
    if "Partido" in sesion.get("tipo", ""):
        rival = sesion.get("rival", "Rival")
        pref = "J" if "Oficial" in sesion.get("tipo", "") else "A"
        subtitle = f"{pref}{num} vs {rival} | {fecha_f}"
    else:
        md = sesion.get("descripcion", "TD")
        subtitle = f"S{num} | {md} | {fecha_f}"

    es_partido_pdf = "Partido" in sesion.get("tipo", "")
    df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0]

    # PAGE 1
    pdf.add_page()
    draw_header("INFORME DE SESIÓN DIARIA", subtitle)
    
    tqr_m = df_para_medias['TQR'].mean() if not df_para_medias.empty and pd.notna(df_para_medias['TQR'].mean()) else 0
    well_m = df_para_medias['WELLNESS'].mean() if not df_para_medias.empty and pd.notna(df_para_medias['WELLNESS'].mean()) else 0
    rpe_m = df_para_medias['RPE'].mean() if not df_para_medias.empty and pd.notna(df_para_medias['RPE'].mean()) else 0
    
    if es_partido_pdf:
        min_tot_ci = df_para_medias[df_para_medias['MIN'] > 0]['MIN'].sum() if not df_para_medias.empty else 0
        carga_m = (df_para_medias['CARGA'].sum() / min_tot_ci) * 90.0 if min_tot_ci > 0 else 0
        min_m = 90.0 if min_tot_ci > 0 else 0
    else:
        carga_m = df_para_medias['CARGA'].mean() if not df_para_medias.empty and pd.notna(df_para_medias['CARGA'].mean()) else 0
        min_m = df_para_medias['MIN'].mean() if not df_para_medias.empty and pd.notna(df_para_medias['MIN'].mean()) else 0

    draw_section_title("1. BIENESTAR Y CARGA INTERNA", pdf.get_y())
    
    y_kpi = pdf.get_y()
    w_kpi = 277 / 5
    draw_kpi(10, y_kpi, w_kpi-2, 22, "TQR Medio", f"{tqr_m:.1f} / 10")
    draw_kpi(10 + w_kpi, y_kpi, w_kpi-2, 22, "Wellness Medio", f"{well_m:.1f} pts")
    draw_kpi(10 + w_kpi*2, y_kpi, w_kpi-2, 22, "Minutos Ref." if es_partido_pdf else "Minutos Sesión", f"{min_m:.0f}'")
    draw_kpi(10 + w_kpi*3, y_kpi, w_kpi-2, 22, "RPE Medio", f"{rpe_m:.1f} / 10")
    draw_kpi(10 + w_kpi*4, y_kpi, w_kpi-2, 22, "Carga Media (90')" if es_partido_pdf else "Carga Media", f"{carga_m:.0f} UA")
    
    y_img = pdf.get_y() + 26
    w_img_3 = 277 / 3
    if "Desglose de Wellness" in img_paths: pdf.image(img_paths["Desglose de Wellness"], x=10, y=y_img, w=w_img_3)
    if "Calidad de Recuperación (TQR)" in img_paths: pdf.image(img_paths["Calidad de Recuperación (TQR)"], x=10 + w_img_3, y=y_img, w=w_img_3)
    if "Carga de Sesión" in img_paths: pdf.image(img_paths["Carga de Sesión"], x=10 + w_img_3*2, y=y_img, w=w_img_3)

    # PAGE 2
    pdf.add_page()
    draw_header("INFORME DE SESIÓN DIARIA", subtitle)
    draw_section_title("2. CARGA EXTERNA (GPS)", pdf.get_y())
    
    if es_partido_pdf and not df_para_medias_gps.empty:
        import numpy as np
        min_ef_gps = np.where(df_para_medias_gps.get('MIN_GPS', df_para_medias_gps['MIN']) > 0, df_para_medias_gps.get('MIN_GPS', df_para_medias_gps['MIN']), df_para_medias_gps['MIN'])
        min_tot_gps = min_ef_gps.sum()
        dis_m = (df_para_medias_gps['DIS'].sum() / min_tot_gps) * 90.0 if min_tot_gps > 0 else 0
        hsr_m = (df_para_medias_gps['DIS AI'].sum() / min_tot_gps) * 90.0 if min_tot_gps > 0 else 0
        spr_m = (df_para_medias_gps['Nº SPR'].sum() / min_tot_gps) * 90.0 if min_tot_gps > 0 else 0
        acc_m = (df_para_medias_gps['ACC'].sum() / min_tot_gps) * 90.0 if min_tot_gps > 0 else 0
        dcc_m = (df_para_medias_gps['DCC'].sum() / min_tot_gps) * 90.0 if min_tot_gps > 0 else 0
    else:
        dis_m = df_para_medias_gps['DIS'].mean() if not df_para_medias_gps.empty else 0
        hsr_m = df_para_medias_gps['DIS AI'].mean() if not df_para_medias_gps.empty else 0
        spr_m = df_para_medias_gps['Nº SPR'].mean() if not df_para_medias_gps.empty else 0
        acc_m = df_para_medias_gps['ACC'].mean() if not df_para_medias_gps.empty else 0
        dcc_m = df_para_medias_gps['DCC'].mean() if not df_para_medias_gps.empty else 0
    
    y_kpi = pdf.get_y()
    w_kpi = 277 / 5
    draw_kpi(10, y_kpi, w_kpi-2, 22, "Distancia", f"{dis_m:.2f} km")
    draw_kpi(10 + w_kpi, y_kpi, w_kpi-2, 22, "HSR (>21 km/h)", f"{hsr_m:.0f} m")
    draw_kpi(10 + w_kpi*2, y_kpi, w_kpi-2, 22, "Sprints (>24 km/h)", f"{spr_m:.1f}")
    draw_kpi(10 + w_kpi*3, y_kpi, w_kpi-2, 22, "ACC (>3 m/s²)", f"{acc_m:.0f}")
    draw_kpi(10 + w_kpi*4, y_kpi, w_kpi-2, 22, "DCC (>3 m/s²)", f"{dcc_m:.0f}")
    
    y_img = pdf.get_y() + 26
    if "Huella Dactilar" in img_paths: pdf.image(img_paths["Huella Dactilar"], x=10, y=y_img, w=w_img_3)
    if "Volumen vs Intensidad" in img_paths: pdf.image(img_paths["Volumen vs Intensidad"], x=10 + w_img_3, y=y_img, w=w_img_3)
    if "ACC vs DCC" in img_paths: pdf.image(img_paths["ACC vs DCC"], x=10 + w_img_3*2, y=y_img, w=w_img_3)

    # PAGE 3
    pdf.add_page()
    draw_header("INFORME DE SESIÓN DIARIA", subtitle)
    draw_section_title("3. TABLA MAESTRA DE RENDIMIENTO INDIVIDUAL", pdf.get_y())
    
    if 'HID >21' not in df_graficos.columns:
        df_graficos['HID >21'] = df_graficos.get('DIS AI', 0.0)

    pdf.set_font("Arial", 'B', 7)
    pdf.set_fill_color(*C_TAB_H)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(255, 255, 255)
    
    cols_all = ['JUGADOR', 'POS', 'MIN', 'RPE', 'CARGA', 'TQR', 'WELLNESS', 'A/C INT', 'DIS', 'HSR >21', 'SPR >24', 'ACC', 'DCC', 'VMAX']
    widths_all = [35, 12, 12, 12, 15, 15, 20, 20, 15, 18, 18, 15, 15, 15]
    
    offset_x = (297 - sum(widths_all)) / 2
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_all):
        pdf.cell(widths_all[i], 8, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 7)
    pdf.set_draw_color(226, 232, 240)
    row_count = 0
    for _, row in df_graficos.iterrows():
        pdf.set_x(offset_x)
        if row_count % 2 == 0:
            pdf.set_fill_color(*C_TAB_R2)
        else:
            pdf.set_fill_color(*C_TAB_R1)
            
        vals = [
            str(row.get('JUGADOR', ''))[:20],
            str(row.get('POS', '')),
            f"{row.get('MIN', 0):.0f}",
            f"{row.get('RPE', 0):.1f}",
            f"{row.get('CARGA', 0):.0f}",
            f"{row.get('TQR', 0):.1f}",
            f"{row.get('WELLNESS', 0):.1f}",
            f"{row.get('RATIO A/C', 0):.2f}",
            f"{row.get('DIS', 0):.2f}",
            f"{row.get('HID >21', 0):.0f}",
            f"{row.get('Nº SPR', 0):.0f}",
            f"{row.get('ACC', 0):.0f}",
            f"{row.get('DCC', 0):.0f}",
            f"{row.get('VMAX', 0):.1f}"
        ]
        
        for i, val in enumerate(vals):
            if cols_all[i] == 'A/C INT':
                v = float(val) if val else 0
                if v >= 1.5: pdf.set_text_color(*C_RED); pdf.set_font("Arial", 'B', 7)
                elif v <= 0.8: pdf.set_text_color(245, 158, 11); pdf.set_font("Arial", 'B', 7)
                else: pdf.set_text_color(*C_GREEN); pdf.set_font("Arial", 'B', 7)
            else:
                pdf.set_text_color(*C_DARK)
                pdf.set_font("Arial", '', 7)
                
            align = 'L' if i == 0 else 'C'
            pdf.cell(widths_all[i], 6, clean_txt(val), border='B', align=align, fill=True)
        pdf.ln()
        row_count += 1

    # PAGE 4
    if alertas_multi or alertas_rec or alertas_car:
        pdf.add_page()
        draw_header("INFORME DE SESIÓN DIARIA", subtitle)
        draw_section_title("4. ALERTAS DE RENDIMIENTO Y RIESGO", pdf.get_y())
        
        def print_alert_group(title, alerts, color, icon_text):
            if not alerts: return
            pdf.set_fill_color(*color)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(277, 8, clean_txt(f" {icon_text} {title.upper()}"), fill=True, ln=1)
            
            pdf.set_text_color(*C_DARK)
            pdf.set_font("Arial", '', 9)
            pdf.ln(2)
            for al in alerts:
                pdf.set_x(12)
                pdf.multi_cell(273, 6, clean_txt(f"• {al.replace('**', '')}"))
            pdf.ln(6)

        print_alert_group("Riesgo Multifactorial (2 o más alertas simultáneas)", alertas_multi, C_RED, "!!")
        print_alert_group("Alertas de Recuperación", alertas_rec, (245, 158, 11), "!")
        print_alert_group("Alertas de Carga Extrema / Desentrenamiento", alertas_car, C_GOLD, "!")

    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)


def generar_pdf_microciclo(nombre_micro, df_diario, df_indiv, kpis_globales, dict_figs, escudo_b64=None):
    import os
    import tempfile
    import base64
    from fpdf import FPDF
    import pandas as pd
    import re
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    C_DARK = (11, 14, 20)
    C_GOLD = (197, 160, 89)
    C_RED = (239, 68, 68)
    C_GREEN = (16, 185, 129)
    C_GRAY = (148, 163, 184)
    C_TAB_H = (17, 19, 24)
    C_TAB_R1 = (255, 255, 255)
    C_TAB_R2 = (248, 250, 252)

    img_paths = {}
    if escudo_b64:
        tmp_esc = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        if str(escudo_b64).startswith("http"):
            import requests
            r = requests.get(escudo_b64)
            tmp_esc.write(r.content)
        else:
            tmp_esc.write(base64.b64decode(escudo_b64.split(",")[1] if "," in escudo_b64 else escudo_b64))
        tmp_esc.close()
        img_paths['escudo'] = tmp_esc.name

    def adaptar_grafico_para_pdf(fig, title_text):
        if fig is None: return None
        fig.update_layout(
            paper_bgcolor="white", 
            plot_bgcolor="white", 
            font=dict(color="black", family="Arial", size=12),
            title=dict(text=title_text, font=dict(color="black", size=18, family="Arial"), x=0.5, xanchor="center"),
            xaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0", tickangle=-45, automargin=True),
            yaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(font=dict(color="black")),
            margin=dict(b=130, t=60, l=40, r=40)
        )
        if hasattr(fig.layout, 'polar'):
            fig.update_layout(polar=dict(angularaxis=dict(tickfont=dict(color="black")), radialaxis=dict(tickfont=dict(color="black"))))
        return fig

    for name, fig in dict_figs.items():
        if fig is not None:
            fig = adaptar_grafico_para_pdf(fig, name)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=800, height=530, format="jpg")
            img_paths[name] = tmp.name

    def draw_header(title, subtitle):
        pdf.set_fill_color(*C_DARK)
        pdf.rect(0, 0, 297, 24, 'F')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(0, 24, 297, 1, 'F')
        if 'escudo' in img_paths:
            pdf.image(img_paths['escudo'], x=12, y=3, w=18)
        pdf.set_xy(35, 5)
        pdf.set_font("Arial", 'B', 15)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(200, 7, clean_txt(title.upper()), ln=1)
        pdf.set_xy(35, 13)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(*C_GOLD)
        pdf.cell(200, 6, clean_txt(subtitle.upper()), ln=1)
        pdf.set_y(32)

    def draw_kpi(x, y, w, h, title, val):
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, w, h, 'DF')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(x, y, w, 2, 'F')
        pdf.set_xy(x+3, y+4)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(w-6, 4, clean_txt(title.upper()), align='C')
        pdf.set_xy(x+3, y+9)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(*C_DARK)
        pdf.cell(w-6, 7, clean_txt(str(val)), align='C')

    def draw_section_title(txt, y):
        pdf.set_xy(10, y)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(*C_DARK)
        pdf.cell(200, 8, clean_txt(txt), ln=1)
        pdf.set_draw_color(*C_GOLD)
        pdf.line(10, y+8, 287, y+8)
        pdf.set_y(y+12)

    match = re.search(r'Microciclo (\d+)', nombre_micro)
    num_m = match.group(1) if match else "X"
    if "|" in nombre_micro:
        rango = nombre_micro.split("|")[1].strip().replace("Semana del ", "")
        subtitle = f"M{num_m} | {rango}"
    else:
        subtitle = f"M{num_m}"

    pdf.add_page()
    draw_header("INFORME DE MICROCICLO", subtitle)
    draw_section_title("1. RESUMEN ACUMULADO DEL MICROCICLO", pdf.get_y())
    
    y_kpi = pdf.get_y()
    w_kpi = 277 / 5
    draw_kpi(10, y_kpi, w_kpi-2, 18, "Wellness Medio", f"{kpis_globales.get('Wellness', 0):.1f}")
    draw_kpi(10 + w_kpi, y_kpi, w_kpi-2, 18, "TQR Medio", f"{kpis_globales.get('TQR', 0):.1f}")
    draw_kpi(10 + w_kpi*2, y_kpi, w_kpi-2, 18, "RPE Medio", f"{kpis_globales.get('RPE', 0):.1f}")
    draw_kpi(10 + w_kpi*3, y_kpi, w_kpi-2, 18, "Minutos Totales", f"{kpis_globales.get('Minutos', 0):.0f}'")
    draw_kpi(10 + w_kpi*4, y_kpi, w_kpi-2, 18, "Carga Total", f"{kpis_globales.get('Carga', 0):.0f} UA")
    
    y_kpi2 = y_kpi + 22
    draw_kpi(10, y_kpi2, w_kpi-2, 18, "Distancia", f"{kpis_globales.get('DIS', 0):.2f} km")
    draw_kpi(10 + w_kpi, y_kpi2, w_kpi-2, 18, "HSR (>21)", f"{kpis_globales.get('HSR', 0):.0f} m")
    draw_kpi(10 + w_kpi*2, y_kpi2, w_kpi-2, 18, "Sprints (>24)", f"{kpis_globales.get('SPR', 0):.1f}")
    draw_kpi(10 + w_kpi*3, y_kpi2, w_kpi-2, 18, "ACC (>3)", f"{kpis_globales.get('ACC', 0):.0f}")
    draw_kpi(10 + w_kpi*4, y_kpi2, w_kpi-2, 18, "DCC (>3)", f"{kpis_globales.get('DCC', 0):.0f}")
    
    pdf.set_y(y_kpi2 + 24)
    draw_section_title("2. RESUMEN DIARIO", pdf.get_y())
    
    cols_dia = ['DIA', 'WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_dia = [25, 25, 20, 20, 20, 25, 25, 25, 25, 25, 25] 
    offset_x = (297 - sum(widths_dia)) / 2
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_TAB_H)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_dia):
        pdf.cell(widths_dia[i], 8, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    pdf.set_draw_color(226, 232, 240)
    for r_idx, row in df_diario.iterrows():
        pdf.set_x(offset_x)
        pdf.set_fill_color(*C_TAB_R2) if r_idx % 2 == 0 else pdf.set_fill_color(*C_TAB_R1)
        pdf.set_text_color(*C_DARK)
        for i, col in enumerate(cols_dia):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            pdf.cell(widths_dia[i], 6, clean_txt(val_str), border='B', align='C', fill=True)
        pdf.ln()

    w_img3 = 277 / 3

    pdf.add_page()
    draw_header("INFORME DE MICROCICLO", subtitle)
    draw_section_title("3. BIENESTAR Y CARGA INTERNA DIARIA", pdf.get_y())
    y_img = pdf.get_y()
    if "TQR" in img_paths: pdf.image(img_paths["TQR"], x=10, y=y_img, w=135)
    if "Wellness" in img_paths: pdf.image(img_paths["Wellness"], x=150, y=y_img, w=135)
    
    y_img2 = y_img + 80
    if "Minutos" in img_paths: pdf.image(img_paths["Minutos"], x=10, y=y_img2, w=w_img3)
    if "RPE" in img_paths: pdf.image(img_paths["RPE"], x=10 + w_img3, y=y_img2, w=w_img3)
    if "Carga" in img_paths: pdf.image(img_paths["Carga"], x=10 + w_img3*2, y=y_img2, w=w_img3)

    pdf.add_page()
    draw_header("INFORME DE MICROCICLO", subtitle)
    draw_section_title("4. CARGA EXTERNA DIARIA (GPS)", pdf.get_y())
    y_img = pdf.get_y()
    if "ACC_DCC" in img_paths: pdf.image(img_paths["ACC_DCC"], x=10, y=y_img, w=w_img3)
    if "DIS" in img_paths: pdf.image(img_paths["DIS"], x=10 + w_img3, y=y_img, w=w_img3)
    if "DIS_AI" in img_paths: pdf.image(img_paths["DIS_AI"], x=10 + w_img3*2, y=y_img, w=w_img3)

    pdf.add_page()
    draw_header("INFORME DE MICROCICLO", subtitle)
    draw_section_title("5. RESUMEN SEMANAL POR JUGADOR", pdf.get_y())
    
    cols_indiv = ['JUGADOR', 'POS', 'MIN', 'TQR', 'WELLNESS', 'RPE', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_indiv = [40, 15, 15, 15, 22, 15, 20, 20, 20, 20, 20, 20] 
    offset_x_indiv = (297 - sum(widths_indiv)) / 2
    
    pdf.set_font("Arial", 'B', 7)
    pdf.set_fill_color(*C_TAB_H)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(offset_x_indiv)
    for i, col in enumerate(cols_indiv):
        pdf.cell(widths_indiv[i], 8, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 7)
    pdf.set_draw_color(226, 232, 240)
    for r_idx, row in df_indiv.iterrows():
        pdf.set_x(offset_x_indiv)
        pdf.set_fill_color(*C_TAB_R2) if r_idx % 2 == 0 else pdf.set_fill_color(*C_TAB_R1)
        pdf.set_text_color(*C_DARK)
            
        for i, col in enumerate(cols_indiv):
            val = row.get(col, 0)
            if isinstance(val, float):
                val_str = f"{val:.1f}" if col in ['TQR', 'WELLNESS', 'RPE', 'Nº SPR', 'ACC', 'DCC'] else f"{val:.2f}" if col in ['DIS', 'DIS AI'] else f"{val:.0f}"
            else:
                val_str = str(val)[:20]
            align = 'L' if i == 0 else 'C'
            pdf.cell(widths_indiv[i], 6, clean_txt(val_str), border='B', align=align, fill=True)
        pdf.ln()

    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

def generar_pdf_antropometria_jugador(jugador_nombre, jugador_info, fecha_pesaje, kpis_pesaje, kpis_perimetros, kpis_asimetrias, dict_figs, df_historial, escudo_b64, foto_b64):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    # PALETA DE COLORES ÉLITE (Unificada con Sesión y Microciclo)
    C_DARK = (11, 14, 20)
    C_GOLD = (197, 160, 89)
    C_RED = (239, 68, 68)
    C_GREEN = (16, 185, 129)
    C_GRAY = (148, 163, 184)
    C_TAB_H = (17, 19, 24)
    C_TAB_R1 = (255, 255, 255)
    C_TAB_R2 = (248, 250, 252)
    
    img_paths = {}
    
    if escudo_b64:
        try:
            tmp_esc = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            if str(escudo_b64).startswith("http"):
                import requests
                r = requests.get(escudo_b64)
                tmp_esc.write(r.content)
            else:
                tmp_esc.write(base64.b64decode(escudo_b64.split(",")[1] if "," in str(escudo_b64) else escudo_b64))
            tmp_esc.close()
            img_paths['escudo'] = tmp_esc.name
        except Exception:
            pass
        
    if foto_b64:
        try:
            tmp_foto = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            if str(foto_b64).startswith("http"):
                import requests
                r = requests.get(foto_b64)
                tmp_foto.write(r.content)
            else:
                tmp_foto.write(base64.b64decode(foto_b64.split(",")[1] if "," in str(foto_b64) else foto_b64))
            tmp_foto.close()
            img_paths['foto'] = tmp_foto.name
        except Exception:
            pass

    titulos_graficos = {
        'peso': 'Evolución Peso (kg)',
        'grasa': 'Evolución % Graso (Faulkner)',
        'per1': 'Perímetros: Pecho y Bíceps',
        'per2': 'Perímetros: Cintura y Cadera',
        'per3': 'Perímetros: Muslo (D/I)',
        'per4': 'Perímetros: Pierna (D/I)',
        'quadrante': 'Posición en el Cuadrante Élite Corporal (FFMI vs % Grasa)'
    }

    def adaptar_grafico_para_pdf(fig, title_text):
        if fig is None: return None
        fig.update_layout(
            paper_bgcolor="white", 
            plot_bgcolor="white", 
            font=dict(color="black", family="Arial", size=12),
            title=dict(text=title_text, font=dict(color="black", size=17, family="Arial"), x=0.5, xanchor="center"),
            xaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0", tickangle=-35, automargin=True),
            yaxis=dict(tickfont=dict(color="black", size=11), title_font=dict(color="black", size=12), showgrid=True, gridcolor="#e2e8f0", automargin=True),
            legend=dict(font=dict(color="black", size=10), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(b=95, t=65, l=55, r=30)
        )
        return fig
        
    for name, fig in dict_figs.items():
        if fig is not None:
            fig_copy = go.Figure(fig) if 'go' in globals() else fig
            fig_copy = adaptar_grafico_para_pdf(fig_copy, titulos_graficos.get(name, name))
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig_copy.write_image(tmp.name, engine="kaleido", width=800, height=530, format="jpg")
            img_paths[name] = tmp.name

    def draw_header(title, subtitle):
        pdf.set_fill_color(*C_DARK)
        pdf.rect(0, 0, 297, 24, 'F')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(0, 24, 297, 1, 'F')
        
        if 'escudo' in img_paths:
            pdf.image(img_paths['escudo'], x=12, y=3, w=18)
        if 'foto' in img_paths:
            pdf.image(img_paths['foto'], x=265, y=3, w=18)
            
        pdf.set_xy(35, 5)
        pdf.set_font("Arial", 'B', 15)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(200, 7, clean_txt(title.upper()), ln=1)
        
        pdf.set_xy(35, 13)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(*C_GOLD)
        pdf.cell(200, 6, clean_txt(subtitle.upper()), ln=1)
        pdf.set_y(32)

    def draw_kpi(x, y, w, h, title, val, subtitle="", val_color=C_DARK):
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, w, h, 'DF')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(x, y, w, 2, 'F')
        
        pdf.set_xy(x+2, y+3.5)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(w-4, 4, clean_txt(title.upper()), align='C')
        
        pdf.set_xy(x+2, y+8.5)
        pdf.set_font("Arial", 'B', 13)
        pdf.set_text_color(*val_color)
        pdf.cell(w-4, 6, clean_txt(str(val)), align='C')
        
        if subtitle:
            pdf.set_xy(x+2, y+15.5)
            pdf.set_font("Arial", 'B', 6.5)
            pdf.set_text_color(*C_GOLD)
            pdf.cell(w-4, 4, clean_txt(subtitle), align='C')

    def draw_section_title(txt, y):
        pdf.set_xy(10, y)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(*C_DARK)
        pdf.cell(200, 8, clean_txt(txt), ln=1)
        pdf.set_draw_color(*C_GOLD)
        pdf.line(10, y+8, 287, y+8)
        pdf.set_y(y+12)

    subtitle = f"{jugador_nombre} | {jugador_info} | ÚLTIMO CONTROL: {fecha_pesaje}"

    # ==========================================
    # PÁGINA 1: KPIs Y TABLA DE HISTORIAL
    # ==========================================
    pdf.add_page()
    draw_header("INFORME DE COMPOSICIÓN CORPORAL Y ANTROPOMETRÍA", subtitle)
    
    # 1. KPIs PESAJE
    draw_section_title(f"1. COMPOSICIÓN CORPORAL ({fecha_pesaje})", pdf.get_y())
    y_kpi1 = pdf.get_y()
    w_kpi4 = 277 / 4
    draw_kpi(10, y_kpi1, w_kpi4-2, 20, "Peso Corporal", kpis_pesaje.get('Peso', '-'))
    draw_kpi(10 + w_kpi4, y_kpi1, w_kpi4-2, 20, "% Graso (Faulkner)", kpis_pesaje.get('Grasa', '-'))
    draw_kpi(10 + w_kpi4*2, y_kpi1, w_kpi4-2, 20, "Masa Magra", kpis_pesaje.get('Magra', '-'))
    draw_kpi(10 + w_kpi4*3, y_kpi1, w_kpi4-2, 20, "Sumatorio 4 Pliegues", kpis_pesaje.get('Pliegues', '-'))
    
    # 2. KPIs PERÍMETROS Y ASIMETRÍAS
    pdf.set_y(y_kpi1 + 24)
    draw_section_title("2. PERÍMETROS CORPORALES Y ASIMETRÍAS BILATERALES", pdf.get_y())
    y_kpi2 = pdf.get_y()
    w_kpi6 = 277 / 6
    draw_kpi(10, y_kpi2, w_kpi6-2, 22, "Pecho", kpis_perimetros.get('Pecho', '-'))
    draw_kpi(10 + w_kpi6, y_kpi2, w_kpi6-2, 22, "Cintura", kpis_perimetros.get('Cintura', '-'))
    draw_kpi(10 + w_kpi6*2, y_kpi2, w_kpi6-2, 22, "Cadera", kpis_perimetros.get('Cadera', '-'))
    draw_kpi(10 + w_kpi6*3, y_kpi2, w_kpi6-2, 22, "Muslo (Media)", kpis_perimetros.get('Muslo', '-'), f"Asim D-I: {kpis_asimetrias.get('Muslo', '-')}")
    draw_kpi(10 + w_kpi6*4, y_kpi2, w_kpi6-2, 22, "Pierna (Media)", kpis_perimetros.get('Pierna', '-'), f"Asim D-I: {kpis_asimetrias.get('Pierna', '-')}")
    draw_kpi(10 + w_kpi6*5, y_kpi2, w_kpi6-2, 22, "Bíceps (Media)", kpis_perimetros.get('Biceps', '-'), f"Asim D-I: {kpis_asimetrias.get('Biceps', '-')}")

    # 3. TABLA HISTORIAL COMPLETO
    pdf.set_y(y_kpi2 + 26)
    draw_section_title("3. HISTORIAL COMPLETO DE MEDICIONES", pdf.get_y())
    
    widths = [18, 13, 14, 16, 16, 15, 15, 15, 16, 16, 18, 16, 16, 18, 16, 16, 18]
    cols = list(df_historial.columns)
    offset_x = (297 - sum(widths)) / 2
    
    pdf.set_font("Arial", 'B', 6.5)
    pdf.set_fill_color(*C_TAB_H)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(255, 255, 255)
    
    pdf.set_x(offset_x)
    for i, col in enumerate(cols):
        clean_c = clean_txt(col.replace('Σ', 'Sum.').replace('Asimetría ', 'Asim. '))
        pdf.cell(widths[i], 8, clean_c, border=1, fill=True, align='C')
    pdf.ln()
    
    pdf.set_draw_color(226, 232, 240)
    row_count = 0
    for _, row in df_historial.iterrows():
        pdf.set_x(offset_x)
        pdf.set_fill_color(*C_TAB_R2) if row_count % 2 == 0 else pdf.set_fill_color(*C_TAB_R1)
            
        for i, col in enumerate(cols):
            val = row.get(col, "-")
            es_asim = "Asimetría" in col
            
            if pd.isna(val) or val == "-" or str(val).strip() == "":
                val_str = "-"
                num_val = None
            else:
                try:
                    num_val = float(val)
                    val_str = f"{num_val:.1f}%" if es_asim else f"{num_val:.1f}"
                except ValueError:
                    num_val = None
                    val_str = str(val)
            
            if es_asim and num_val is not None:
                if num_val > 5.0:
                    pdf.set_text_color(*C_RED)
                    pdf.set_font("Arial", 'B', 7)
                elif num_val <= 2.0:
                    pdf.set_text_color(*C_GREEN)
                    pdf.set_font("Arial", 'B', 7)
                else:
                    pdf.set_text_color(245, 158, 11)
                    pdf.set_font("Arial", 'B', 7)
            else:
                pdf.set_text_color(*C_DARK)
                pdf.set_font("Arial", 'B' if i == 0 else '', 7)
                    
            pdf.cell(widths[i], 6, clean_txt(val_str), border='B', align='C', fill=True)
        pdf.ln()
        row_count += 1

    # ==========================================
    # PÁGINA 2: EVOLUCIÓN HISTÓRICA (GRID 3x2)
    # ==========================================
    pdf.add_page()
    draw_header("INFORME DE COMPOSICIÓN CORPORAL Y ANTROPOMETRÍA", subtitle)
    draw_section_title("4. EVOLUCIÓN MENSUAL: PESO, % GRASO Y PERÍMETROS", pdf.get_y())
    
    w_img_3 = 277 / 3
    y_row1 = pdf.get_y() + 2
    y_row2 = y_row1 + 68
    
    if 'peso' in img_paths: pdf.image(img_paths['peso'], x=10, y=y_row1, w=w_img_3)
    if 'grasa' in img_paths: pdf.image(img_paths['grasa'], x=10 + w_img_3, y=y_row1, w=w_img_3)
    if 'per1' in img_paths: pdf.image(img_paths['per1'], x=10 + w_img_3*2, y=y_row1, w=w_img_3)
    
    if 'per2' in img_paths: pdf.image(img_paths['per2'], x=10, y=y_row2, w=w_img_3)
    if 'per3' in img_paths: pdf.image(img_paths['per3'], x=10 + w_img_3, y=y_row2, w=w_img_3)
    if 'per4' in img_paths: pdf.image(img_paths['per4'], x=10 + w_img_3*2, y=y_row2, w=w_img_3)

    # ==========================================
    # PÁGINA 3: CUADRANTE ESTRUCTURAL (FFMI)
    # ==========================================
    if 'quadrante' in img_paths:
        pdf.add_page()
        draw_header("INFORME DE COMPOSICIÓN CORPORAL Y ANTROPOMETRÍA", subtitle)
        draw_section_title("5. EVALUACIÓN ESTRUCTURAL (CUADRANTE FFMI VS % GRASA)", pdf.get_y())
        
        w_quad = 165
        offset_quad = (297 - w_quad) / 2
        y_quad = pdf.get_y() + 2
        pdf.image(img_paths['quadrante'], x=offset_quad, y=y_quad, w=w_quad)
        
        y_box = y_quad + 114
        pdf.set_fill_color(*C_TAB_R2)
        pdf.set_draw_color(*C_GOLD)
        pdf.rect(25, y_box, 247, 16, 'DF')
        pdf.set_xy(30, y_box + 3)
        pdf.set_font("Arial", 'B', 8)
        pdf.set_text_color(*C_DARK)
        pdf.cell(237, 4, clean_txt("NOTA METODOLÓGICA: ZONA ÉLITE (7.5% - 10.0% GRASA | 20.0 - 23.0 FFMI)"), align='C', ln=1)
        pdf.set_x(30)
        pdf.set_font("Arial", '', 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(237, 5, clean_txt("El Índice de Masa Libre de Grasa (FFMI) relativiza el desarrollo muscular respecto a la estatura del futbolista, eliminando el sesgo del peso absoluto."), align='C')
        
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)
        
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

def generar_pdf_valoracion_jugador(jug_masivo, jug_datos, v_latest, v_ref, peso_act, img_paths, escudo_b64, cuadrante, v0, f0_kg_barra, f0_rel_N, r2, pauta_fv):
    from fpdf import FPDF
    import tempfile
    import os
    import base64

    def safe_float(val):
        try: return float(val) if val else 0.0
        except: return 0.0

    def calc_asimetria(der, izq):
        d, i = safe_float(der), safe_float(izq)
        if max(d, i) == 0: return 0.0
        return (abs(d - i) / max(d, i)) * 100

    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    def no_emo(t): return clean_txt(str(t)[2:].strip() if len(str(t))>2 and str(t)[0] in '🟢🟡🔴🏃⚖🚀' else str(t))
    
    def badge_asi_detallado(val, der, izq):
        if val < 10: return f"🟢 {val:.1f}% (Optimo)"
        else:
            pierna_debil = "Derecha" if safe_float(der) < safe_float(izq) else ("Izquierda" if safe_float(izq) < safe_float(der) else "Ninguna")
            if val <= 15: return f"🟡 {val:.1f}% (Precaucion | Debil: {pierna_debil})"
            else: return f"🔴 {val:.1f}% (Riesgo | Debil: {pierna_debil})"

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, clean_txt(jug_masivo.upper()), ln=False)
    
    if jug_datos and jug_datos.get("foto"):
        tmp_foto = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        fb64 = jug_datos["foto"]
        if str(fb64).startswith("http"):
            import requests
            r = requests.get(fb64)
            tmp_foto.write(r.content)
        else:
            tmp_foto.write(base64.b64decode(fb64.split(',')[1] if ',' in fb64 else fb64))
        tmp_foto.close()
        pdf.image(tmp_foto.name, x=260, y=8, w=22)
        os.unlink(tmp_foto.name)
    
    pdf.ln(12)
    
    def draw_card(pdf_obj, x, y, w, h, title, v_left, v_right=None, l_left="", l_right="", b_lbl="", b_val=""):
        pdf_obj.set_xy(x, y)
        pdf_obj.set_fill_color(255, 255, 255)
        pdf_obj.set_draw_color(220, 220, 220)
        pdf_obj.cell(w, h, "", border=1, fill=True)
        pdf_obj.set_xy(x+3, y+2)
        pdf_obj.set_font("Arial", 'B', 6)
        pdf_obj.set_text_color(80, 80, 80)
        pdf_obj.cell(w-6, 4, clean_txt(title.upper()), ln=0)
        pdf_obj.set_xy(x+3, y+8)
        if v_right is not None:
            pdf_obj.set_font("Arial", '', 7)
            pdf_obj.set_text_color(120, 120, 120)
            pdf_obj.cell(6, 6, clean_txt(l_left), ln=0)
            pdf_obj.set_font("Arial", 'B', 11)
            pdf_obj.set_text_color(220, 38, 38)
            pdf_obj.cell(w/2 - 12, 6, clean_txt(v_left), ln=0)
            pdf_obj.set_font("Arial", '', 7)
            pdf_obj.set_text_color(120, 120, 120)
            pdf_obj.cell(6, 6, clean_txt(l_right), ln=0)
            pdf_obj.set_font("Arial", 'B', 11)
            pdf_obj.set_text_color(220, 38, 38)
            pdf_obj.cell(w/2 - 12, 6, clean_txt(v_right), ln=0)
        else:
            pdf_obj.set_font("Arial", 'B', 12)
            pdf_obj.set_text_color(0, 0, 0)
            pdf_obj.cell(w-6, 6, clean_txt(v_left), ln=0)
        if b_lbl:
            pdf_obj.set_xy(x, y + h)
            pdf_obj.set_fill_color(240, 248, 255)
            pdf_obj.cell(w, 6, "", border=1, fill=True)
            pdf_obj.set_xy(x+3, y + h + 1)
            pdf_obj.set_font("Arial", 'B', 7)
            pdf_obj.set_text_color(30, 80, 140)
            lbl_w = pdf_obj.get_string_width(clean_txt(b_lbl)) + 1
            pdf_obj.cell(lbl_w, 4, clean_txt(b_lbl), ln=0)
            pdf_obj.set_font("Arial", '', 7)
            pdf_obj.set_text_color(80, 80, 80)
            pdf_obj.cell(10, 4, clean_txt(b_val), ln=0)

    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 8, "Movilidad (Grados)", ln=True)
    y_mov = pdf.get_y()
    w_3 = 89
    m_re_d, m_re_i = v_latest.get('mov_rot_ext_d',0), v_latest.get('mov_rot_ext_i',0)
    m_ri_d, m_ri_i = v_latest.get('mov_rot_int_d',0), v_latest.get('mov_rot_int_i',0)
    m_do_d, m_do_i = v_latest.get('mov_dorsi_d',0), v_latest.get('mov_dorsi_i',0)
    a_re, a_ri, a_do = calc_asimetria(m_re_d, m_re_i), calc_asimetria(m_ri_d, m_ri_i), calc_asimetria(m_do_d, m_do_i)
    draw_card(pdf, 10, y_mov, w_3, 16, "Rot. Ext. Cadera", str(m_re_d), str(m_re_i), "Der:", "Izq:", "Asimetria Rot. Ext:", no_emo(badge_asi_detallado(a_re, m_re_d, m_re_i)))
    draw_card(pdf, 10+w_3+5, y_mov, w_3, 16, "Rot. Int. Cadera", str(m_ri_d), str(m_ri_i), "Der:", "Izq:", "Asimetria Rot. Int:", no_emo(badge_asi_detallado(a_ri, m_ri_d, m_ri_i)))
    draw_card(pdf, 10+(w_3*2)+10, y_mov, w_3, 16, "Dorsiflexion Tobillo", str(m_do_d), str(m_do_i), "Der:", "Izq:", "Asimetria Dorsiflexion:", no_emo(badge_asi_detallado(a_do, m_do_d, m_do_i)))

    pdf.set_xy(10, y_mov + 28)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, "Salto y Perfil Vectorial", ln=True)
    y_salto = pdf.get_y()
    s_hb = safe_float(v_latest.get('sh_bi', v_latest.get('sj_bi', 0)))
    s_cb = safe_float(v_latest.get('cmj_bi', 0))
    s_cd, s_ci = v_latest.get('cmj_uni_d',0), v_latest.get('cmj_uni_i',0)
    s_hd, s_hi = v_latest.get('sh_d',0), v_latest.get('sh_i',0)
    a_cmj, a_sh = calc_asimetria(s_cd, s_ci), calc_asimetria(s_hd, s_hi)
    c_sum = s_cd + s_ci
    dbl = round(100*(s_cb/c_sum)-100, 1) if c_sum>0 else 0
    rv = round(s_hb/s_cb, 2) if s_cb>0 else 0
    w_4 = 65.5
    draw_card(pdf, 10, y_salto, w_4, 16, "Salto Horiz. Bilateral", f"{s_hb} cm", None, "", "", "Asimetria Vertical:", f"{a_cmj:.1f}%")
    draw_card(pdf, 10+w_4+5, y_salto, w_4, 16, "CMJ Bilateral", f"{s_cb} cm", None, "", "", "Asimetria Horizontal:", f"{a_sh:.1f}%")
    draw_card(pdf, 10+(w_4*2)+10, y_salto, w_4, 16, "CMJ Unilateral", f"{s_cd} cm", f"{s_ci} cm", "Der:", "Izq:", "Deficit Bilateral:", f"{dbl}%")
    draw_card(pdf, 10+(w_4*3)+15, y_salto, w_4, 16, "Salto Horiz. Unilateral", f"{s_hd} cm", f"{s_hi} cm", "Der:", "Izq:", "Ratio Vectores (H/V):", f"{rv}")

    pdf.set_xy(10, y_salto + 28)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, "Fuerza Maxima Isometrica", ln=True)
    y_iso = pdf.get_y()
    f_ed, f_ei = v_latest.get('iso_ext_d',0), v_latest.get('iso_ext_i',0)
    f_fd, f_fi = v_latest.get('iso_flx_d',0), v_latest.get('iso_flx_i',0)
    f_ad, f_ai = v_latest.get('iso_add_d',0), v_latest.get('iso_add_i',0)
    a_e, a_f, a_a = calc_asimetria(f_ed, f_ei), calc_asimetria(f_fd, f_fi), calc_asimetria(f_ad, f_ai)
    draw_card(pdf, 10, y_iso, w_3, 16, "Extension (Cuad)", f"{f_ed} N", f"{f_ei} N", "Der:", "Izq:", "Asim. Cuadriceps:", no_emo(badge_asi_detallado(a_e, f_ed, f_ei)))
    draw_card(pdf, 10+w_3+5, y_iso, w_3, 16, "Flexion (Isq)", f"{f_fd} N", f"{f_fi} N", "Der:", "Izq:", "Asim. Isquiosurales:", no_emo(badge_asi_detallado(a_f, f_fd, f_fi)))
    draw_card(pdf, 10+(w_3*2)+10, y_iso, w_3, 16, "Aduccion", f"{f_ad} N", f"{f_ai} N", "Der:", "Izq:", "Asim. Aduccion:", no_emo(badge_asi_detallado(a_a, f_ad, f_ai)))

    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, "Fuerza Maxima (Sentadilla)", ln=True)
    y_sq = pdf.get_y()
    rm_sq = safe_float(v_latest.get('rm_sq', v_latest.get('rm_sentadilla', 0)))
    rel_sq = rm_sq/peso_act if peso_act>0 else 0
    rfs = s_cb / rel_sq if rel_sq>0 else 0
    draw_card(pdf, 10, y_sq, w_3, 16, "1RM Sentadilla (VMP 0.3 M/S)", f"{rm_sq} kg")
    draw_card(pdf, 10+w_3+5, y_sq, w_3, 16, "Fuerza Relativa Sentadilla", f"{rel_sq:.2f}x Peso")
    draw_card(pdf, 10+(w_3*2)+10, y_sq, w_3, 16, "Ratio Fuerza-Salto", f"{rfs:.1f}")

    y_fv = y_sq + 20
    if 'fv' in img_paths: pdf.image(img_paths['fv'], x=5, y=y_fv, w=145)
    
    pdf.set_xy(150, y_fv+10)
    pdf.set_fill_color(240, 248, 255)
    pdf.cell(127, 45, "", border=1, fill=True)
    pdf.set_xy(155, y_fv+15)
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(30, 80, 140)
    pdf.cell(20, 6, "Diagnostico:", ln=0)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 6, clean_txt(no_emo(cuadrante)), ln=1)
    
    pdf.set_x(155)
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(30, 80, 140)
    pdf.cell(6, 6, "V0:", ln=0)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(18, 6, f"{v0:.2f} m/s |", ln=0)
    pdf.set_font("Arial", 'B', 8)
    pdf.set_text_color(30, 80, 140)
    pdf.cell(16, 6, "F0 (Barra):", ln=0)
    pdf.set_font("Arial", '', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(20, 6, f"{f0_kg_barra:.1f} kg", ln=1)

    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, "Perfil Evolutivo y Asimetrias", ln=True)
    if 'rad' in img_paths: pdf.image(img_paths['rad'], x=10, y=25, w=130)
    if 'tor' in img_paths: pdf.image(img_paths['tor'], x=150, y=25, w=130)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

def generar_pdf_gps_individual(jugador_nombre, sesion_nombre, kpis_abs, kpis_rel, img_paths, escudo_b64, foto_b64, pos_jugador):
    from fpdf import FPDF
    import tempfile
    import os
    import base64

    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    C_DARK = (11, 14, 20)
    C_GOLD = (197, 160, 89)
    C_GRAY = (148, 163, 184)
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    img_files_to_delete = []
    
    if escudo_b64:
        tmp_esc = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        if str(escudo_b64).startswith("http"):
            import requests
            r = requests.get(escudo_b64)
            tmp_esc.write(r.content)
        else:
            tmp_esc.write(base64.b64decode(escudo_b64.split(",")[1] if "," in escudo_b64 else escudo_b64))
        tmp_esc.close()
        img_paths['escudo'] = tmp_esc.name
        img_files_to_delete.append(tmp_esc.name)
        
    if foto_b64:
        tmp_foto = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        if str(foto_b64).startswith("http"):
            import requests
            r = requests.get(foto_b64)
            tmp_foto.write(r.content)
        else:
            tmp_foto.write(base64.b64decode(foto_b64.split(',')[1] if ',' in foto_b64 else foto_b64))
        tmp_foto.close()
        img_paths['foto'] = tmp_foto.name
        img_files_to_delete.append(tmp_foto.name)

    def draw_header(title, subtitle):
        pdf.set_fill_color(*C_DARK)
        pdf.rect(0, 0, 297, 24, 'F')
        pdf.set_fill_color(*C_GOLD)
        pdf.rect(0, 24, 297, 1, 'F')
        if 'escudo' in img_paths:
            pdf.image(img_paths['escudo'], x=12, y=3, w=18)
        if 'foto' in img_paths:
            pdf.image(img_paths['foto'], x=265, y=3, w=18)
            
        pdf.set_xy(35, 5)
        pdf.set_font("Arial", 'B', 15)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(200, 7, clean_txt(title.upper()), ln=1)
        pdf.set_xy(35, 13)
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(*C_GOLD)
        pdf.cell(200, 6, clean_txt(subtitle.upper()), ln=1)
        pdf.set_y(32)

    def draw_kpi(x, y, w, h, title, val_abs, lbl_abs, val_rel, lbl_rel, color_bar=(197, 160, 89)):
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(x, y, w, h, 'DF')
        pdf.set_fill_color(*color_bar)
        pdf.rect(x, y, w, 2, 'F')
        
        pdf.set_xy(x+3, y+4)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(w-6, 4, clean_txt(title.upper()), align='C')
        
        pdf.set_xy(x+3, y+9)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w-6, 7, f"{val_abs} {lbl_abs}", align='C')
        
        pdf.set_xy(x+3, y+18)
        pdf.set_font("Arial", 'B', 7)
        pdf.set_text_color(*C_GRAY)
        pdf.cell((w-6)/2, 4, "Densidad:", align='L')
        pdf.set_text_color(*color_bar)
        pdf.cell((w-6)/2, 4, f"{val_rel} {lbl_rel}", align='R')

    def draw_section_title(txt, y):
        pdf.set_xy(10, y)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(*C_DARK)
        pdf.cell(200, 8, clean_txt(txt), ln=1)
        pdf.set_draw_color(*C_GOLD)
        pdf.line(10, y+8, 287, y+8)
        pdf.set_y(y+12)

    # PÁGINA 1
    pdf.add_page()
    subtitle = f"{jugador_nombre} | {pos_jugador} | {sesion_nombre}"
    draw_header("INFORME GPS INDIVIDUAL", subtitle)
    
    draw_section_title("1. RENDIMIENTO FISICO MEDIO (ABSOLUTO VS RELATIVO)", pdf.get_y())
    
    y_kpi = pdf.get_y()
    w_kpi = 277 / 6
    draw_kpi(10, y_kpi, w_kpi-2, 24, "Distancia", f"{kpis_abs['DIS']:.2f}", "km", f"{kpis_rel['m/min']:.1f}", "m/min", (197, 160, 89))
    draw_kpi(10 + w_kpi, y_kpi, w_kpi-2, 24, "HSR (>21)", f"{kpis_abs['DIS AI']:.0f}", "m", f"{kpis_rel['HSR/min']:.2f}", "m/min", (245, 158, 11))
    draw_kpi(10 + w_kpi*2, y_kpi, w_kpi-2, 24, "Sprints (>24)", f"{kpis_abs['Nº SPR']:.1f}", "n", f"{kpis_rel['SPR/min']:.2f}", "n/min", (239, 68, 68))
    draw_kpi(10 + w_kpi*3, y_kpi, w_kpi-2, 24, "ACC (>3)", f"{kpis_abs['ACC']:.0f}", "n", f"{kpis_rel['ACC/min']:.2f}", "n/min", (16, 185, 129))
    draw_kpi(10 + w_kpi*4, y_kpi, w_kpi-2, 24, "DCC (>3)", f"{kpis_abs['DCC']:.0f}", "n", f"{kpis_rel['DCC/min']:.2f}", "n/min", (139, 92, 246))
    
    x_v = 10 + w_kpi*5
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(x_v, y_kpi, w_kpi-2, 24, 'DF')
    pdf.set_fill_color(236, 72, 153)
    pdf.rect(x_v, y_kpi, w_kpi-2, 2, 'F')
    pdf.set_xy(x_v+3, y_kpi+4)
    pdf.set_font("Arial", 'B', 7)
    pdf.set_text_color(*C_GRAY)
    pdf.cell(w_kpi-8, 4, "VELOCIDAD MAX", align='C')
    pdf.set_xy(x_v+3, y_kpi+9)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(w_kpi-8, 7, f"{kpis_abs['VMAX']:.1f} km/h", align='C')
    pdf.set_xy(x_v+3, y_kpi+18)
    pdf.set_font("Arial", 'B', 7)
    pdf.set_text_color(*C_GRAY)
    pdf.cell((w_kpi-8)/2, 4, "% Hist:", align='L')
    pdf.set_text_color(236, 72, 153)
    pdf.cell((w_kpi-8)/2, 4, f"{kpis_abs['% VMAX']:.1f}%", align='R')

    draw_section_title("2. COMPARACION DATOS / MINUTO (RADAR)", y_kpi + 30)
    if 'radar' in img_paths:
        pdf.image(img_paths['radar'], x=70, y=pdf.get_y()+5, w=150)
        img_files_to_delete.append(img_paths['radar'])

    # PÁGINA 2
    pdf.add_page()
    draw_header("INFORME GPS INDIVIDUAL", subtitle)
    
    draw_section_title("3. DATOS TOTALES", pdf.get_y())
    w_img = 135
    y_img1 = pdf.get_y() + 10 # Bajamos un poco los gráficos para centrarlos visualmente
    
    if 'vol_int' in img_paths:
        pdf.image(img_paths['vol_int'], x=10, y=y_img1, w=w_img)
        img_files_to_delete.append(img_paths['vol_int'])
    if 'tension' in img_paths:
        pdf.image(img_paths['tension'], x=150, y=y_img1, w=w_img)
        img_files_to_delete.append(img_paths['tension'])

    # PÁGINA 3 (Salto de página para que los gráficos de densidad tengan su propio espacio)
    pdf.add_page()
    draw_header("INFORME GPS INDIVIDUAL", subtitle)
    
    draw_section_title("4. DENSIDAD", pdf.get_y())
    y_img2 = pdf.get_y() + 10
    
    if 'den_vol_int' in img_paths:
        pdf.image(img_paths['den_vol_int'], x=10, y=y_img2, w=w_img)
        img_files_to_delete.append(img_paths['den_vol_int'])
    if 'den_tension' in img_paths:
        pdf.image(img_paths['den_tension'], x=150, y=y_img2, w=w_img)
        img_files_to_delete.append(img_paths['den_tension'])
        
    for path in img_files_to_delete:
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)
