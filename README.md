# real-exchange-rate-app

Streamlit app that computes the real exchange rate (RER) between any two IMF countries or the Euro area, using monthly IMF data from January 1976.

- S(t): units of Country 2 currency per 1 unit of Country 1 currency (IMF gives local currency per USD, so S = X2 / X1)
- RER(t) = S(t) × P1(t) / P2(t); RER* = the sample average, recalculated when the dates change
- Real Index(t) = 100 × RER(t) / RER*
- Charts: Real, Nominal, or Both (dual axes), with event markers
- Extras: over/undervalued gauge, iPhone offer call, rank view against all other countries
- CSV download of all observations and calculations for the selected sample

Data: IMF SDMX 3.0 API (`CPI`: `{ISO3}.CPI._T.IX.M`, `ER`: `{ISO3}.XDC_USD.PA_RT.M`; Euro area = `G163`). Python 3.12, main file `app.py`.


## Run

Deployed on Streamlit Community Cloud with Python 3.12 and main file `app.py`. Dependencies are listed in `requirements.txt`.
