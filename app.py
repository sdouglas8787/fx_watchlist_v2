from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import zscore
from flask_caching import Cache
import requests
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here_please_change_in_production')

# Configure cache
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Configuration
ITEMS_PER_PAGE = 15
ANOMALY_ZSCORE_THRESHOLD = 2.5
ROLLING_WINDOW = 7
MAX_WORKERS = 5

# Rate limiting for Yahoo Finance
class FXWatchlistGlobal:
    def __init__(self, currency_pairs):
        self.currency_pairs = currency_pairs
        self.tickers = self._convert_to_tickers(currency_pairs)
        self.lock = threading.Lock()

    def _convert_to_tickers(self, currency_pairs):
        """Convert currency pairs to Yahoo Finance ticker format"""
        tickers = []
        for pair in currency_pairs:
            base = pair['base']
            quote = pair['quote']
            
            if base == 'USD':
                tickers.append(f"{quote}=X")
            elif quote == 'USD':
                tickers.append(f"{base}=X")
            else:
                tickers.append(f"{base}{quote}=X")
        return tickers

    def _fetch_data(self, start_date, end_date):
        """Fetch data with improved error handling and rate limiting"""
        try:
            with self.lock:
                data = yf.download(
                    self.tickers,
                    start=start_date,
                    end=end_date,
                    group_by='ticker',
                    threads=True,
                    progress=False
                )
                # Ensure single ticker results are properly formatted
                if len(self.tickers) == 1 and 'Close' in data.columns:
                    data = pd.DataFrame({self.tickers[0]: data['Close']})
                return data
        except Exception as e:
            logger.error(f"Data fetch error: {str(e)}")
            return pd.DataFrame()

    @cache.memoize(timeout=300)
    def get_metrics(self, start_date=None, end_date=None):
        """Get cached metrics with improved error handling"""
        end_date = end_date or datetime.now()
        start_date = start_date or end_date - timedelta(days=365*3)
        
        data = self._fetch_data(start_date, end_date)
        if data.empty:
            return {}
            
        metrics = {}
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for pair in self.currency_pairs:
                futures.append(executor.submit(self._process_pair, pair, data))
            
            for future in futures:
                result = future.result()
                if result:
                    metrics.update(result)
        
        return metrics

    def _process_pair(self, pair, data):
        """Process single currency pair"""
        pair_name = f"{pair['base']}/{pair['quote']}"
        ticker = self._convert_to_tickers([pair])[0]
        
        try:
            # Extract ticker data
            if len(self.currency_pairs) == 1:
                series = data[ticker]
            else:
                series = data[ticker]['Close']
            
            # Clean data
            series = series.dropna()
            if len(series) < 7:  # Need at least 7 days for 7d changes
                return None
                
            series = series.ffill().bfill()
            
            return {pair_name: {
                **self._calculate_metrics(series),
                'anomaly': self._detect_anomaly(series)
            }}
        except Exception as e:
            logger.error(f"Error processing {pair_name}: {str(e)}")
            return None

    def _calculate_metrics(self, series):
        """Calculate currency pair metrics"""
        latest = series.iloc[-1]
        metrics = {'current': float(latest)}
        
        # Calculate changes with proper error handling
        for period, days in [('7d', 7), ('30d', 30), ('1y', 365), ('3y', 365*3)]:
            if len(series) >= days:
                old_value = series.iloc[-days]
                abs_change = latest - old_value
                pct_change = ((latest / old_value) - 1) * 100
                metrics[f'{period}_abs'] = float(abs_change)
                metrics[f'{period}_pct'] = float(pct_change)
            else:
                metrics[f'{period}_abs'] = np.nan
                metrics[f'{period}_pct'] = np.nan
        
        # YTD calculation
        try:
            year_start = f"{datetime.now().year}-01-01"
            ytd_data = series[series.index >= year_start]
            if not ytd_data.empty:
                year_start_value = ytd_data.iloc[0]
                ytd_abs = latest - year_start_value
                ytd_pct = ((latest / year_start_value) - 1) * 100
                metrics['ytd_abs'] = float(ytd_abs)
                metrics['ytd_pct'] = float(ytd_pct)
            else:
                metrics['ytd_abs'] = np.nan
                metrics['ytd_pct'] = np.nan
        except Exception:
            metrics['ytd_abs'] = np.nan
            metrics['ytd_pct'] = np.nan
        
        return metrics

    def _detect_anomaly(self, series):
        """Detect price anomalies using z-score"""
        if len(series) < ROLLING_WINDOW*2:
            return False
            
        try:
            rolling_mean = series.rolling(ROLLING_WINDOW).mean().shift(1)
            rolling_std = series.rolling(ROLLING_WINDOW).std().shift(1)
            
            # Avoid division by zero
            if rolling_std.iloc[-1] == 0:
                return False
                
            z_scores = (series - rolling_mean) / rolling_std
            return abs(z_scores.iloc[-1]) > ANOMALY_ZSCORE_THRESHOLD
        except Exception:
            return False

