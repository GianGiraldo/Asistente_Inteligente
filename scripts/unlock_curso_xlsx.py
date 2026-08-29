# -*- coding: utf-8 -*-
"""
Genera copia editable de Curso.xlsx SIN romper navegacion interactiva.
La navegacion usa formas (drawings) con hlinkClick -> #Hoja!A1
openpyxl.save() elimina esos enlaces; este script solo parchea XML en el zip.
"""
import os
import re
import shutil
import zipfile
import tempfile

SRC = r"c:\Proyectos\Aplicacion_Personal\content\excel\Curso.xlsx"
DST = r"c:\Proyectos\Aplicacion_Personal\content\excel\Curso_Editable_Interactivo.xlsx"


def count_hlinks(z: zipfile.ZipFile) -> int:
    total = 0
    for name in z.namelist():
        if name.startswith("xl/drawings/drawing") and name.endswith(".xml"):
            total += z.read(name).decode("utf-8", errors="replace").count("hlinkClick")
    return total


def patch_workbook_unhide(data: bytes) -> bytes:
    text = data.decode("utf-8")
    # Mantener DCargos/Auxiliar ocultas (datos); solo quitar proteccion de edicion
    return text.encode("utf-8")


def patch_sheet_remove_protection(data: bytes) -> tuple[bytes, bool]:
    text = data.decode("utf-8")
    if "sheetProtection" not in text:
        return data, False
    # Quitar cualquier sheetProtection (con o sin password)
    new_text, n = re.subn(r"<sheetProtection[^>]*/>", "", text)
    return (new_text.encode("utf-8") if n else data), n > 0


def build_editable_copy(
    src: str = SRC,
    dst: str = DST,
    unhide_auxiliary_sheets: bool = False,
) -> dict:
    if os.path.exists(dst):
        os.remove(dst)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(tmp_fd)

    stats = {"sheets_unlocked": 0, "hlinks_before": 0, "hlinks_after": 0, "drawings": 0}

    with zipfile.ZipFile(src, "r") as zin:
        stats["hlinks_before"] = count_hlinks(zin)
        stats["drawings"] = len(
            [n for n in zin.namelist() if n.startswith("xl/drawings/drawing") and n.endswith(".xml")]
        )

        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename == "xl/workbook.xml" and unhide_auxiliary_sheets:
                    text = data.decode("utf-8")
                    text = re.sub(r'\s+state="hidden"', "", text)
                    data = text.encode("utf-8")

                if item.filename.startswith("xl/worksheets/sheet") and item.filename.endswith(".xml"):
                    data, changed = patch_sheet_remove_protection(data)
                    if changed:
                        stats["sheets_unlocked"] += 1

                zout.writestr(item, data)

    with zipfile.ZipFile(tmp_path, "r") as zout:
        stats["hlinks_after"] = count_hlinks(zout)

    os.replace(tmp_path, dst)
    stats["dst"] = dst
    stats["size_mb"] = os.path.getsize(dst) / 1024 / 1024
    return stats


def main():
    stats = build_editable_copy(unhide_auxiliary_sheets=False)
    print("=== Curso editable (navegacion interactiva preservada) ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["hlinks_after"] != stats["hlinks_before"]:
        print("  AVISO: hipervinculos cambiaron — revisar archivo")
    else:
        print("  OK: todos los botones de menu conservados")


if __name__ == "__main__":
    main()
