import io
import re

import pandas as pd
import plotly.graph_objects as go
import pycountry
import requests
import streamlit as st
import plotly.io as pio
from plotly.subplots import make_subplots

st.set_page_config(page_title="The Real Exchange Ledger", page_icon="💱", layout="wide")

# ---------------------------------------------------------------- look & feel
# Theme: "banknote ledger" - cream paper, engraved-green ink, gold accents, serif type.
INK, GREEN, GOLD, RUST, PAPER = "#1f3a2e", "#2f6b4f", "#b8892b", "#a63d2f", "#f4efe1"

pio.templates["ledger"] = go.layout.Template(layout=dict(
    font=dict(family="Georgia, 'Times New Roman', serif", color=INK),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fbf8ee",
    colorway=[GREEN, GOLD, RUST, "#3b6a8a", "#6b4f7a"],
    xaxis=dict(gridcolor="#e3dcc4", linecolor=INK, zerolinecolor="#e3dcc4"),
    yaxis=dict(gridcolor="#e3dcc4", linecolor=INK, zerolinecolor="#e3dcc4"),
    hoverlabel=dict(bgcolor="#fffdf5", font=dict(family="Georgia, serif", color=INK)),
))
pio.templates.default = "ledger"

st.markdown(f"""
<style>
.stApp {{
  background-color: {PAPER};
  background-image:
    repeating-linear-gradient(45deg, rgba(47,107,79,.045) 0 2px, transparent 2px 14px),
    repeating-linear-gradient(-45deg, rgba(184,137,43,.05) 0 2px, transparent 2px 14px);
}}
.stApp, .stApp p, .stApp label, .stApp li, .stApp span, .stApp div[data-testid="stMarkdownContainer"] {{
  color: {INK}; font-family: Georgia, 'Times New Roman', serif;
}}
h1, h2, h3 {{ font-family: Georgia, 'Times New Roman', serif !important; color: {INK} !important;
  letter-spacing: .3px; }}
h2, h3 {{ border-bottom: 2px double {GOLD}; padding-bottom: 4px; }}
.hero {{
  border: 3px double {GOLD}; border-radius: 6px; padding: 22px 28px; margin-bottom: 18px;
  background: linear-gradient(135deg, {GREEN} 0%, #1f4a37 100%); text-align: center;
  box-shadow: 0 4px 14px rgba(0,0,0,.25), inset 0 0 0 6px rgba(244,239,225,.10);
}}
.hero h1 {{ color: #f4efe1 !important; margin: 0; font-size: 2.3rem; border: 0; }}
.hero .sub {{ color: #e8d9a8 !important; font-style: italic; margin-top: 4px; }}
.hero .formula {{ display: inline-block; margin-top: 12px; padding: 6px 16px; border-radius: 20px;
  background: rgba(244,239,225,.14); color: #f4efe1 !important; font-family: 'Courier New', monospace;
  font-size: .95rem; }}
div[data-testid="stMetric"] {{
  background: #fffdf5; border: 1px solid {GOLD}; border-left: 6px solid {GREEN};
  border-radius: 4px; padding: 10px 14px; box-shadow: 2px 3px 0 rgba(31,58,46,.15);
}}
div[data-testid="stMetricValue"] {{ font-family: 'Courier New', monospace; color: {GREEN}; }}
button[data-baseweb="tab"] {{ font-family: Georgia, serif; font-size: 1.05rem; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {GREEN}; font-weight: 700; }}
div[data-baseweb="tab-highlight"] {{ background-color: {GOLD} !important; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
  background-color: #fffdf5 !important; border-color: {GOLD} !important; }}
div[data-baseweb="select"] *, div[data-baseweb="input"] input {{ color: {INK} !important; }}
.stDownloadButton button {{
  background: {GREEN}; color: #f4efe1 !important; border: 2px solid {GOLD}; border-radius: 4px;
  font-family: Georgia, serif; letter-spacing: .5px;
}}
.stDownloadButton button:hover {{ background: {GOLD}; color: {INK} !important; border-color: {INK}; }}
div[data-testid="stDataFrame"] {{ border: 1px solid {GOLD}; }}
.verdict {{ background: #fffdf5; border: 1px dashed {GREEN}; border-radius: 4px; padding: 12px 16px; }}
footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA"
HEADERS = {"Accept": "text/csv"}
CPI_KEY = "{}.CPI._T.IX.M"
FX_KEY = "{}.XDC_USD.PA_RT.M"

EVENTS = [
    ("1985-09", "Plaza Accord"),
    ("1992-09", "Black Wednesday (ERM crisis)"),
    ("1997-07", "Asian financial crisis"),
    ("1999-01", "Euro launched"),
    ("2008-09", "Lehman collapse"),
    ("2010-05", "Euro-area debt crisis"),
    ("2015-01", "Swiss franc peg removed"),
    ("2016-06", "Brexit referendum"),
    ("2020-03", "COVID-19 pandemic"),
    ("2022-02", "Russia invades Ukraine"),
]


# ---------------------------------------------------------------- data
def get_csv(dataflow, key):
    url = f"{BASE}/{dataflow}/+/{key}"
    r = requests.get(url, headers=HEADERS, params={"c[TIME_PERIOD]": "ge:1976-01"}, timeout=120)
    if r.status_code != 200:
        r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), low_memory=False)


def parse_period(p):
    p = str(p)
    if "-M" in p:
        return pd.to_datetime(p.replace("-M", "-") + "-01", errors="coerce")
    return pd.to_datetime(p, errors="coerce")


def find_col(df, prefix):
    return next(c for c in df.columns if c.upper().startswith(prefix))


def code_of(x):
    return str(x).split(":")[0].split("|")[0].strip()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all(dataflow, key_template):
    """Download the series for every country at once. Returns {ISO: Series}."""
    df = get_csv(dataflow, key_template.format("*"))
    ccol, tcol, vcol = find_col(df, "COUNTRY"), find_col(df, "TIME_PERIOD"), find_col(df, "OBS_VALUE")
    df = pd.DataFrame({"iso": df[ccol].map(code_of),
                       "date": df[tcol].map(parse_period),
                       "value": pd.to_numeric(df[vcol], errors="coerce")}).dropna()
    df = df[df["date"] >= "1976-01-01"]
    return {iso: g.drop_duplicates("date").set_index("date")["value"].sort_index()
            for iso, g in df.groupby("iso")}


def country_name(iso):
    if iso == "G163":
        return "Euro area"
    c = pycountry.countries.get(alpha_3=iso)
    if c:
        return getattr(c, "common_name", None) or c.name
    return {"XKX": "Kosovo", "UVK": "Kosovo"}.get(iso, iso)


def is_country(iso):
    return iso == "G163" or bool(re.fullmatch(r"[A-Z]{3}", iso))


def build_pair(i1, i2):
    df = pd.concat({"P1": CPI[i1], "P2": CPI[i2], "X1_per_USD": FX[i1], "X2_per_USD": FX[i2]},
                   axis=1).dropna()
    df["S"] = df["X2_per_USD"] / df["X1_per_USD"]  # C2 units per 1 C1 unit
    df["RER"] = df["S"] * df["P1"] / df["P2"]
    return df


# ---------------------------------------------------------------- load
st.markdown(
    """
<div class="hero">
  <h1>💱 The Real Exchange Ledger</h1>
  <div class="sub">What is a currency really worth? Prices, not just rates, tell the story.</div>
  <div class="formula">RER(t) = S(t) × P1(t) / P2(t)</div>
</div>
""",
    unsafe_allow_html=True,
)
st.caption(
    "S(t) = units of Country 2 currency per 1 unit of Country 1 currency. "
    "Data: IMF monthly CPI and period-average exchange rates."
)

try:
    with st.spinner("Downloading IMF data..."):
        CPI = fetch_all("CPI", CPI_KEY)
        FX = fetch_all("ER", FX_KEY)
except Exception as e:
    st.error(f"Could not retrieve IMF data: {e}")
    st.stop()

if "USA" in CPI and "USA" not in FX:
    FX["USA"] = pd.Series(1.0, index=CPI["USA"].index)

isos = sorted((i for i in CPI if i in FX and is_country(i)), key=country_name)
if not isos:
    st.error("No countries with both CPI and exchange-rate data were returned by the IMF.")
    st.stop()
label = {i: country_name(i) for i in isos}
names = [label[i] for i in isos]
by_name = {label[i]: i for i in isos}

c1, c2 = st.columns(2)
n1 = c1.selectbox("Country 1", names,
                  index=names.index("United Kingdom") if "United Kingdom" in names else 0)
n2 = c2.selectbox("Country 2", names,
                  index=names.index("United States") if "United States" in names else 1)
if n1 == n2:
    st.warning("Choose two different countries.")
    st.stop()
i1, i2 = by_name[n1], by_name[n2]

df = build_pair(i1, i2)
if df.empty:
    st.error("No overlapping monthly data for this pair.")
    st.stop()

months = list(df.index.to_period("M").to_timestamp())
s_date, e_date = st.select_slider(
    "Sample period", options=months, value=(months[0], months[-1]),
    format_func=lambda d: d.strftime("%Y-%m"),
)
sub = df.loc[s_date:e_date].copy()
rer_star = sub["RER"].mean()
sub["RER_star"] = rer_star
sub["Real_Index"] = 100 * sub["RER"] / rer_star
latest = sub.iloc[-1]
latest_idx = float(latest["Real_Index"])

tab_pair, tab_rank = st.tabs(["Pair analysis", "Rank view"])

# ---------------------------------------------------------------- pair tab
with tab_pair:
    view = st.radio("Chart", ["Real", "Nominal", "Both"], horizontal=True)
    show_events = st.checkbox("Show event markers", value=True)
    cur1, cur2 = f"{n1} currency", f"{n2} currency"

    fig = make_subplots(specs=[[{"secondary_y": view == "Both"}]])
    if view in ("Real", "Both"):
        fig.add_trace(go.Scatter(x=sub.index, y=sub["Real_Index"], name="Real Index (RER*=100)"),
                      secondary_y=False)
    if view in ("Nominal", "Both"):
        fig.add_trace(go.Scatter(x=sub.index, y=sub["S"], name=f"Nominal S ({cur2} per {cur1})",
                                 line=dict(dash="dot")), secondary_y=(view == "Both"))
    if view == "Both":
        fig.update_yaxes(title_text="Real Index", secondary_y=False)
        fig.update_yaxes(title_text=f"S: {cur2} per {cur1}", secondary_y=True)
    elif view == "Real":
        fig.update_yaxes(title_text="Real Index")
    else:
        fig.update_yaxes(title_text=f"S: {cur2} per {cur1}")

    if show_events:
        for k, (d, text) in enumerate(EVENTS):
            dt = pd.Timestamp(d + "-01")
            if sub.index.min() <= dt <= sub.index.max():
                fig.add_shape(type="line", x0=dt, x1=dt, y0=0, y1=1, xref="x", yref="paper",
                              line=dict(color="gray", width=1, dash="dash"))
                fig.add_annotation(x=dt, y=1 - 0.07 * (k % 4), xref="x", yref="paper",
                                   text=text, showarrow=False, textangle=-90 if False else 0,
                                   xanchor="left", font=dict(size=10, color="gray"))
    fig.update_layout(hovermode="x unified", height=520, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("RER* (average RER)", f"{rer_star:,.4f}")
    m2.metric("Valid months", len(sub))
    m3.metric("Mean of Real Index", f"{sub['Real_Index'].mean():.4f}")

    # ---- gauge
    st.subheader("Over/undervalued gauge")
    gap = latest_idx - 100
    lo, hi = min(50, latest_idx - 10), max(150, latest_idx + 10)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=latest_idx,
        delta={"reference": 100, "valueformat": ".1f"},
        title={"text": f"Real Index, {latest.name:%b %Y}"},
        gauge={
            "axis": {"range": [lo, hi]},
            "bar": {"color": "black"},
            "steps": [
                {"range": [lo, 90], "color": "#b9cfdc"},
                {"range": [90, 110], "color": "#bcd8c4"},
                {"range": [110, hi], "color": "#e8c48a"},
            ],
            "threshold": {"line": {"color": RUST, "width": 4}, "value": 100},
        }))
    gauge.update_layout(height=320, margin=dict(t=60, b=10))
    g1, g2 = st.columns([1, 1])
    g1.plotly_chart(gauge, use_container_width=True)
    if gap > 1:
        verdict = (f"The {n1} currency is **{gap:.1f}% stronger in real terms** than its average "
                   f"against the {n2} currency over this sample: {n1} looks relatively expensive.")
    elif gap < -1:
        verdict = (f"The {n1} currency is **{-gap:.1f}% weaker in real terms** than its average "
                   f"against the {n2} currency over this sample: {n1} looks relatively cheap.")
    else:
        verdict = f"The real exchange rate is close to its sample average (within 1%)."
    g2.markdown(f'<div class="verdict">{verdict}</div>', unsafe_allow_html=True)
    g2.caption("Blue: below 90 · Green: 90–110 · Orange: above 110. "
               "'Over/undervalued' is relative to the sample average RER*, not a measure of true "
               "equilibrium: changing the dates changes the benchmark.")

    # ---- iPhone comparison
    st.subheader("What does an iPhone cost?")
    price1 = st.number_input(f"iPhone price in {n1} currency (illustrative, enter your own)",
                             min_value=1.0, value=999.0, step=10.0)
    s_now = float(latest["S"])
    s_fair = float(rer_star * latest["P2"] / latest["P1"])  # S that would give RER = RER*
    cost_now = price1 * s_now
    cost_fair = price1 * s_fair
    diff = (cost_now / cost_fair - 1) * 100
    note = (f"{abs(diff):.1f}% {'more' if diff > 0 else 'less'} than at the average real rate"
            if abs(diff) >= 0.05 else "the same as at the average real rate")
    st.markdown(
        f"""
<div style="display:flex;justify-content:center;">
 <div style="width:260px;border:10px solid #1c1c1e;border-radius:42px;background:#fffdf5;outline:3px solid #b8892b;
             padding:34px 18px 28px 18px;text-align:center;box-shadow:0 6px 18px rgba(0,0,0,.3);
             color:#111;font-family:-apple-system,Helvetica,Arial,sans-serif;">
  <div style="width:80px;height:20px;background:#1c1c1e;border-radius:12px;margin:-22px auto 18px;"></div>
  <div style="font-size:42px;">📱</div>
  <div style="font-size:13px;color:#555;">A phone priced at</div>
  <div style="font-size:20px;font-weight:600;">{price1:,.0f} ({n1})</div>
  <hr style="border:0;border-top:1px solid #ccc;margin:12px 0;">
  <div style="font-size:13px;color:#555;">costs in {n2} at today's rate</div>
  <div style="font-size:26px;font-weight:700;">{cost_now:,.2f}</div>
  <div style="font-size:13px;color:#555;margin-top:10px;">at the sample-average real rate</div>
  <div style="font-size:20px;font-weight:600;">{cost_fair:,.2f}</div>
  <div style="margin-top:12px;font-size:13px;font-weight:600;color:{'#c0392b' if diff > 0 else '#1e8449'};">
   {note}</div>
 </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption(f"Amounts are in {n2} currency units, as of {latest.name:%b %Y}. The same phone price "
               f"is assumed in {n1} currency; this illustrates the RER, not actual Apple pricing.")

    # ---- table + CSV
    out = sub.reset_index().rename(columns={"index": "date"})
    out["date"] = out["date"].dt.strftime("%Y-%m")
    out = out.rename(columns={
        "P1": f"CPI_{n1}", "P2": f"CPI_{n2}",
        "X1_per_USD": f"{n1}_LCU_per_USD", "X2_per_USD": f"{n2}_LCU_per_USD",
        "S": "S_C2_per_C1"})
    st.dataframe(out, use_container_width=True)
    st.download_button("Download CSV", out.to_csv(index=False).encode(),
                       file_name="rer_data.csv", mime="text/csv")

# ---------------------------------------------------------------- rank tab
with tab_rank:
    st.markdown(
        f"Each bar compares **{n1}** with one other country: the latest Real Index in the selected "
        f"sample ({s_date:%Y-%m} to {e_date:%Y-%m}), where the sample-average real rate for that pair "
        f"= 100. Above 100 means the {n1} currency is stronger in real terms than its average "
        f"against that country; below 100 means weaker."
    )
    rows = []
    for j in isos:
        if j == i1:
            continue
        d = build_pair(i1, j).loc[s_date:e_date]
        if len(d) < 12:
            continue
        rows.append({"Country": label[j], "Real Index (latest)": 100 * d["RER"].iloc[-1] / d["RER"].mean(),
                     "Latest month": d.index[-1].strftime("%Y-%m"), "Valid months": len(d)})
    if not rows:
        st.info("Not enough overlapping data in this sample period to rank countries.")
    else:
        rk = pd.DataFrame(rows).sort_values("Real Index (latest)", ascending=False).reset_index(drop=True)
        rk.index = rk.index + 1
        top_n = st.slider("Countries to show in chart", 5, min(60, len(rk)), min(20, len(rk)))
        order = st.radio("Show", ["Highest (strongest vs them)", "Lowest (weakest vs them)"], horizontal=True)
        chart_df = rk.head(top_n) if order.startswith("Highest") else rk.tail(top_n).iloc[::-1]
        colors = [GOLD if v > 100 else GREEN for v in chart_df["Real Index (latest)"]]
        bar = go.Figure(go.Bar(x=chart_df["Real Index (latest)"], y=chart_df["Country"],
                               orientation="h", marker_color=colors))
        bar.add_vline(x=100, line_dash="dash", line_color="black")
        bar.update_layout(height=max(350, 24 * top_n), yaxis=dict(autorange="reversed"),
                          xaxis_title="Real Index (pair average = 100)", margin=dict(l=10, r=10))
        st.plotly_chart(bar, use_container_width=True)
        st.dataframe(rk, use_container_width=True)
        st.download_button("Download ranking CSV", rk.to_csv().encode(),
                           file_name="rer_ranking.csv", mime="text/csv")
