import time
import threading
from flask import Flask, render_template, jsonify, request
from scraper import scrape_sensibull_option_chain

app = Flask(__name__)

# In-memory storage for cached option chain data
CACHE = {
    '1m': {
        'data': None,
        'last_updated': 0,
        'interval_sec': 60,
    },
    '3m': {
        'data': None,
        'last_updated': 0,
        'interval_sec': 180,
    }
}

CACHE_LOCK = threading.Lock()

def update_cache_for(interval_key):
    """
    Fetches fresh option chain data and updates the given cache key.
    """
    try:
        print(f"[{time.strftime('%H:%M:%S')}] Updating cache for {interval_key} table...")
        result = scrape_sensibull_option_chain(num_strikes=15)
        with CACHE_LOCK:
            CACHE[interval_key]['data'] = result
            CACHE[interval_key]['last_updated'] = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Successfully updated {interval_key} cache.")
    except Exception as e:
        print(f"Error updating {interval_key} cache: {e}")

def background_scheduler():
    """
    Background worker that updates 1m and 3m caches at their respective intervals.
    """
    # Initial load
    update_cache_for('1m')
    update_cache_for('3m')

    last_run_1m = time.time()
    last_run_3m = time.time()

    while True:
        time.sleep(1)
        now = time.time()

        if now - last_run_1m >= 60:
            threading.Thread(target=update_cache_for, args=('1m',), daemon=True).start()
            last_run_1m = now

        if now - last_run_3m >= 180:
            threading.Thread(target=update_cache_for, args=('3m',), daemon=True).start()
            last_run_3m = now

# Start background scheduler thread
scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    table_type = request.args.get('table', '1m')
    if table_type not in ('1m', '3m'):
        table_type = '1m'

    with CACHE_LOCK:
        cache_entry = CACHE.get(table_type)
        if cache_entry['data'] is None:
            # Fallback inline fetch if scheduler hasn't populated yet
            result = scrape_sensibull_option_chain(num_strikes=15)
            cache_entry['data'] = result
            cache_entry['last_updated'] = time.time()

        now = time.time()
        elapsed = int(now - cache_entry['last_updated'])
        interval = cache_entry['interval_sec']
        remaining = max(0, interval - elapsed)

        response_payload = dict(cache_entry['data'])
        response_payload['interval'] = table_type
        response_payload['last_updated_time'] = time.strftime('%H:%M:%S', time.localtime(cache_entry['last_updated']))
        response_payload['next_update_seconds'] = remaining

    return jsonify(response_payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
