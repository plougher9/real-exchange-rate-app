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
/* Expander: leave Streamlit's own layout alone. */
div[data-testid="stExpander"] summary {{
  padding-top: 8px;
  padding-bottom: 8px;
}}
footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

BASE = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA"
HEADERS = {"Accept": "text/csv"}
CPI_KEY = "{}.CPI._T.IX.M"
FX_KEY = "{}.XDC_USD.PA_RT.M"

EVENTS = [
    ("1985-09", "Plaza Accord",
     "The G5 agreed to let the US dollar fall after its sharp rise in the early 1980s.",
     "The dollar depreciated through 1985-87, a real depreciation for the US against the "
     "yen, mark and pound."),
    ("1992-09", "Black Wednesday (ERM crisis)",
     "Britain was forced out of the European Exchange Rate Mechanism after failing to keep "
     "sterling above its floor.",
     "Sterling fell sharply and the UK's Real Index dropped well below 100 within months."),
    ("1997-07", "Asian financial crisis",
     "The Thai baht peg broke and the crisis spread through East Asia.",
     "Currencies across the region collapsed in nominal terms; real rates moved with them."),
    ("1999-01", "Euro launched",
     "Eleven currencies were locked together at fixed conversion rates and the euro appeared "
     "for electronic payments.",
     "Nominal volatility between members vanished; real rates within the euro area can no "
     "longer adjust through the exchange rate."),
    ("2008-09", "Lehman collapse",
     "The bankruptcy of Lehman Brothers turned a credit crunch into a global financial crisis.",
     "A flight to safe-haven currencies, especially the US dollar, drove large real swings."),
    ("2010-05", "Euro-area debt crisis",
     "Greece's bailout exposed fiscal weakness across the euro periphery.",
     "The euro fell against the dollar; periphery members lost real competitiveness within "
     "the currency union."),
    ("2015-01", "Swiss franc peg removed",
     "The Swiss National Bank abandoned its 1.20 floor against the euro without warning.",
     "The franc jumped about 20% in minutes; a stark reminder that pegs are not permanent."),
    ("2016-06", "Brexit referendum",
     "The UK voted to leave the European Union.",
     "Sterling fell sharply, a nominal depreciation that fed straight into the UK's real rate."),
    ("2020-03", "COVID-19 pandemic",
     "Global lockdowns and a scramble for dollars.",
     "Emergency policy support, sharp inflation differences, and a strong dollar through 2022."),
    ("2022-02", "Russia invades Ukraine",
     "War in Europe and an energy shock.",
     "European currencies weakened in real terms as energy import costs surged."),
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
  <div class="sub">Struck from IMF data: prices, rates, and the real value between them.</div>
  <div class="formula">An application of RER by Patrick Loughery</div>
</div>
""",
    unsafe_allow_html=True,
)
st.caption(
    "S(t) = units of Country 2 currency per 1 unit of Country 1 currency, so "
    "RER(t) = S(t) × P1(t) / P2(t). Data: IMF monthly CPI and period-average exchange rates."
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

import random

# Country 2's view of the same real exchange rate is the inverse: 1/RER(t).
inv = 1 / sub["RER"]
sub["Real_Index_C2"] = 100 * inv / inv.mean()
latest = sub.iloc[-1]
latest_idx2 = float(latest["Real_Index_C2"])

tab_pair, tab_rank = st.tabs(["Pair analysis", "Rank view"])

# ---------------------------------------------------------------- pair tab
with tab_pair:
    view = st.radio(
        "Chart view",
        ["Real index (RER* = 100)", "Nominal exchange rate S(t)", "Both (separate axes)"],
        horizontal=True,
        help="Real index: 100 x RER(t) / RER*, rescaled to average 100 over your sample. "
             "Nominal: S(t) in actual currency units, not rescaled. "
             "Both: the real index on the left axis and S(t) on the right.")
    if view.startswith("Real") or view.startswith("Both"):
        persp = st.radio(
            "Show the real index for",
            [f"{n1} (the RER series)", f"{n2} (mirror image)", "Both currencies"],
            horizontal=True,
            help=f"{n2}'s index is the mirror image of {n1}'s: it is built from 1/RER(t) and rescaled "
                 f"so its own average is 100. When {n1} looks overvalued, {n2} looks undervalued.")
    else:
        persp = f"{n1}"
    show_events = st.checkbox("Show event markers", value=True)
    cur1, cur2 = f"{n1} currency", f"{n2} currency"

    both_mode = view.startswith("Both")
    fig = make_subplots(specs=[[{"secondary_y": both_mode}]])
    if view.startswith("Real") or view.startswith("Both"):
        if persp.startswith(f"{n1}") or persp == "Both currencies":
            fig.add_trace(go.Scatter(x=sub.index, y=sub["Real_Index"],
                                     name=f"{n1} real index (vs {n2})", line=dict(width=2.5)),
                          secondary_y=False)
        if persp.startswith(f"{n2}") or persp == "Both currencies":
            fig.add_trace(go.Scatter(x=sub.index, y=sub["Real_Index_C2"],
                                     name=f"{n2} real index (vs {n1})", line=dict(width=2.5, color=RUST)),
                          secondary_y=False)
        # clearly defined 100 reference line
        fig.add_hline(y=100, line=dict(color="black", width=3), secondary_y=False,
                      annotation_text="100 = sample average (fair-value benchmark)",
                      annotation_position="bottom right",
                      annotation_font=dict(size=12, color="black"))
        fig.add_hrect(y0=90, y1=110, fillcolor=GREEN, opacity=0.07, line_width=0, secondary_y=False)
    if view.startswith("Nominal") or both_mode:
        fig.add_trace(go.Scatter(x=sub.index, y=sub["S"], name=f"Nominal S — {cur2} per 1 {cur1}",
                                 line=dict(dash="dot", color=GOLD)), secondary_y=both_mode)
    real_axis = f"Real index of {n1} currency<br>(sample average = 100, rescaled)"
    nom_axis = f"Nominal S(t)<br>({cur2} per 1 {cur1}, actual units)"
    if both_mode:
        fig.update_yaxes(title_text=real_axis, secondary_y=False)
        fig.update_yaxes(title_text=nom_axis, secondary_y=True)
    elif view.startswith("Real"):
        fig.update_yaxes(title_text=real_axis)
    else:
        fig.update_yaxes(title_text=nom_axis)

    fig.update_xaxes(title_text="Month")
    fig.update_layout(
        title=dict(
            text=(f"<b>{n1} vs {n2}</b> — {sub.index.min():%b %Y} to {sub.index.max():%b %Y}"
                  f"<br><sup>RER(t) = S(t) x P1(t) / P2(t) &nbsp;|&nbsp; RER* = {rer_star:,.4f}"
                  f" &nbsp;|&nbsp; Real index = 100 x RER(t) / RER*</sup>"),
            x=0.5, xanchor="center", font=dict(size=15)),
        margin=dict(t=90, b=40))

    if show_events:
        for k, (d, title, what, impact) in enumerate(EVENTS):
            dt = pd.Timestamp(d + "-01")
            if sub.index.min() <= dt <= sub.index.max():
                fig.add_shape(type="line", x0=dt, x1=dt, y0=0, y1=1, xref="x", yref="paper",
                              line=dict(color="gray", width=1, dash="dash"))
                fig.add_annotation(x=dt, y=1 - 0.07 * (k % 4), xref="x", yref="paper",
                                   text=title, showarrow=False, xanchor="left",
                                   font=dict(size=10, color="gray"))

    fig.update_layout(hovermode="x unified", height=520, legend=dict(orientation="h"),
                      margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

    # ---- event notes for the sample, opened on demand
    if show_events:
        shown = [(d, t, w, i) for d, t, w, i in EVENTS
                 if sub.index.min() <= pd.Timestamp(d + "-01") <= sub.index.max()]
        if shown:
            show_notes = st.checkbox(f"Show event notes for this sample ({len(shown)} events)")
            if show_notes:
                for d, t, w, i in shown:
                    st.markdown(f"**{t}** — {pd.Timestamp(d + '-01'):%B %Y}")
                    st.markdown(f"*What happened.* {w}")
                    st.markdown(f"*Effect on the real exchange rate.* {i}")
                    st.divider()

    m1, m2, m3 = st.columns(3)
    m1.metric("RER* (average RER)", f"{rer_star:,.4f}")
    m2.metric("Valid months", len(sub))
    m3.metric("Mean of Real Index", f"{sub['Real_Index'].mean():.4f}")

    # ---- gauge
    st.subheader("Over/undervalued gauge")
    gap1 = latest_idx - 100
    gap2 = latest_idx2 - 100

    def word(g):
        return "OVERVALUED" if g > 1 else ("UNDERVALUED" if g < -1 else "about FAIRLY valued")

    lo, hi = min(50, latest_idx - 10), max(150, latest_idx + 10)
    gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=latest_idx,
        delta={"reference": 100, "valueformat": ".1f"},
        title={"text": f"{n1} currency vs {n2} currency<br>"
                       f"<span style='font-size:0.7em'>Real Index, {latest.name:%b %Y}</span>"},
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
    gauge.update_layout(height=340, margin=dict(t=90, b=10))
    g1, g2 = st.columns([1, 1])
    g1.plotly_chart(gauge, use_container_width=True)
    verdict = (
        f"<b>{n1} currency: {word(gap1)}</b> ({gap1:+.1f}% vs its sample average against {n2}).<br>"
        f"<b>{n2} currency: {word(gap2)}</b> ({gap2:+.1f}% vs its sample average against {n1}).<br><br>"
        f"<i>Overvalued</i> means the currency buys more goods abroad than usual (real appreciation); "
        f"<i>undervalued</i> means it buys less. The two currencies are mirror images, so one is "
        f"overvalued exactly when the other is undervalued."
    )
    g2.markdown(f'<div class="verdict">{verdict}</div>', unsafe_allow_html=True)
    g2.caption("Gauge colours: blue below 90 · green 90–110 · orange above 110. "
               "'Over/undervalued' is relative to the sample average RER*, not a measure of true "
               "equilibrium: changing the dates changes the benchmark.")

    # ---- iPhone call
    st.subheader("📞 Incoming call: an iPhone offer")
    s_now = float(latest["S"])
    s_fair = float(rer_star * latest["P2"] / latest["P1"])  # S that would give RER = RER*

    if "call_state" not in st.session_state:
        st.session_state.call_state = "ringing"
    if "offer" not in st.session_state:
        st.session_state.offer = random.choice(range(500, 1501, 50))

    st.markdown("""
<style>
@keyframes ring { 0%,100%{transform:rotate(0)} 10%,30%,50%{transform:rotate(-4deg)}
                  20%,40%,60%{transform:rotate(4deg)} 70%{transform:rotate(0)} }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(46,204,113,.7)} 100%{box-shadow:0 0 0 22px rgba(46,204,113,0)} }
