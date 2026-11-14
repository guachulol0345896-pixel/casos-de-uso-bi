"""Genera el dataset sintético de TiendaNova S.A.S. (e-commerce, Colombia).
Periodo: nov-2024 a oct-2026. Historia: caída de ~15% en los últimos 6 meses,
concentrada en la región Caribe y la categoría Tecnología, asociada a mayores
tiempos de entrega (cambio de transportadora en may-2026) y más devoluciones."""
import numpy as np, pandas as pd

rng = np.random.default_rng(42)
months = pd.period_range("2024-11", "2026-10", freq="M")
CUT = pd.Period("2026-05", "M")  # inicio de los últimos 6 meses

regiones = {"Andina": 0.38, "Caribe": 0.24, "Pacífico": 0.16, "Orinoquía": 0.08, "Bogotá D.C.": 0.14}
categorias = {  # (peso, precio medio, margen)
    "Tecnología": (0.30, 620000, 0.18),
    "Hogar": (0.22, 180000, 0.32),
    "Moda": (0.20, 120000, 0.45),
    "Deportes": (0.14, 210000, 0.35),
    "Belleza": (0.14, 75000, 0.50),
}
canales = {"App móvil": 0.48, "Web": 0.40, "Marketplace": 0.12}

# Productos
prod_rows, pid = [], 1
for cat, (w, p, m) in categorias.items():
    for i in range(12):
        price = round(p * rng.uniform(0.5, 1.6), -3)
        prod_rows.append(dict(id_producto=f"P{pid:03d}", producto=f"{cat} {i+1:02d}", categoria=cat,
                              precio_unitario=price, costo_unitario=round(price * (1 - m * rng.uniform(0.85, 1.15)), -2)))
        pid += 1
productos = pd.DataFrame(prod_rows)

# Clientes (se crean a medida que llegan)
clientes, ventas = [], []
next_cid, vid = 1, 1
active = []  # (id, region, is_new)
for reg, w in regiones.items():  # base de clientes existente antes de nov-2024
    for _ in range(int(3200 * w)):
        cid = f"C{next_cid:05d}"; next_cid += 1
        fr = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 1000)))
        clientes.append(dict(id_cliente=cid, region=reg, fecha_registro=fr.date(),
                             segmento=rng.choice(["Nuevo", "Frecuente", "Premium"], p=[0.3, 0.5, 0.2])))
        active.append((cid, reg, False))

def month_index(m):
    return (m - months[0]).n

for m in months:
    late = m >= CUT
    t = month_index(m)
    season = 1 + 0.18 * (m.month in (11, 12)) + 0.05 * (m.month == 6)
    # Nuevos clientes por región
    for reg, w in regiones.items():
        n_new = rng.poisson(230 * w * (1 + 0.01 * t) * (0.75 if (late and reg == "Caribe") else 1))
        for _ in range(n_new):
            cid = f"C{next_cid:05d}"; next_cid += 1
            fecha_reg = m.to_timestamp() + pd.Timedelta(days=int(rng.integers(0, 28)))
            clientes.append(dict(id_cliente=cid, region=reg, fecha_registro=fecha_reg.date(),
                                 segmento=rng.choice(["Nuevo", "Frecuente", "Premium"], p=[0.6, 0.3, 0.1])))
            active.append((cid, reg, True))
    # Compras del mes: cada cliente activo compra con cierta prob.
    new_active = []
    for cid, reg, is_new in active:
        p_buy = 0.95 if is_new else 0.30
        p_buy *= 1.06 if m.month in (11, 12) else 1.0
        if late and reg == "Caribe": p_buy *= 0.80
        if rng.random() < p_buy:
            n_items = 1 + rng.poisson(0.4)
            for _ in range(n_items):
                cat = rng.choice(list(categorias), p=[v[0] for v in categorias.values()])
                if late and cat == "Tecnología" and rng.random() < 0.18:
                    cat = rng.choice(["Hogar", "Moda", "Belleza"])  # sustituye compras de tecnología
                    if rng.random() < 0.5:
                        continue  # o se pierde la venta
                pr = productos[productos.categoria == cat].sample(1, random_state=int(rng.integers(1e9))).iloc[0]
                qty = int(1 + rng.poisson(0.3))
                desc = float(rng.choice([0, 0.05, 0.10, 0.15], p=[0.55, 0.2, 0.15, 0.1]))
                base_days = {"Andina": 3, "Caribe": 4, "Pacífico": 4, "Orinoquía": 6, "Bogotá D.C.": 2}[reg]
                days = max(1, int(rng.normal(base_days + (3.5 if late and reg == "Caribe" else 0) + (0.3 if late else 0), 1.2)))
                p_dev = 0.04 + 0.012 * max(0, days - 4) + (0.03 if cat == "Tecnología" else 0)
                fecha = m.to_timestamp() + pd.Timedelta(days=int(rng.integers(0, m.days_in_month)))
                total = round(pr.precio_unitario * qty * (1 - desc), 0)
                ventas.append(dict(id_venta=f"V{vid:06d}", fecha=fecha.date(), id_cliente=cid, id_producto=pr.id_producto,
                                   canal=rng.choice(list(canales), p=list(canales.values())), cantidad=qty,
                                   precio_unitario=pr.precio_unitario, descuento=desc, valor_venta=total,
                                   costo_total=round(pr.costo_unitario * qty, 0), dias_entrega=days,
                                   devuelto="Sí" if rng.random() < p_dev else "No"))
                vid += 1
        # Churn
        churn = 0.07 + (0.04 if (late and reg == "Caribe") else 0)
        if rng.random() > churn:
            new_active.append((cid, reg, False))
    active = new_active

ventas = pd.DataFrame(ventas)
clientes = pd.DataFrame(clientes)

# Metas comerciales mensuales (Excel del área comercial)
tmp = ventas.merge(clientes[["id_cliente", "region"]], on="id_cliente")
tmp["mes"] = pd.to_datetime(tmp.fecha).dt.to_period("M")
base = tmp[tmp.mes < CUT].groupby(["mes", "region"]).valor_venta.sum().unstack()
metas = []
for m in months:
    for reg in regiones:
        ref = base[reg].iloc[-12:].mean() if m >= CUT else base[reg].get(m, base[reg].mean())
        metas.append(dict(mes=str(m), region=reg, meta_ventas=round(ref * (1.08 if m >= CUT else 1.03), -5)))
metas = pd.DataFrame(metas)

# Inyectar "suciedad" para que el ETL tenga sentido (se documenta y se limpia luego)
raw = ventas.copy()
dups = raw.sample(85, random_state=1)
raw = pd.concat([raw, dups]).sort_values("id_venta")
raw.loc[raw.sample(40, random_state=2).index, "canal"] = raw.loc[raw.sample(40, random_state=2).index, "canal"].str.upper()
raw.loc[raw.sample(25, random_state=3).index, "dias_entrega"] = np.nan
raw.to_csv("raw_ventas.csv", index=False)
productos.to_csv("productos.csv", index=False)
clientes.to_csv("clientes.csv", index=False)
metas.to_csv("metas.csv", index=False)
print(len(raw), len(ventas), len(clientes), len(productos))
