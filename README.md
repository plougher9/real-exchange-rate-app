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
- Real Index can be viewed from Country 1's side, Country 2's side, or both. Country 2's index is the mirror image of Country 1's, built from 1/RER and scaled to average 100.
- A clearly marked 100 line shows the sample-average benchmark, with a shaded 90–110 band.
- Event markers for major episodes (for example Black Wednesday, the Asian financial crisis, Brexit, COVID-19).
- Over/undervalued gauge naming which currency is overvalued or undervalued and by how much.
- iPhone call: answer a ringing phone, receive an offer in Country 1 currency, and see the cost in Country 2 currency at today's rate and at the sample-average real rate. Prices are illustrative.
- Rank view comparing Country 1 against all other countries, with the percentage over- or undervalued on each bar.
- CSV downloads of all observations and calculations for the selected sample, plus a separate ranking CSV.

## Data

IMF SDMX 3.0 API: [api.imf.org](https://api.imf.org/external/sdmx/3.0)

- CPI: `{ISO3}.CPI._T.IX.M`
- Exchange rate: `{ISO3}.XDC_USD.PA_RT.M`

IMF data may have gaps or limited coverage for some countries.

## Run

Deployed on Streamlit Community Cloud with Python 3.12 and main file `app.py`. Dependencies are listed in `requirements.txt`.
