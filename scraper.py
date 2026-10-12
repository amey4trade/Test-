import re
import time
import random
from playwright.sync_api import sync_playwright

SENSIBULL_URL = "https://web.sensibull.com/option-chain?tradingsymbol=NIFTY&expiry=2026-10-13"

def get_simulated_fallback(num_strikes=15, spot_price=22365.0):
    """
    Generates realistic fallback data for 15 strikes centered around spot price
    if live scraping encounters network issues or timeouts.
    """
    atm_strike = round(spot_price / 50) * 50
    half = num_strikes // 2
    strikes = [atm_strike + i * 50 for i in range(-half, half + 1)]
    if len(strikes) > num_strikes:
        strikes = strikes[:num_strikes]

    rows = []
    for s in strikes:
        distance = (s - spot_price) / 50.0
        # Call delta ~ 0.5 - 0.05 * distance
        call_delta = max(0.01, min(0.99, round(0.50 - 0.05 * distance, 2)))
        put_delta = max(-0.99, min(-0.01, round(call_delta - 1.0, 2)))

        call_ltp = max(0.5, round(max(0, spot_price - s) + 120 * max(0.1, 1 - abs(distance)*0.12) + random.uniform(-2, 2), 2))
        put_ltp = max(0.5, round(max(0, s - spot_price) + 120 * max(0.1, 1 - abs(distance)*0.12) + random.uniform(-2, 2), 2))

        call_oi = round(random.uniform(20.0, 150.0), 1)
        call_oi_chg_val = round(random.uniform(-10.0, 25.0), 1)
        call_oi_chg_pct = round((call_oi_chg_val / call_oi) * 100, 1)

        put_oi = round(random.uniform(25.0, 180.0), 1)
        put_oi_chg_val = round(random.uniform(-8.0, 30.0), 1)
        put_oi_chg_pct = round((put_oi_chg_val / put_oi) * 100, 1)

        call_vol = random.randint(100, 5000)
        put_vol = random.randint(150, 6000)

        rows.append({
            'call_delta': f"{call_delta:.2f}",
            'call_volume': f"{call_vol:,}",
            'call_oi_chg': f"{call_oi_chg_val:+.1f} ({call_oi_chg_pct:+.1f}%)",
            'call_oi': f"{call_oi:.1f}",
            'call_ltp': f"{call_ltp:.2f}",
            'strike': s,
            'is_atm': (s == atm_strike),
            'put_ltp': f"{put_ltp:.2f}",
            'put_oi': f"{put_oi:.1f}",
            'put_oi_chg': f"{put_oi_chg_val:+.1f} ({put_oi_chg_pct:+.1f}%)",
            'put_volume': f"{put_vol:,}",
            'put_delta': f"{put_delta:.2f}"
        })

    return {
        'spot_price': spot_price,
        'atm_strike': atm_strike,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'source': 'Sensibull (Simulated Fallback)',
        'data': rows
    }


def scrape_sensibull_option_chain(num_strikes=15):
    """
    Scrapes live NIFTY option chain from Sensibull using Playwright.
    Selects `num_strikes` strikes centered on ATM spot price.
    Returns dictionary with spot_price, atm_strike, timestamp, data.
    """
    print(f"Scraping live data from {SENSIBULL_URL}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(SENSIBULL_URL, timeout=35000)
            page.wait_for_timeout(8000)

            # Click 'All Column View' if available to reveal Delta & Volume
            all_col_btn = page.query_selector('button:has-text("All Column View")')
            if all_col_btn:
                all_col_btn.click()
                page.wait_for_timeout(2000)

            # Extract spot price from body text
            body_text = page.locator('body').inner_text()
            match = re.search(r'NIFTY\s*\n\s*([\d,]+\.?\d*)', body_text)
            spot_price = float(match.group(1).replace(',', '')) if match else 22365.0

            rows = page.query_selector_all('tr')
            extracted = []

            for r in rows:
                cells = [c.inner_text().strip().replace('\n', ' ') for c in r.query_selector_all('th, td')]
                if len(cells) == 37:
                    try:
                        strike_val = int(cells[18])
                        call_ltp = cells[17].split(' ')[0] if cells[17] else '0.00'
                        put_ltp = cells[20].split(' ')[0] if cells[20] else '0.00'

                        call_oi_chg = f"{cells[7]} ({cells[8]})" if cells[7] and cells[8] else cells[8]
                        put_oi_chg = f"{cells[30]} ({cells[29]})" if cells[30] and cells[29] else cells[29]

                        extracted.append({
                            'call_delta': cells[3] or '--',
                            'call_volume': cells[6] or '0',
                            'call_oi_chg': call_oi_chg or '0',
                            'call_oi': cells[9] or '0.0',
                            'call_ltp': call_ltp,
                            'strike': strike_val,
                            'is_atm': False,
                            'put_ltp': put_ltp,
                            'put_oi': cells[28] or '0.0',
                            'put_oi_chg': put_oi_chg or '0',
                            'put_volume': cells[31] or '0',
                            'put_delta': cells[33] or '--',
                        })
                    except ValueError:
                        continue

            browser.close()

            if extracted:
                strikes = [item['strike'] for item in extracted]
                closest_strike = min(strikes, key=lambda s: abs(s - spot_price))
                atm_index = strikes.index(closest_strike)

                start_idx = max(0, atm_index - num_strikes // 2)
                end_idx = min(len(strikes), start_idx + num_strikes)
                if end_idx - start_idx < num_strikes and start_idx > 0:
                    start_idx = max(0, end_idx - num_strikes)

                selected = extracted[start_idx:end_idx]
                for item in selected:
                    if item['strike'] == closest_strike:
                        item['is_atm'] = True

                return {
                    'spot_price': spot_price,
                    'atm_strike': closest_strike,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'Sensibull Live',
                    'data': selected
                }
    except Exception as e:
        print(f"Playwright scraping error: {e}")

    print("Falling back to simulated data generator...")
    return get_simulated_fallback(num_strikes=num_strikes)

if __name__ == "__main__":
    result = scrape_sensibull_option_chain(15)
    print(f"Fetched {len(result['data'])} strikes. Spot: {result['spot_price']}, ATM: {result['atm_strike']}, Source: {result['source']}")
    for r in result['data']:
        print(r)