# Default currency pairs
DEFAULT_PAIRS = [
    {'base': 'EUR', 'quote': 'USD'},
    {'base': 'GBP', 'quote': 'USD'},
    {'base': 'USD', 'quote': 'JPY'},
    {'base': 'USD', 'quote': 'CHF'},
    {'base': 'AUD', 'quote': 'USD'},
    {'base': 'USD', 'quote': 'CAD'},
    {'base': 'NZD', 'quote': 'USD'},
    {'base': 'EUR', 'quote': 'GBP'},
    {'base': 'EUR', 'quote': 'JPY'},
    {'base': 'GBP', 'quote': 'JPY'},
]

@app.route('/')
def index():
    """Main dashboard route"""
    page = request.args.get('page', 1, type=int)
    saved_pairs = session.get('saved_pairs', DEFAULT_PAIRS)
    
    # Initialize saved_pairs if empty
    if not saved_pairs:
        saved_pairs = DEFAULT_PAIRS
        session['saved_pairs'] = saved_pairs
    
    # Pagination
    start = (page - 1) * ITEMS_PER_PAGE
    paginated_pairs = saved_pairs[start:start+ITEMS_PER_PAGE]
    
    if not paginated_pairs:
        return render_template('index.html', metrics={}, pagination={'page': 1, 'total_pages': 1})
    
    try:
        fx = FXWatchlistGlobal(paginated_pairs)
        metrics = fx.get_metrics()
        
        total_pages = (len(saved_pairs) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        return render_template(
            'index.html',
            metrics=metrics,
            saved_pairs=saved_pairs,
            pagination={
                'page': page,
                'total_pages': total_pages
            }
        )
    except Exception as e:
        logger.error(f"Error in main route: {str(e)}")
        return render_template('error.html', error=str(e)), 500

@app.route('/add_pair', methods=['POST'])
def add_pair():
    """Add a new currency pair to watchlist"""
    base = request.form.get('base', '').upper()
    quote = request.form.get('quote', '').upper()
    
    if base and quote:
        pairs = session.get('saved_pairs', [])
        new_pair = {'base': base, 'quote': quote}
        
        # Check if pair already exists
        if not any(p['base'] == base and p['quote'] == quote for p in pairs):
            pairs.append(new_pair)
            session['saved_pairs'] = pairs
            session.modified = True
    
    return redirect(url_for('index'))

@app.route('/remove_pair/<base>/<quote>', methods=['POST'])
def remove_pair(base, quote):
    """Remove a currency pair from watchlist"""
    pairs = session.get('saved_pairs', [])
    pairs = [p for p in pairs if not (p['base'] == base and p['quote'] == quote)]
    session['saved_pairs'] = pairs
    session.modified = True
    return redirect(url_for('index'))

@app.route('/clear_cache')
def clear_cache():
    """Clear application cache"""
    cache.clear()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
