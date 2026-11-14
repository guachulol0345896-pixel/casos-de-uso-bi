import pandas as pd, numpy as np, json
v = pd.read_csv("fact_ventas_limpio.csv", parse_dates=["fecha"])
metas = pd.read_csv("metas.csv")
months = sorted(v.mes.unique())
P_ACT = ("2026-05", "2026-10"); P_ANT = ("2025-11", "2026-04"); P_AA = ("2025-05", "2025-10")
per = lambda df, p: df[(df.mes >= p[0]) & (df.mes <= p[1])]
first = v.groupby("id_cliente").mes.min()

def kp(df, p, pp, regs=None):
    d = per(df, p); prev = set(per(df, pp).id_cliente)
    m = metas[(metas.mes >= p[0]) & (metas.mes <= p[1])]
    if regs: m = m[m.region.isin(regs)]
    nuevos = first[(first >= p[0]) & (first <= p[1])]
    nuevos = nuevos[nuevos.index.isin(d.id_cliente)]
    return {"Ventas totales": d.valor_venta.sum(), "Utilidad bruta": d.utilidad.sum(),
            "Margen de utilidad (%)": d.utilidad.sum() / d.valor_venta.sum() * 100,
            "Transacciones": len(d), "Ticket promedio": d.valor_venta.sum() / len(d),
            "Clientes activos": d.id_cliente.nunique(), "Clientes nuevos": len(nuevos),
            "Tasa de retención (%)": len(prev & set(d.id_cliente)) / len(prev) * 100,
            "Tasa de devolución (%)": (d.devuelto == "Sí").mean() * 100,
            "Tiempo promedio de entrega (días)": d.dias_entrega.mean(),
            "Cumplimiento de meta (%)": d.valor_venta.sum() / m.meta_ventas.sum() * 100}

R = {"act": kp(v, P_ACT, P_ANT), "ant": kp(v, P_ANT, ("2025-05", "2025-10")), "aa": kp(v, P_AA, ("2024-11", "2025-04"))}
def brk(col):
    out = []
    for k, g in v.groupby(col):
        a, b = per(g, P_ACT), per(g, P_ANT)
        row = {col: k, "ventas_ant": b.valor_venta.sum(), "ventas_act": a.valor_venta.sum()}
        row["var"] = (row["ventas_act"] / row["ventas_ant"] - 1) * 100
        row["aporte"] = row["ventas_act"] - row["ventas_ant"]
        row["entrega_ant"], row["entrega_act"] = b.dias_entrega.mean(), a.dias_entrega.mean()
        row["dev_ant"], row["dev_act"] = (b.devuelto == "Sí").mean() * 100, (a.devuelto == "Sí").mean() * 100
        pc = set(b.id_cliente); row["retencion"] = len(pc & set(a.id_cliente)) / len(pc) * 100
        row["ticket_act"] = a.valor_venta.sum() / len(a); row["ticket_ant"] = b.valor_venta.sum() / len(b)
        out.append(row)
    t = sum(r["aporte"] for r in out)
    for r in out: r["aporte_pct"] = r["aporte"] / t * 100
    return out
R["region"], R["categoria"], R["canal"] = brk("region"), brk("categoria"), brk("canal")
# Tecnología en Caribe vs resto
tc = v[(v.categoria == "Tecnología")]
R["tec_caribe"] = {"var": (per(tc[tc.region == "Caribe"], P_ACT).valor_venta.sum() / per(tc[tc.region == "Caribe"], P_ANT).valor_venta.sum() - 1) * 100,
                   "var_resto": (per(tc[tc.region != "Caribe"], P_ACT).valor_venta.sum() / per(tc[tc.region != "Caribe"], P_ANT).valor_venta.sum() - 1) * 100}
# Devolución según días de entrega
v["rango_entrega"] = pd.cut(v.dias_entrega, [0, 3, 5, 7, 99], labels=["1–3 días", "4–5 días", "6–7 días", "8+ días"])
R["dev_por_entrega"] = v.groupby("rango_entrega", observed=True).agg(transacciones=("id_venta", "size"), devolucion=("devuelto", lambda s: (s == "Sí").mean() * 100)).reset_index().astype({"rango_entrega": str}).to_dict("records")
R["corr_entrega_dev"] = float(np.corrcoef(v.dias_entrega, (v.devuelto == "Sí").astype(int))[0, 1])
# Retención por región pre-cambio (control)
R["mensual"] = v.groupby("mes").agg(ventas=("valor_venta", "sum")).reset_index().merge(metas.groupby("mes").meta_ventas.sum().reset_index()).to_dict("records")
R["mensual_reg"] = v.pivot_table(index="mes", columns="region", values="valor_venta", aggfunc="sum").reset_index().to_dict("records")
R["entrega_mes_reg"] = v.pivot_table(index="mes", columns="region", values="dias_entrega", aggfunc="mean").round(2).reset_index().to_dict("records")
json.dump(R, open("results.json", "w"), default=float, ensure_ascii=False, indent=1)

# Datos compactos para el dashboard
R_ = sorted(v.region.unique()); C_ = sorted(v.categoria.unique()); K_ = sorted(v.canal.unique())
cid = {c: i for i, c in enumerate(v.id_cliente.unique())}
rows = [[months.index(r.mes), R_.index(r.region), C_.index(r.categoria), K_.index(r.canal), cid[r.id_cliente],
         int(r.valor_venta // 100), int(r.utilidad // 100), int(r.dias_entrega), 1 if r.devuelto == "Sí" else 0]
        for r in v.itertuples()]
mt = metas.pivot_table(index="mes", columns="region", values="meta_ventas").reindex(columns=R_)
D = {"months": months, "regions": R_, "cats": C_, "canales": K_, "rows": rows,
     "metas": [[int(x // 100) for x in mt.loc[m]] for m in months]}
json.dump(D, open("dash_data.json", "w"), separators=(",", ":"), ensure_ascii=False)
for k in R["act"]: print(f"{k:38s} {R['ant'][k]:>16,.1f} {R['act'][k]:>16,.1f} {(R['act'][k]/R['ant'][k]-1)*100:6.1f}%")
print(R["tec_caribe"], R["dev_por_entrega"], R["corr_entrega_dev"])
for r in R["region"]: print(r["region"], round(r["var"],1), round(r["aporte_pct"],1), round(r["retencion"],1), round(r["entrega_act"],1), round(r["dev_act"],1))
