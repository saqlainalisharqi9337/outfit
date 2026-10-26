# -*- coding: utf-8 -*-
"""
Full BS/MCS Thesis Documentation Builder for ADORE
(Smart Cloth Advisor and Outfit Recommender App)
Authors: Saqlain Ali (Roll # 49), Rubab Iqbal (Roll # 46)
Supervisor: Dr. Sajjad Ahmed Nadeem
Department of Computer Science & Information Technology, University of Azad Jammu & Kashmir, Muzaffarabad
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_document():
    doc = Document()

    # Configure default Page Setup for A4 and Margins (Format_for_MCS_BS_Thesis)
    # Page Size: A4 (8.27" x 11.69")
    # Page Margins: Top & Bottom = 1" and Left = 1.5" & Right = 1.25"
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.25)
        
        # Configure Footer for page numbering (Bottom Center)
        footer = section.footer
        f_p = footer.paragraphs[0]
        f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        f_run = f_p.add_run()
        f_run.font.name = 'Times New Roman'
        f_run.font.size = Pt(10)
        
        # Add dynamic page number field
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = "PAGE"
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')
        f_run._r.append(fldChar1)
        f_run._r.append(instrText)
        f_run._r.append(fldChar2)
        f_run._r.append(fldChar3)

    # Base styling helper
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.5
    normal_style.paragraph_format.space_after = Pt(6)

    def p(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=0, space_after=6, font_size=12):
        para = doc.add_paragraph()
        para.alignment = align
        para.paragraph_format.line_spacing = 1.5
        para.paragraph_format.space_before = Pt(space_before)
        para.paragraph_format.space_after = Pt(space_after)
        if text:
            run = para.add_run(text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(font_size)
            run.bold = bold
            run.italic = italic
            run.font.color.rgb = RGBColor(0, 0, 0)
        return para

    def h1(text, space_before=18, space_after=12):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.line_spacing = 1.5
        para.paragraph_format.space_before = Pt(space_before)
        para.paragraph_format.space_after = Pt(space_after)
        run = para.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return para

    def h2(text, space_before=14, space_after=6):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.line_spacing = 1.5
        para.paragraph_format.space_before = Pt(space_before)
        para.paragraph_format.space_after = Pt(space_after)
        run = para.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return para

    def h3(text, space_before=10, space_after=4):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.line_spacing = 1.5
        para.paragraph_format.space_before = Pt(space_before)
        para.paragraph_format.space_after = Pt(space_after)
        run = para.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.bold = True
        run.italic = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return para

    def add_fig(img_path, caption, width=5.5):
        if os.path.exists(img_path):
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(12)
            para.paragraph_format.space_after = Pt(4)
            run = para.add_run()
            run.add_picture(img_path, width=Inches(width))
            
            c_para = doc.add_paragraph()
            c_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c_para.paragraph_format.space_before = Pt(2)
            c_para.paragraph_format.space_after = Pt(14)
            c_run = c_para.add_run(caption)
            c_run.font.name = 'Times New Roman'
            c_run.font.size = Pt(11)
            c_run.bold = True
            c_run.italic = True

    def add_tbl(caption, headers, rows, col_widths=None):
        c_para = doc.add_paragraph()
        c_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_para.paragraph_format.space_before = Pt(12)
        c_para.paragraph_format.space_after = Pt(4)
        c_run = c_para.add_run(caption)
        c_run.font.name = 'Times New Roman'
        c_run.font.size = Pt(11)
        c_run.bold = True
        
        table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Header Row
        hdr_cells = table.rows[0].cells
        for idx, title in enumerate(headers):
            hdr_cells[idx].text = title
            p_hdr = hdr_cells[idx].paragraphs[0]
            p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_hdr.runs[0].font.name = 'Times New Roman'
            p_hdr.runs[0].font.size = Pt(10.5)
            p_hdr.runs[0].bold = True
            # Background
            tcPr = hdr_cells[idx]._element.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="2C3E50"/>')
            tcPr.append(shd)
            p_hdr.runs[0].font.color.rgb = RGBColor(255, 255, 255)
            
        for r_idx, row_data in enumerate(rows):
            row_cells = table.rows[r_idx + 1].cells
            fill_color = "F2F4F4" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, cell_value in enumerate(row_data):
                row_cells[c_idx].text = str(cell_value)
                p_cell = row_cells[c_idx].paragraphs[0]
                p_cell.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx != 0 else WD_ALIGN_PARAGRAPH.CENTER
                if len(p_cell.runs) > 0:
                    p_cell.runs[0].font.name = 'Times New Roman'
                    p_cell.runs[0].font.size = Pt(10)
                tcPr = row_cells[c_idx]._element.get_or_add_tcPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
                tcPr.append(shd)
                
        p("", space_after=10)

    print("Document structure initialized. Writing chapters...")
    return doc, p, h1, h2, h3, add_fig, add_tbl

doc, p, h1, h2, h3, add_fig, add_tbl = create_document()
print("Initialized builder.")