.phone { width:270px; margin:0 auto; border:10px solid #1c1c1e; border-radius:44px; outline:3px solid #b8892b;
  padding:34px 18px 26px; text-align:center; box-shadow:0 6px 18px rgba(0,0,0,.35);
  font-family:-apple-system,Helvetica,Arial,sans-serif; }
.phone.ring { background:linear-gradient(180deg,#2c3e50,#111); color:#fff; animation:ring 1.2s infinite; }
.phone.live { background:#fffdf5; color:#111; }
.notch { width:80px; height:20px; background:#1c1c1e; border-radius:12px; margin:-22px auto 16px; }
.avatar { width:74px; height:74px; border-radius:50%; background:#8e8e93; margin:8px auto; font-size:40px;
  line-height:74px; animation:pulse 1.3s infinite; }
.verdictbox { background:#fffdf5; border:1px solid #b8892b; border-left:8px solid #2f6b4f;
  border-radius:4px; padding:14px 18px; margin-top:14px; box-shadow:2px 3px 0 rgba(31,58,46,.15); }
.vtag { display:inline-block; padding:3px 12px; border-radius:12px; font-weight:700;
  font-size:.85rem; letter-spacing:.5px; margin-bottom:8px; }
.vbad { background:#a63d2f; color:#fffdf5; }
.vgood { background:#2f6b4f; color:#fffdf5; }
.vflat { background:#b8892b; color:#2b2110; }
</style>
""", unsafe_allow_html=True)

    if st.session_state.call_state == "ringing":
        st.markdown(
            """
<div class="phone ring"><div class="notch"></div>
  <div style="font-size:13px;opacity:.7;">incoming call…</div>
  <div class="avatar">🍎</div>
  <div style="font-size:24px;font-weight:600;">iPhone Dealer</div>
  <div style="font-size:13px;opacity:.7;margin-top:4px;">I have an offer for you</div>
</div>""", unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        if b2.button("📞 Answer", use_container_width=True, type="primary"):
            st.session_state.call_state = "answered"
            st.rerun()
        if b3.button("❌ Decline", use_container_width=True):
            st.session_state.offer = random.choice(range(500, 1501, 50))
            st.toast("Declined. The dealer will call back with another offer!")
    else:
        st.markdown(
            f"""
<div class="phone live"><div class="notch"></div>
  <div style="font-size:12px;color:#34c759;font-weight:600;">● Call connected</div>
  <div style="font-size:15px;margin-top:6px;">“I'll sell you an iPhone for</div>
  <div style="font-size:30px;font-weight:700;">{st.session_state.offer:,.0f}</div>
  <div style="font-size:13px;color:#555;">in {n1} currency (base currency)”</div>
</div>""", unsafe_allow_html=True)
        st.write("")
        o1, o2 = st.columns([2, 1])
        offer = o1.slider(f"Offer price in {n1} currency (base)", 100, 3000,
                          int(st.session_state.offer), step=10)
        if o2.button("📵 Hang up / new call", use_container_width=True):
            st.session_state.call_state = "ringing"
            st.session_state.offer = random.choice(range(500, 1501, 50))
            st.rerun()

        # Who holds the base currency? Flips the direction of the verdict.
        buyer = st.radio(
            "Who is doing the buying?", [f"I hold {n1} currency", f"I hold {n2} currency"],
            horizontal=True,
            help=f"The offer is priced in {n1} currency. Pick which currency you are spending to "
                 f"decide whether the current exchange rate works in your favour.")

        cost_now = offer * s_now
        cost_fair = offer * s_fair
        diff = (cost_now / cost_fair - 1) * 100
        c_a, c_b, c_c = st.columns(3)
        c_a.metric(f"Offer in {n1} currency", f"{offer:,.0f}")
        c_b.metric(f"Cost in {n2} currency (today's rate)", f"{cost_now:,.2f}")
        c_c.metric(f"Cost in {n2} currency (avg real rate)", f"{cost_fair:,.2f}",
                   delta=f"{diff:+.1f}% today vs average", delta_color="inverse")

        # The same number reads in opposite directions depending on who is buying.
        holds_c1 = buyer == f"I hold {n1} currency"
        gap_for_buyer = diff if holds_c1 else -diff
        if abs(diff) < 1:
            tag, cls = "NO CLEAR SIGNAL", "vflat"
            line = (f"The real rate is within 1% of its sample average, so converting now is neither "
                    f"unusually good nor unusually bad.")
        elif holds_c1:
            if gap_for_buyer < 0:
                tag, cls = "BAD MOMENT TO CONVERT", "vbad"
            else:
                tag, cls = "GOOD MOMENT TO CONVERT", "vgood"
            line = (f"Holding {n1} currency and buying {n2} currency, your money buys "
                    f"<b>{abs(gap_for_buyer):.1f}% {'less' if gap_for_buyer < 0 else 'more'}</b> "
                    f"in {n2} than it usually does over this sample.")
        else:
            # Holding Country 2 currency: a LOWER cost than average is the good outcome.
            if diff < 0:
                tag, cls = "GOOD MOMENT", "vgood"
            else:
                tag, cls = "BAD MOMENT", "vbad"
            line = (f"Holding {n2} currency, this {n1} priced item costs you "
                    f"<b>{abs(diff):.1f}% {'less' if diff < 0 else 'more'}</b> "
                    f"than usual over this sample.")

        st.markdown(
            f"""<div class="verdictbox">
<span class="vtag {cls}">{tag}</span><br>
{line}<br><br>
<b>Buying power check:</b> {offer:,.0f} {n1} buys <b>{cost_now:,.2f} {n2}</b> today, against a
sample-average {cost_fair:,.2f} {n2} ({diff:+.1f}%).<br>
<span style="font-size:.85rem;opacity:.8;">This compares today's price with the average over your
selected sample ({s_date:%Y-%m} to {e_date:%Y-%m}), not with an equilibrium value, and it does not
predict future moves. Change the sample dates and this figure changes.</span>
</div>""",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Converted with S = {s_now:,.4f} {n2} per {n1} (latest month, {latest.name:%b %Y}). "
            f"The 'average real rate' is the exchange rate that would make the RER equal its sample "
            f"average, S = {s_fair:,.4f}. Prices are illustrative, not actual Apple pricing.")

# ---- table + CSV
    out = sub.reset_index().rename(columns={"index": "date"})
    out["date"] = out["date"].dt.strftime("%Y-%m")
    out = out.rename(columns={
        "P1": f"CPI_{n1}", "P2": f"CPI_{n2}",
        "X1_per_USD": f"{n1}_LCU_per_USD", "X2_per_USD": f"{n2}_LCU_per_USD",
        "S": "S_C2_per_C1", "Real_Index": f"Real_Index_{n1}", "Real_Index_C2": f"Real_Index_{n2}"})
    st.dataframe(out, use_container_width=True)
    st.download_button("Download CSV", out.to_csv(index=False).encode(),
                       file_name="rer_data.csv", mime="text/csv")

# ---------------------------------------------------------------- rank tab
with tab_rank:
    st.markdown(
        f"Each bar compares the **{n1} currency** with one other country, using the latest month in "
        f"the selected sample ({s_date:%Y-%m} to {e_date:%Y-%m}). The pair's own sample-average "
        f"real rate is set to 100, and the label on each bar is the **% overvalued (+) or "
        f"undervalued (−)** versus that average."
    )
    st.info(
        f"**Most overvalued:** the {n1} currency is furthest ABOVE its own average real rate against "
        f"that country. It is unusually strong in real terms there (goods in that country look cheap "
        f"to {n1} buyers).\n\n"
        f"**Most undervalued:** the {n1} currency is furthest BELOW its own average real rate against "
        f"that country. It is unusually weak in real terms there (goods in that country look "
        f"expensive to {n1} buyers)."
    )
    rows = []
    for j in isos:
        if j == i1:
            continue
        d = build_pair(i1, j).loc[s_date:e_date]
        if len(d) < 12:
            continue
        idx = 100 * d["RER"].iloc[-1] / d["RER"].mean()
        rows.append({"Country": label[j], "Real Index (latest)": idx,
                     "% over/(under)valued": idx - 100,
                     "Latest month": d.index[-1].strftime("%Y-%m"), "Valid months": len(d)})
    if not rows:
        st.info("Not enough overlapping data in this sample period to rank countries.")
    else:
        rk = pd.DataFrame(rows).sort_values("Real Index (latest)", ascending=False).reset_index(drop=True)
        rk.index = rk.index + 1
        top_n = st.slider("Countries to show in chart", 5, min(60, len(rk)), min(20, len(rk)))
        order = st.radio("Show", [f"Most overvalued ({n1} strongest)", f"Most undervalued ({n1} weakest)"],
                         horizontal=True)
        chart_df = rk.head(top_n) if order.startswith("Most overvalued") else rk.tail(top_n).iloc[::-1]
        colors = [GOLD if v > 100 else GREEN for v in chart_df["Real Index (latest)"]]
        bar = go.Figure(go.Bar(
            x=chart_df["Real Index (latest)"], y=chart_df["Country"], orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in chart_df["% over/(under)valued"]],
            textposition="outside", cliponaxis=False,
            hovertemplate="%{y}<br>Real Index %{x:.1f}<br>%{text}<extra></extra>"))
        bar.add_vline(x=100, line=dict(color="black", width=3),
                      annotation_text="100 = average", annotation_position="top")
        bar.update_layout(height=max(350, 26 * top_n), yaxis=dict(autorange="reversed"),
                          xaxis_title=f"Real Index of {n1} currency (pair average = 100)",
                          margin=dict(l=10, r=60))
        st.plotly_chart(bar, use_container_width=True)
        st.dataframe(rk, use_container_width=True)
        st.download_button("Download ranking CSV", rk.to_csv().encode(),
                           file_name="rer_ranking.csv", mime="text/csv")
