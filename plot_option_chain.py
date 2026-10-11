#!/usr/bin/env python3
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def fetch_or_generate_nifty_option_chain():
    """
    Returns Nifty 50 spot price, ATM strike, and option chain DataFrame near ATM.
    Includes Call/Put OI, LTP, Bid Price, and Ask Price.
    """
    spot_price = 22520.45
    try:
        import yfinance as yf
        ticker = yf.Ticker("^NSEI")
        live_price = ticker.fast_info.get('lastPrice')
        if live_price and not np.isnan(live_price):
            spot_price = round(live_price, 2)
    except Exception as e:
        print(f"Using default spot price due to fetch notice: {e}")

    # Calculate ATM strike rounded to nearest 50 points
    atm_strike = int(round(spot_price / 50.0) * 50)

    # Generate strikes around ATM (-200 to +200)
    strikes = [atm_strike + i * 50 for i in range(-4, 5)]

    data = []
    for strike in strikes:
        diff = strike - spot_price

        # Calculate realistic option prices
        if diff < 0:
            call_ltp = abs(diff) + 110.0 - abs(diff) * 0.15
            put_ltp = max(10.0, 110.0 - abs(diff) * 0.45)
        else:
            call_ltp = max(10.0, 110.0 - abs(diff) * 0.45)
            put_ltp = diff + 110.0 - diff * 0.15

        call_bid = max(0.05, call_ltp - 0.50)
        call_ask = call_ltp + 0.50
        put_bid = max(0.05, put_ltp - 0.50)
        put_ask = put_ltp + 0.50

        # Standard simulated OI distribution around ATM
        call_oi = int(3500000 * np.exp(-((strike - atm_strike)**2) / (2 * 150**2)) + 500000)
        put_oi = int(3800000 * np.exp(-((strike - atm_strike)**2) / (2 * 150**2)) + 600000)

        strike_label = f"{strike:,}"
        if strike == atm_strike:
            strike_label += " (ATM)"

        data.append({
            "Call OI": f"{call_oi:,}",
            "Call Bid (₹)": f"{call_bid:.2f}",
            "Call Ask (₹)": f"{call_ask:.2f}",
            "Call LTP (₹)": f"{call_ltp:.2f}",
            "Strike Price": strike_label,
            "Put LTP (₹)": f"{put_ltp:.2f}",
            "Put Bid (₹)": f"{put_bid:.2f}",
            "Put Ask (₹)": f"{put_ask:.2f}",
            "Put OI": f"{put_oi:,}"
        })

    df = pd.DataFrame(data)
    return spot_price, atm_strike, df


def plot_option_chain_table(spot_price, atm_strike, df, output_filename="nifty_option_chain.png"):
    fig, ax = plt.subplots(figsize=(15, 6.5))
    ax.axis('tight')
    ax.axis('off')

    # Add header title and metadata
    title_text = f"NIFTY 50 Option Chain (ATM Calls & Puts: Prices, Bid/Ask & Open Interest)\nSpot Price: {spot_price:,} | ATM Strike: {atm_strike:,}"
    plt.title(title_text, fontsize=14, fontweight='bold', pad=22, color='#1A237E')

    # Create table
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1.15, 2.0)

    # Style table headers and rows
    for (row, col), cell in table.get_celld().items():
        cell.set_linewidth(0.8)
        cell.set_edgecolor('#D0D0D0')

        if row == 0:
            # Header styling
            cell.set_facecolor('#1A237E')
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
            cell.get_text().set_fontsize(10.5)
        else:
            data_row_idx = row - 1
            strike_val = df.iloc[data_row_idx]['Strike Price']

            if "(ATM)" in strike_val:
                # ATM Row highlight
                cell.set_facecolor('#FFF9C4')  # Soft yellow highlight
                cell.get_text().set_weight('bold')
            elif data_row_idx % 2 == 0:
                cell.set_facecolor('#F8F9FA')  # Alternating light background
            else:
                cell.set_facecolor('#FFFFFF')

    plt.tight_layout()
    plt.savefig(output_filename, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Successfully saved table plot to '{output_filename}'.")


if __name__ == "__main__":
    spot, atm, df = fetch_or_generate_nifty_option_chain()
    print("\n=================== NIFTY 50 OPTION CHAIN ===================")
    print(f"Spot Price: {spot} | ATM Strike: {atm}\n")
    print(df.to_string(index=False))
    print("=============================================================\n")

    plot_option_chain_table(spot, atm, df)
