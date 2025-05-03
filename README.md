# FX Watchlist Matrix Dashboard

A real-time foreign exchange rate monitoring dashboard with trend analysis and anomaly detection.

## Features

- **Real-time FX Rate Tracking**: Monitor multiple currency pairs with live updates
- **Comprehensive Trend Analysis**: Track 7-day, 30-day, YTD, 1-year, and 3-year changes
- **Anomaly Detection**: Automatically detect unusual price movements using statistical analysis
- **Customizable Watchlist**: Add/remove currency pairs on the fly
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Caching**: Efficient data caching to minimize API calls
- **Production Ready**: Docker support for easy deployment

## Quick Start

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd fx-watchlist
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export SECRET_KEY=your_secret_key_here
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

2. Access the application at `http://localhost:5000`

## Project Structure

```
fx-watchlist/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── templates/
│   ├── index.html        # Main dashboard template
│   └── error.html        # Error page template
└── README.md             # This file
```

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key for session management
- `FLASK_ENV`: Environment mode (development/production)
- `PORT`: Port to run the application (default: 5000)

### Application Settings

Key configuration parameters in `app.py`:

```python
ITEMS_PER_PAGE = 15              # Number of pairs per page
ANOMALY_ZSCORE_THRESHOLD = 2.5   # Z-score threshold for anomaly detection
ROLLING_WINDOW = 7               # Rolling window for calculations
MAX_WORKERS = 5                  # Thread pool size
```

## API Endpoints

### GET `/`
Main dashboard displaying currency pair metrics

**Query Parameters:**
- `page`: Page number for pagination (default: 1)

### POST `/add_pair`
Add a new currency pair to the watchlist

**Form Parameters:**
- `base`: Base currency code (e.g., USD, EUR)
- `quote`: Quote currency code (e.g., USD, GBP)

### POST `/remove_pair/<base>/<quote>`
Remove a currency pair from the watchlist

**URL Parameters:**
- `base`: Base currency code
- `quote`: Quote currency code

### GET `/clear_cache`
Clear application cache

## Technical Features

### Anomaly Detection

The application uses statistical analysis to detect anomalies:
- Calculates rolling mean and standard deviation
- Uses z-score to identify outliers
- Configurable threshold for sensitivity

### Data Fetching Optimization

- Multi-threaded data fetching
- Efficient caching with TTL
- Rate limiting for API calls
- Error handling and fallbacks

### Performance Considerations

- Pagination for large datasets
- Asynchronous processing
- Minimal database footprint
- Optimized for low latency

## Troubleshooting

### Common Issues

1. **API Rate Limiting**
   - The application implements rate limiting
   - If you see delays, this is normal behavior
   - Clear cache if needed: `/clear_cache`

2. **Missing Data**
   - Check internet connection
   - Verify currency codes are valid
   - Look for error messages in browser console

3. **Session Issues**
   - Ensure SECRET_KEY is properly set
   - Check browser cookies are enabled

### Logs

Check application logs for detailed error information:
```bash
docker-compose logs fx-watchlist
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Quality

```bash
# Code formatting
black app.py

# Linting
flake8 app.py

# Type checking
mypy app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Support

For issues and feature requests, please create an issue in the GitHub repository.

## Acknowledgments

- Data provided by [Yahoo Finance](https://finance.yahoo.com/)
- Built with [Flask](https://flask.palletsprojects.com/)
- UI components from [Bootstrap 5](https://getbootstrap.com/)

## Security

- Never commit sensitive credentials
- Use environment variables for secrets
- Implement proper session management
- Regular dependency updates
