# -*- coding: utf-8 -*-
import zipfile
import re

ORIG = r"c:\Proyectos\Aplicacion_Personal\content\excel\Curso.xlsx"

with zipfile.ZipFile(ORIG) as z:
    names = z.namelist()
    print("vbaProject:", "xl/vbaProject.bin" in names)
    print("drawings:", [n for n in names if "drawing" in n.lower()][:15])
    print("ctrl:", [n for n in names if "ctrl" in n.lower() or "vml" in n.lower()][:15])

    # hyperlinks in sheet1 (Area)
    for sn in ["xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"]:
        if sn in names:
            t = z.read(sn).decode("utf-8", errors="replace")
            hls = re.findall(r"<hyperlink[^>]*>", t)
            print(f"\n{sn} hyperlinks ({len(hls)}):")
            for h in hls[:15]:
                print(" ", h[:150])
            # cell values row 1-2
            rows = re.findall(r"<row r=\"([12])\"[^>]*>(.*?)</row>", t, re.DOTALL)
            for rn, body in rows:
                vals = re.findall(r"<c r=\"([A-Z]+[12])\"[^>]*><v>([^<]*)</v>", body)
                vals += re.findall(r"<c r=\"([A-Z]+[12])\"[^>]*t=\"s\"><v>(\d+)</v>", body)
                print(f"  Row {rn} cells:", vals[:12])

    # shared strings sample for menu text
    if "xl/sharedStrings.xml" in names:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
        for term in ["INICIO", "ENFOQUE", "CONTROL", "FUNCIONARIOS", "MISION", "VISION"]:
            if term in ss:
                print(f"sharedStrings contains: {term}")

    # workbook sheet list with sheetId
    wb = z.read("xl/workbook.xml").decode("utf-8")
    for m in re.finditer(r"<sheet[^>]*name=\"([^\"]+)\"[^>]*/>", wb):
        print("Sheet name:", m.group(1))

    # drawing rels for sheet1
    rel = "xl/worksheets/_rels/sheet1.xml.rels"
    if rel in names:
        print("\nsheet1 rels:", z.read(rel).decode()[:2000])

    d1 = "xl/drawings/drawing1.xml"
    if d1 in names:
        d = z.read(d1).decode("utf-8", errors="replace")
        print("\ndrawing1 snippet:", d[:3000])
        # macro assignments
        if "macro" in d.lower() or "hyperlink" in d.lower():
            for m in re.finditer(r".{0,40}(macro|hyperlink|hlink).{0,80}", d, re.I):
                print(" ", m.group(0))
