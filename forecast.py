"""
MedSupply Uganda - weekly demand forecasting.

    python forecast.py          # trains the model, prints accuracy, saves demand_model.joblib

In app.py:
    from forecast import render_forecast_tab
    ...inside the Inventory page, add a tab and call:
    render_forecast_tab(st, db, ugx, **FULL)

The model uses LightGBM if installed (pip install lightgbm), otherwise falls
back to scikit-learn's HistGradientBoostingRegressor (same idea, slightly slower).
"""
import datetime as dt
import json
import os

import joblib
import numpy as np
import pandas as pd

MODEL_FILE = os.environ.get("MEDSUPPLY_MODEL", "demand_model.joblib")
FEATS = ["lag1", "lag2", "lag3", "lag4", "roll4", "roll8",
         "woy_sin", "woy_cos", "item_code", "price"]

try:
    from lightgbm import LGBMRegressor

    def make_model():  # L1 loss: bulk-order spikes should not drag the forecast up
        return LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=10,
                             subsample=0.8, subsample_freq=1, colsample_bytree=0.8, objective="l1", random_state=42, verbose=-1)
except ImportError:
    from sklearn.ensemble import HistGradientBoostingRegressor

    def make_model():
        return HistGradientBoostingRegressor(loss="absolute_error", max_iter=200, learning_rate=0.03, max_leaf_nodes=8,
                                             min_samples_leaf=30, random_state=42)


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
def monday(d):
    d = pd.Timestamp(d).normalize()
    return d - pd.Timedelta(days=d.weekday())


# base weekly boxes across all outlets, and how strongly rainy-season (malaria/diarrhoea) peaks lift demand
ITEM_PARAMS = {"INV-001": (28, .15), "INV-002": (35, .10), "INV-003": (20, .60), "INV-004": (15, .10),
               "INV-005": (30, .05), "INV-006": (18, .00), "INV-007": (22, .40), "INV-008": (8, .10)}


def synthetic_history(prices, end=None, weeks=104, seed=42):
    """SIMULATED order history: trend + two rainy-season peaks (Mar-May, Sep-Nov) + noise + occasional bulk orders."""
    rng = np.random.default_rng(seed)
    # exclusive: last week is end - 7 days
    end = monday(end or dt.date.today())
    wk = pd.date_range(end - pd.Timedelta(weeks=weeks),
                       periods=weeks, freq="7D")
    rows = []
    for iid, price in prices.items():
        base, amp = ITEM_PARAMS.get(iid, (15, .10))
        woy = wk.isocalendar().week.to_numpy().astype(float)
        season = (np.cos(4 * np.pi * (woy - 16) / 52) + 1) / \
            2        # peaks near weeks 16 and 42
        mean = base * (1 + amp * (2 * season - 1)) * \
            (1 + 0.003 * np.arange(weeks))
        qty = rng.poisson(mean) * np.where(rng.random(weeks) < .04, 3, 1)
        rows += [{"week": w, "item_id": iid,
                  "qty": float(q), "price": float(price)} for w, q in zip(wk, qty)]
    return pd.DataFrame(rows)


def weekly_from_orders(orders, prices):
    """Real orders (the app's db['orders']) -> weekly boxes per product."""
    rows = []
    for _, o in orders[orders["Status"] != "Cancelled"].iterrows():
        wk = monday(o["Date"])
        for l in json.loads(o["Items"]):
            rows.append(
                {"week": wk, "item_id": l["id"], "qty": float(l["qty"])})
    if not rows:
        return pd.DataFrame(columns=["week", "item_id", "qty", "price"])
    d = pd.DataFrame(rows).groupby(
        ["week", "item_id"], as_index=False)["qty"].sum()
    d["price"] = d["item_id"].map(prices)
    return d


def fill_weeks(h, prices, end):
    """Make every product have a row for every week up to (not including) `end`; missing weeks = 0 sales."""
    end = monday(end)
    out = []
    for iid, g in h.groupby("item_id"):
        idx = pd.date_range(g["week"].min(), end -
                            pd.Timedelta(weeks=1), freq="7D")
        s = g.set_index("week")["qty"].reindex(idx, fill_value=0.0)
        out.append(pd.DataFrame({"week": idx, "item_id": iid, "qty": s.values, "price": float(
            prices.get(iid, g["price"].iloc[-1]))}))
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------
# Features, training, forecasting
# ----------------------------------------------------------------------
def add_features(w):
    w = w.sort_values(["item_id", "week"]).reset_index(drop=True)
    g = w.groupby("item_id")["qty"]
    for k in (1, 2, 3, 4):
        w[f"lag{k}"] = g.shift(k)
    prev = g.shift(1)
    w["roll4"] = prev.groupby(w["item_id"]).transform(
        lambda x: x.rolling(4, min_periods=1).mean())
    w["roll8"] = prev.groupby(w["item_id"]).transform(
        lambda x: x.rolling(8, min_periods=1).mean())
    woy = w["week"].dt.isocalendar().week.astype(int)
    w["woy_sin"], w["woy_cos"] = np.sin(
        2 * np.pi * woy / 52), np.cos(2 * np.pi * woy / 52)
    w["item_code"] = w["item_id"].str[-3:].astype(int)
    return w


