# -*- coding: utf-8 -*-
"""Mapa de navegacion: botones -> hoja destino"""
import re
import zipfile

p = r"c:\Proyectos\Aplicacion_Personal\content\excel\Curso_Editable_Interactivo.xlsx"

with zipfile.ZipFile(p) as z:
  # sheet name -> drawing file from workbook rels
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    rid_to_file = {}
    for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="worksheets/(sheet\d+\.xml)"', rels):
        rid_to_file[m.group(1)] = m.group(2)

    sheets = []
    for m in re.finditer(r'name="([^"]+)"[^>]*r:id="(rId\d+)"', wb):
        name, rid = m.group(1), m.group(2)
        sheets.append((name, rid_to_file.get(rid)))

    print("=== MAPA DE HOJAS (pestañas inferiores de Excel) ===\n")
    for i, (name, file) in enumerate(sheets, 1):
        print(f"  {i:2}. {name}")

    print("\n=== MENU INTERACTIVO (Area / INICIO) - drawing1 ===\n")
    d = z.read("xl/drawings/drawing1.xml").decode()
    rel = z.read("xl/drawings/_rels/drawing1.xml.rels").decode()
    rid_targets = {}
    for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rel):
        rid_targets[m.group(1)] = m.group(2)

    texts = re.findall(r"<a:t>([^<]+)</a:t>", d)
    rids = re.findall(r'hlinkClick[^>]*r:id="(rId\d+)"', d)
    for t, rid in zip(texts, rids):
        target = rid_targets.get(rid, "?")
        dest = target.replace("#", "").replace("!A1", "") if target.startswith("#") else target
        print(f"  [{t.strip()}]  ->  hoja {dest}")
