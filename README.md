# Real Exchange Rate App

Streamlit app that computes the real exchange rate between any two countries (or the Euro area) from IMF monthly data.

- S(t): units of Country 2 currency per 1 unit of Country 1 currency (IMF gives local currency per USD, so S = X2 / X1)
- RER(t) = S(t) × P1(t) / P2(t)
- RER* = average RER over the selected sample; Real Index = 100 × RER / RER*
- Charts: Real, Nominal, or Both (dual axes); CSV download of the selected sample

Data: IMF SDMX 3.0 API (`CPI`: `{ISO3}.CPI._T.IX.M`, `ER`: `{ISO3}.XDC_USD.PA_RT.M`; Euro area = `G163`). Python 3.12.

Run on Streamlit Community Cloud with main file `app.py`.
