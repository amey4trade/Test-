#!/usr/bin/env python3
import pandas as pd
import numpy as np
from tabulate import tabulate

def fetch_or_generate_nifty_option_chain(num_strikes=10):
    """
    Generates Nifty 50 Option Chain table up to `num_strikes` around ATM.
    Columns included: Call OI, Call OI Change, Call Volume, Call LTP,
                     Strike Price,
                     Put LTP, Put Volume, Put OI Change, Put OI.
    """
    spot_price = 22520.45
    try:
        import yfinance as yf
        ticker = yf.Ticker("^NSEI")
        live_price = ticker.fast_info.get('lastPrice')
        if live_price and not np.isnan(live_price):
            spot_price = round(live_price, 2)
    except Exception as e:
        pass

    # Calculate ATM strike rounded to nearest 50 points
    atm_strike = int(round(spot_price / 50.0) * 50)

    # Calculate strikes range around ATM for 10 strikes (e.g. 5 below, 5 above)
    half_strikes = num_strikes // 2
    strikes = [atm_strike + i * 50 for i in range(-half_strikes, num_strikes - half_strikes)]

    data = []
    for strike in strikes:
        diff = strike - spot_price

        # Calculate option prices
        if diff < 0:
            call_ltp = abs(diff) + 110.0 - abs(diff) * 0.15
            put_ltp = max(10.0, 110.0 - abs(diff) * 0.45)
        else:
            call_ltp = max(10.0, 110.0 - abs(diff) * 0.45)
            put_ltp = diff + 110.0 - diff * 0.15

        # Calculate Open Interest, OI Change, Volume
        call_oi = int(3500000 * np.exp(-((strike - atm_strike)**2) / (2 * 150**2)) + 500000)
        put_oi = int(3800000 * np.exp(-((strike - atm_strike)**2) / (2 * 150**2)) + 600000)

        call_oi_chg = int(call_oi * (0.05 + 0.02 * np.sin(strike)))
        put_oi_chg = int(put_oi * (0.06 + 0.02 * np.cos(strike)))

        call_volume = int(call_oi * 0.35 + 120000)
        put_volume = int(put_oi * 0.38 + 140000)

        strike_label = f"{strike:,}"
        if strike == atm_strike:
            strike_label += " (ATM)"

        data.append({
            "Call OI": f"{call_oi:,}",
            "Call OI Chg": f"{call_oi_chg:+,}",
            "Call Vol": f"{call_volume:,}",
            "Call LTP (₹)": f"{call_ltp:.2f}",
            "Strike Price": strike_label,
            "Put LTP (₹)": f"{put_ltp:.2f}",
            "Put Vol": f"{put_volume:,}",
            "Put OI Chg": f"{put_oi_chg:+,}",
            "Put OI": f"{put_oi:,}"
        })

    df = pd.DataFrame(data)
    return spot_price, atm_strike, df


def display_option_chain_table():
    spot, atm, df = fetch_or_generate_nifty_option_chain(num_strikes=10)

    header = f"NIFTY 50 Option Chain (Spot Price: {spot:,.2f} | ATM Strike: {atm:,})"
    divider = "=" * len(header)

    print(f"\n{divider}")
    print(header)
    print(f"{divider}\n")

    table_str = tabulate(df, headers='keys', tablefmt='fancy_grid', showindex=False)
    print(table_str)
    print("\n" + divider + "\n")
    return df


if __name__ == "__main__":
    display_option_chain_table()
