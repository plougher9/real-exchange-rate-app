# real-exchange-rate-app

**The Real Exchange Ledger** is a Streamlit app that computes the real exchange rate (RER) between any two IMF countries, or the Euro area, using monthly IMF data.

## Definitions

- S(t): units of Country 2 currency per 1 unit of Country 1 currency. The IMF reports local currency per USD, so S = X2 / X1.
- RER(t) = S(t) × P1(t) / P2(t), where P1 and P2 are monthly CPIs.
- RER* = average of RER(t) over the selected sample. It is recalculated whenever the dates change.
- Real Index(t) = 100 × RER(t) / RER*.

## Features

- Choose Country 1 and Country 2 from IMF countries plus the Euro area (IMF code G163). Data starts in January 1976 where available.
- Interactive chart: Real, Nominal, or Both (dual axes). Nominal S is shown in actual currency units.
- Event markers for major episodes (for example Black Wednesday, the Asian financial crisis, Brexit, COVID-19).
- Over/undervalued gauge showing the latest Real Index against 100.
- iPhone price comparison showing what a phone costs in Country 2 currency at today's rate and at the sample-average real rate. Prices are illustrative.
- Rank view comparing Country 1 against all other countries.
- CSV download of all observations and calculations for the selected sample.

## Data

IMF SDMX 3.0 API: [api.imf.org](https://api.imf.org/external/sdmx/3.0)

- CPI: `{ISO3}.CPI._T.IX.M`
- Exchange rate: `{ISO3}.XDC_USD.PA_RT.M`

IMF data may have gaps or limited coverage for some countries.

## Run

Deployed on Streamlit Community Cloud with Python 3.12 and main file `app.py`. Dependencies are listed in `requirements.txt`.
