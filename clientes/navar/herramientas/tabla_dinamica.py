# -*- coding: utf-8 -*-
"""
tabla_dinamica — le agrega a un export de Tango una TABLA DINÁMICA de verdad (la de Excel),
armada por año → mes → proveedor, sumando el importe.

Qué hace con el archivo:
  1. agrega dos columnas a los datos: "Año" y "Mes" (el mes va como "07 Julio" para que ordene
     cronológicamente y no alfabéticamente);
  2. crea una solapa nueva con la tabla dinámica: filas Año, Mes y Razón social, valor la suma
     del importe. Se abre y se cierra con los [+] y [-] de la izquierda, y los campos se pueden
     arrastrar como cualquier dinámica;
  3. deja también una solapa "Resumen" con los totales por año ya calculados, por si alguien
     abre el archivo en Google Sheets o en el celular (las dinámicas de Excel no se ven ahí).

La dinámica se guarda "para refrescar al abrir": Excel la llena con los datos de la solapa al
abrir el archivo. Si se agregan filas después, se refresca con click derecho → Actualizar.

USO
    python clientes/navar/herramientas/tabla_dinamica.py --archivo "<ruta>.xlsx"
    python ... --archivo x.xlsx --fecha "Fecha de vencimiento" --importe "Total pendiente (CTE)" --quien "Razón social"
"""

import os
import sys
import shutil
import datetime
import argparse

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.pivot.cache import CacheDefinition, CacheSource, WorksheetSource, CacheField, SharedItems
from openpyxl.pivot.table import (TableDefinition, Location, PivotField, RowColField, DataField,
                                  FieldItem, RowColItem, PivotTableStyle)

MESES = ["01 Enero", "02 Febrero", "03 Marzo", "04 Abril", "05 Mayo", "06 Junio",
         "07 Julio", "08 Agosto", "09 Septiembre", "10 Octubre", "11 Noviembre", "12 Diciembre"]
FORMATO = "#,##0.00"


def agregar_ano_mes(ws, col_fecha):
    """Agrega las columnas Año y Mes al final. Devuelve los encabezados finales."""
    enc = [c.value for c in ws[1]]
    if "Año" in enc and "Mes" in enc:
        return enc
    i = enc.index(col_fecha) + 1
    n = ws.max_column
    ws.cell(1, n + 1, "Año").font = Font(bold=True)
    ws.cell(1, n + 2, "Mes").font = Font(bold=True)
    for f in range(2, ws.max_row + 1):
        v = ws.cell(f, i).value
        if isinstance(v, datetime.datetime):
            ws.cell(f, n + 1, v.year)
            ws.cell(f, n + 2, MESES[v.month - 1])
    return [c.value for c in ws[1]]


def hoja_resumen(wb, ws, enc, col_fecha, col_importe, col_quien):
    """Totales por año y por mes, calculados: se ven en cualquier lado (Excel, Sheets, celular)."""
    i_f, i_i, i_q = enc.index(col_fecha), enc.index(col_importe), enc.index(col_quien)
    datos = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        f, imp = r[i_f], r[i_i]
        if not isinstance(f, datetime.datetime) or not isinstance(imp, (int, float)):
            continue
        datos.setdefault(f.year, {}).setdefault(MESES[f.month - 1], {}).setdefault(str(r[i_q] or "(sin nombre)"), 0.0)
        datos[f.year][MESES[f.month - 1]][str(r[i_q] or "(sin nombre)")] += float(imp)
    h = wb["Resumen"] if "Resumen" in wb.sheetnames else wb.create_sheet("Resumen", 0)
    h.delete_rows(1, h.max_row)
    h.append(["Año", "Mes", "Proveedor", col_importe])
    for c in h[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="174EA6")
    fila = 2
    for ano in sorted(datos):
        ini_ano = fila
        tot_ano = sum(v for m in datos[ano].values() for v in m.values())
        h.cell(fila, 1, ano).font = Font(bold=True)
        h.cell(fila, 4, tot_ano).font = Font(bold=True)
        fila += 1
        for mes in sorted(datos[ano]):
            ini_mes = fila
            h.cell(fila, 2, mes).font = Font(bold=True, color="5F6368")
            h.cell(fila, 4, sum(datos[ano][mes].values())).font = Font(bold=True, color="5F6368")
            fila += 1
            for quien, v in sorted(datos[ano][mes].items(), key=lambda x: -x[1]):
                h.cell(fila, 3, quien)
                h.cell(fila, 4, v)
                fila += 1
            if fila - 1 > ini_mes:
                h.row_dimensions.group(ini_mes + 1, fila - 1, outline_level=2, hidden=True)
        if fila - 1 > ini_ano:
            h.row_dimensions.group(ini_ano + 1, fila - 1, outline_level=1, hidden=True)
    for f in h.iter_rows(min_row=2, min_col=4, max_col=4):
        f[0].number_format = FORMATO
    h.column_dimensions["A"].width = 10
    h.column_dimensions["B"].width = 14
    h.column_dimensions["C"].width = 46
    h.column_dimensions["D"].width = 20
    h.freeze_panes = "A2"
    h.sheet_properties.outlinePr.summaryBelow = False      # el total del año va arriba del detalle
    return h


