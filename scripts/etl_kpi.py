import pandas as pd, numpy as np, json

raw = pd.read_csv("raw_ventas.csv")
prod = pd.read_csv("productos.csv"); cli = pd.read_csv("clientes.csv"); metas = pd.read_csv("metas.csv")
log = {"registros_extraidos": len(raw)}
# --- Transformación
n0 = len(raw); v = raw.drop_duplicates("id_venta"); log["duplicados_eliminados"] = n0 - len(v)
log["canal_mal_escrito"] = int((v.canal != v.canal.str.title().str.replace("Móvil", "móvil")).sum())
v["canal"] = v.canal.str.lower().map({"app móvil": "App móvil", "web": "Web", "marketplace": "Marketplace"})
log["dias_entrega_nulos"] = int(v.dias_entrega.isna().sum())
v = v.merge(cli[["id_cliente", "region"]], on="id_cliente").merge(prod[["id_producto", "categoria"]], on="id_producto")
v["dias_entrega"] = v.dias_entrega.fillna(v.groupby("region").dias_entrega.transform("median"))
v["fecha"] = pd.to_datetime(v.fecha); v["mes"] = v.fecha.dt.to_period("M").astype(str)
v["utilidad"] = v.valor_venta - v.costo_total
log["registros_cargados"] = len(v)
v.to_csv("fact_ventas_limpio.csv", index=False)

P_ACT = ("2026-05", "2026-10"); P_ANT = ("2025-11", "2026-04"); P_AA = ("2025-05", "2025-10")
def per(df, p): return df[(df.mes >= p[0]) & (df.mes <= p[1])]

def kpis(df_all, p, p_prev):
    d = per(df_all, p)
    first = df_all.groupby("id_cliente").fecha.min()
    cl_prev = set(per(df_all, p_prev).id_cliente); cl_now = set(d.id_cliente)
    pedidos = d.groupby(["id_cliente", "fecha"]).ngroups
    meta = metas[(metas.mes >= p[0]) & (metas.mes <= p[1])]
    if df_all.region.nunique() < metas.region.nunique():
        meta = meta[meta.region.isin(df_all.region.unique())]
    return dict(
        ventas=d.valor_venta.sum(), utilidad=d.utilidad.sum(), margen=d.utilidad.sum() / d.valor_venta.sum() * 100,
        pedidos=pedidos, ticket=d.valor_venta.sum() / pedidos,
        clientes=len(cl_now),
        nuevos=int(((first >= pd.Timestamp(p[0] + "-01")) & (first <= pd.Period(p[1]).to_timestamp(how="end"))).sum()),
        retencion=len(cl_prev & cl_now) / len(cl_prev) * 100,
        devolucion=(d.devuelto == "Sí").mean() * 100, entrega=d.dias_entrega.mean(),
        cumplimiento=d.valor_venta.sum() / meta.meta_ventas.sum() * 100)

act = kpis(v, P_ACT, P_ANT); ant = kpis(v, P_ANT, ("2025-05", "2025-10")); aa = kpis(v, P_AA, ("2024-11", "2025-04"))
res = pd.DataFrame({"Últimos 6m (may–oct 2026)": act, "6m anteriores (nov 2025–abr 2026)": ant, "Mismo periodo 2025 (may–oct 2025)": aa})
res["Var % vs 6m ant."] = (res.iloc[:, 0] / res.iloc[:, 1] - 1) * 100
res["Var % vs año ant."] = (res.iloc[:, 0] / res.iloc[:, 2] - 1) * 100
pd.set_option("display.float_format", lambda x: f"{x:,.1f}"); pd.set_option("display.width", 200)
print(json.dumps(log)); print(res)

def breakdown(col):
    a = per(v, P_ACT).groupby(col).valor_venta.sum(); b = per(v, P_ANT).groupby(col).valor_venta.sum(); c = per(v, P_AA).groupby(col).valor_venta.sum()
    t = pd.DataFrame({"actual": a, "ant": b, "aa": c}); t["var_ant"] = (t.actual / t.ant - 1) * 100; t["var_aa"] = (t.actual / t.aa - 1) * 100
    t["aporte_caida_%"] = (t.actual - t.ant) / (t.actual - t.ant).sum() * 100
    return t
for c in ["region", "categoria", "canal"]:
    print(breakdown(c))
# entrega y devolución por región
g = lambda d: d.groupby("region").agg(entrega=("dias_entrega", "mean"), devol=("devuelto", lambda s: (s == "Sí").mean() * 100))
print(pd.concat([g(per(v, P_ANT)), g(per(v, P_ACT))], axis=1, keys=["ant", "act"]))
# retención por región
for r in v.region.unique():
    vr = v[v.region == r]; print(r, round(len(set(per(vr, P_ANT).id_cliente) & set(per(vr, P_ACT).id_cliente)) / len(set(per(vr, P_ANT).id_cliente)) * 100, 1))
print(v.groupby("mes").valor_venta.sum().apply(lambda x: f"{x/1e6:,.0f}"))
