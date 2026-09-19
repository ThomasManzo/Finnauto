import json, datetime, openpyxl, calendar, sys
from collections import defaultdict
INFL=0.017; hoy=datetime.date(2026,9,18); H=hoy.isoformat()
c = json.load(open("clientes/navar/contrato_2026-09-18.json"))
wb = openpyxl.load_workbook("clientes/navar/privado/bancos/para_pegar_bancos_2026-09-18.xlsx", data_only=True)
ws = wb["Movimientos"]; enc=[x.value for x in ws[1]]
real = defaultdict(lambda: defaultdict(float))
for r in ws.iter_rows(min_row=2, values_only=True):
    d = dict(zip(enc, r))
    if "INTERNO" in str(d["Observaciones"]): continue
    real[d["Fecha"].strftime("%Y-%m")][(d["Tipo"], d["Categoria"])] += abs(d["Importe"])
def mes(f): return str(f)[:7]
def lista(items, key="importe"):
    out=defaultdict(float)
    for x in items:
        if x["fecha"] >= H: out[mes(x["fecha"])]+=x[key]
    return out
cobrar = lista(c["cuentas_a_cobrar_droguerias"]); pagar = lista([x for x in c["deuda_droguerias"] if not x.get("es_credito")])
cuotas = lista(c["deuda_bancaria"]["cuotas"]); impdeu = lista(c["deuda_impositiva"])
chqprop = lista([x for x in c["cartera_cheques"] if x["propio"]])
proy = lista([x for x in c["egresos_cashflow"] if x["origen"] not in ("Deuda Bancaria (cronograma)","Deuda Impositiva") and x["tipo"] not in ("CHEQUE","SUELDO")])
base=["2026-06","2026-07","2026-08"]; fut=["2026-10","2026-11","2026-12","2027-01","2027-02","2027-03"]; cols=base+["2026-09"]+fut
R=lambda m,t,cat: real[m].get((t,cat),0)
avg=lambda t,cat: sum(R(m,t,cat) for m in base)/3
I=lambda t,cat: (lambda m: R(m,t,cat), lambda n,m: avg(t,cat)*(1+INFL)**n, "prom")
L = {
 "ing": [
  ("Cobranza acreditada (transferencias y depósitos de clientes)",)+I("Ingreso","Cobranza Facturas"),
  ("Cheques de clientes depositados",)+I("Ingreso","Cheques"),
  ("Descuento de cheques (venta de valores)",)+I("Ingreso","Descuento de Cheques"),
  ("Préstamos nuevos", lambda m: R(m,"Ingreso","Prestamo"), lambda n,m: 0, "cero"),
  ("Sin identificar", lambda m: R(m,"Ingreso","Otros"), lambda n,m: 0, "cero"),
 ],
 "egr": [
  ("Proveedores", lambda m: R(m,"Egreso","Proveedores MP y Logist."), lambda n,m: max(pagar.get(m,0), avg("Egreso","Proveedores MP y Logist.")*(1+INFL)**n), "max"),
  ("Sueldos y cargas (del 1 al 10)",)+I("Egreso","Sueldos y Jornales"),
  ("Cuotas bancarias (cronograma)", lambda m: R(m,"Egreso","Prestamo"), lambda n,m: cuotas.get(m,0), "lista"),
  ("Impuestos corrientes (IVA, cargas, retenciones)",)+I("Egreso","Impuestos"),
  ("Impuestos: deuda y planes (vencimientos)", lambda m: 0, lambda n,m: impdeu.get(m,0), "lista"),
  ("Cheques propios (por fecha de pago)", lambda m: R(m,"Egreso","Cheques"), lambda n,m: chqprop.get(m,0), "lista"),
  ("Tarjeta de crédito y otros", lambda m: R(m,"Egreso","Otros")+R(m,"Egreso","Honorarios y Dividendos"), lambda n,m: avg("Egreso","Otros")*(1+INFL)**n, "prom"),
  ("Intereses y gastos bancarios",)+I("Egreso","Gastos Bancarios"),
  ("Otros con fecha (cosecha, estampillas, honorarios)", lambda m: 0, lambda n,m: proy.get(m,0), "lista"),
 ]}
def fila(fr, fe, modo):
    vals=[]
    for m in cols:
        if m in base: vals.append((fr(m), True))
        elif m=="2026-09":
            dias=calendar.monthrange(2026,9)[1]; resto=(dias-hoy.day)/dias
            est = fe(1,m) if modo=="lista" else fe(1,m)*resto
            vals.append((fr(m)+est, False))
        else: vals.append((fe(fut.index(m)+2, m), False))
    return vals
res={"cols":cols,"ing":[],"egr":[]}
for k in ("ing","egr"):
    for nombre, fr, fe, modo in L[k]: res[k].append((nombre, modo, fila(fr,fe,modo)))
tot={k:[sum(r[2][i][0] for r in res[k]) for i in range(len(cols))] for k in ("ing","egr")}
res["tot"]=tot
# saldo: sep arranca de la caja de hoy y suma solo lo que falta del mes
saldo0=c["caja_hoy"]; saldos=[]; s=saldo0
for i,m in enumerate(cols):
    if m in base: saldos.append(None); continue
    if m=="2026-09":
        ing_real=sum(r[1](m) for r in [(0,fr) for _,fr,_,_ in L["ing"]]); egr_real=sum(fr(m) for _,fr,_,_ in L["egr"])
        s = saldo0 + (tot["ing"][i]-ing_real) - (tot["egr"][i]-egr_real)
    else: s = s + tot["ing"][i]-tot["egr"][i]
    saldos.append(s)
res["saldos"]=saldos; res["acuerdos"]=160e6; res["caja_hoy"]=saldo0
res["tango"]={"cobrar":dict(cobrar),"pagar":dict(pagar)}
if __name__=="__main__":
    print("%-58s"%"" + "".join("%9s"%m[2:] for m in cols))
    for k in ("ing","egr"):
        for nombre, modo, vals in res[k]: print("%-58s"%(nombre+" ["+modo+"]") + "".join("%9.1f"%(v/1e6) for v,_ in vals))
        print("%-58s"%("TOTAL "+k.upper()) + "".join("%9.1f"%(v/1e6) for v in tot[k]))
    print("%-58s"%"Saldo bancos al cierre" + "".join("%9s"%("" if v is None else "%.1f"%(v/1e6)) for v in saldos))
    print("%-58s"%"Disponible (saldo + acuerdos)" + "".join("%9s"%("" if v is None else "%.1f"%((v+160e6)/1e6)) for v in saldos))
    print("Tango cobrar:", {m: round(v/1e6,1) for m,v in sorted(cobrar.items())}); print("Tango pagar:", {m: round(v/1e6,1) for m,v in sorted(pagar.items())})