def wape(y, p):
    return float(np.abs(y - p).sum() / max(np.abs(y).sum(), 1e-9))


def train(prices, test_weeks=13, verbose=True):
    f = add_features(synthetic_history(prices)).dropna(subset=["lag4"])
    cut = f["week"].max() - pd.Timedelta(weeks=test_weeks - 1)
    tr, te = f[f["week"] < cut], f[f["week"] >= cut]
    m = make_model().fit(tr[FEATS], tr["qty"])
    if verbose:
        p = m.predict(te[FEATS])
        print(
            f"Time-based test on the last {test_weeks} weeks (never seen in training):")
        print(
            f"  Moving-average baseline  MAE {np.abs(te['qty'] - te['roll4']).mean():5.2f} boxes   WAPE {wape(te['qty'], te['roll4']):.1%}")
        print(
            f"  Naive last-week          MAE {np.abs(te['qty'] - te['lag1']).mean():5.2f} boxes   WAPE {wape(te['qty'], te['lag1']):.1%}")
        print(
            f"  Gradient boosting        MAE {np.abs(te['qty'] - p).mean():5.2f} boxes   WAPE {wape(te['qty'], p):.1%}")
    full = f  # refit on everything for deployment
    m = make_model().fit(full[FEATS], full["qty"])
    joblib.dump({"model": m, "feats": FEATS}, MODEL_FILE)
    return m


def load_bundle():
    return joblib.load(MODEL_FILE) if os.path.exists(MODEL_FILE) else None


def forecast(bundle, history, prices, weeks=4, today=None):
    """Recursive multi-week forecast. `history` = weekly rows up to the last full week."""
    start = monday(today or dt.date.today())
    h = fill_weeks(history[history["week"] < start], prices, start)
    out = []
    for k in range(weeks):
        wk = start + pd.Timedelta(weeks=k)
        new = pd.DataFrame({"week": wk, "item_id": list(
            prices), "qty": np.nan, "price": [float(p) for p in prices.values()]})
        f = add_features(pd.concat([h, new], ignore_index=True))
        nf = f[f["week"] == wk].copy()
        nf["qty"] = np.clip(bundle["model"].predict(
            nf[bundle["feats"]]), 0, None)
        out.append(nf[["week", "item_id", "qty"]].rename(
            columns={"qty": "forecast"}))
        h = pd.concat([h, nf[["week", "item_id", "qty"]].assign(
            price=nf["item_id"].map(prices).values)], ignore_index=True)
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------
# Streamlit tab
# ----------------------------------------------------------------------
def render_forecast_tab(st, db, ugx, **full):
    inv = db["inventory"]
    prices = dict(zip(inv["Item ID"], inv["Unit Price (UGX)"].astype(float)))
    bundle = load_bundle()
    # first visit: train now (a few seconds) and cache the file for next time
    if bundle is None:
        with st.spinner("Training the demand model for the first time..."):
            train(prices, verbose=False)
        bundle = load_bundle()
    this_week = monday(dt.date.today())
    real = weekly_from_orders(db["orders"], prices)
    span = (this_week - real["week"].min()).days // 7 if len(real) else 0
    if span >= 8:
        hist, note = real, "Forecast uses your real order history."
    else:
        hist = synthetic_history(prices, end=this_week)
        note = f"Demo mode: only {span} week(s) of real orders so far, so the forecast uses simulated history. It switches to real data after 8 weeks."
    st.caption(note)
    fc = forecast(bundle, hist, prices, weeks=4)
    need = fc.groupby("item_id")["forecast"].sum()
    rows = []
    for _, r in inv.iterrows():
        n4, stock, lvl = float(need.get(r["Item ID"], 0)), int(
            r["Stock Quantity"]), int(r["Reorder Level"])
        wk_avg = n4 / 4 if n4 > 0 else 0
        cover = stock / wk_avg if wk_avg > 0 else 99
        rows.append({"Product": r["Product Name"], "In stock": stock, "Forecast next 4 wks": round(n4),
                     "Weeks of cover": round(min(cover, 99), 1),
                     "Suggested reorder (boxes)": max(0, int(np.ceil(n4 + lvl - stock))),
                     "Risk": "Stockout soon" if cover < 2 else "Watch" if cover < 4 else "OK"})
    df = pd.DataFrame(rows).sort_values("Weeks of cover")
    st.dataframe(df, hide_index=True, **full)
    pick = st.selectbox("Show history and forecast for",
                        inv["Product Name"], key="fc_pick")
    iid = inv.loc[inv["Product Name"] == pick, "Item ID"].iloc[0]
    past = fill_weeks(hist, prices, this_week)
    past = past[past["item_id"] == iid].tail(26).set_index("week")[
        "qty"].rename("Actual")
    nxt = fc[fc["item_id"] == iid].set_index(
        "week")["forecast"].rename("Forecast")
    st.line_chart(pd.concat([past, nxt], axis=1), color=[
                  "#0E6B63", "#F2B600"], height=260)


if __name__ == "__main__":
    ids = list(ITEM_PARAMS)
    train({i: 20000.0 for i in ids})
    print(f"Saved {MODEL_FILE}")
