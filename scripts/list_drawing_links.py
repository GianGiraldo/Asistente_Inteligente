# -*- coding: utf-8 -*-
import re
import zipfile

p = r"c:\Proyectos\Aplicacion_Personal\content\excel\Curso.xlsx"
with zipfile.ZipFile(p) as z:
    for rel in sorted(z.namelist()):
        if rel.startswith("xl/drawings/_rels/drawing") and rel.endswith(".rels"):
            data = z.read(rel).decode()
            targets = re.findall(r'Target="([^"]+)"', data)
            if any("hyperlink" in t or "#" in t for t in targets):
                print(rel, targets[:5])