def agregar_pivot(wb, ws, enc, col_importe, campos_fila):
    ref = "A1:%s%d" % (get_column_letter(ws.max_column), ws.max_row)
    cache = CacheDefinition(
        cacheSource=CacheSource(type="worksheet", worksheetSource=WorksheetSource(ref=ref, sheet=ws.title)),
        cacheFields=[CacheField(name=h, sharedItems=SharedItems()) for h in enc],
        recordCount=0, saveData=False, refreshOnLoad=True,      # Excel la llena al abrir el archivo
        createdVersion=5, refreshedVersion=6, minRefreshableVersion=3)
    cache.records = None
    idx = [enc.index(c) for c in campos_fila]
    i_imp = enc.index(col_importe)
    campos = []
    for k in range(len(enc)):
        if k in idx:
            campos.append(PivotField(axis="axisRow", showAll=False, defaultSubtotal=True,
                                     compact=False, outline=False, items=[FieldItem(t="default")]))
        elif k == i_imp:
            campos.append(PivotField(dataField=True, showAll=False, defaultSubtotal=False, compact=False, outline=False))
        else:
            campos.append(PivotField(showAll=False, compact=False, outline=False))
    hoja = wb.create_sheet("Tabla dinámica", 0)
    hoja["A1"] = "Deuda por año, mes y proveedor"
    hoja["A1"].font = Font(bold=True, size=14, color="174EA6")
    hoja["A2"] = "Abrí y cerrá cada año con los [+] y [-]. Para cambiar los campos: click en la tabla → panel de la derecha."
    hoja["A2"].font = Font(italic=True, color="5F6368")
    hoja.column_dimensions["A"].width = 46
    hoja.column_dimensions["B"].width = 22
    p = TableDefinition(
        name="DeudaPorAno", cacheId=1, dataCaption="Valores",
        createdVersion=5, updatedVersion=6, minRefreshableVersion=3,
        useAutoFormatting=True, indent=0, compact=False, compactData=False, outline=False, outlineData=False,
        applyNumberFormats=False, applyBorderFormats=False, applyFontFormats=False, applyPatternFormats=False,
        applyAlignmentFormats=False, applyWidthHeightFormats=True, itemPrintTitles=True, multipleFieldFilters=False,
        location=Location(ref="A4:B30", firstHeaderRow=1, firstDataRow=2, firstDataCol=1),
        pivotFields=campos,
        rowFields=[RowColField(x=i) for i in idx],
        rowItems=[RowColItem(t="default", i=0, x=[])],
        dataFields=[DataField(name="Suma de " + col_importe, fld=i_imp, baseField=-1, baseItem=0)],
        pivotTableStyleInfo=PivotTableStyle(name="PivotStyleLight16", showRowHeaders=True, showColHeaders=True,
                                            showRowStripes=False, showColStripes=False, showLastColumn=True))
    p.cache = cache
    hoja.add_pivot(p)
    return hoja


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--hoja", default=None, help="solapa con los datos (default: la primera)")
    ap.add_argument("--fecha", default="Fecha de vencimiento")
    ap.add_argument("--importe", default="Total pendiente (CTE)")
    ap.add_argument("--quien", default="Razón social")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()

    salida = a.salida or a.archivo.replace(".xlsx", " - con tabla dinámica.xlsx")
    wb = openpyxl.load_workbook(a.archivo)
    ws = wb[a.hoja] if a.hoja else wb.worksheets[0]
    enc = [c.value for c in ws[1]]
    for col in (a.fecha, a.importe, a.quien):
        if col not in enc:
            sys.exit("la solapa '%s' no tiene la columna '%s'. Columnas: %s" % (ws.title, col, enc))
    enc = agregar_ano_mes(ws, a.fecha)
    hoja_resumen(wb, ws, enc, a.fecha, a.importe, a.quien)
    agregar_pivot(wb, ws, enc, a.importe, ["Año", "Mes", a.quien])
    wb.save(salida)
    print(salida)


if __name__ == "__main__":
    main()
