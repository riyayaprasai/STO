# Finance News API

A powerful API that aggregates financial news and provides comprehensive market sentiment analysis.

## Features

- 🔍 **Comprehensive Data Sources**
  - Yahoo Finance - Real-time market data and news
  - Reuters - Global financial news and analysis
  - Bloomberg - Market insights and breaking news
  - MarketWatch - Financial news and market commentary
  - Seeking Alpha - In-depth analysis and research
  - Company information and fundamentals
  - Market metrics and analyst recommendations

- 📊 **Advanced Analytics**
  - Sentiment analysis with granular classification
  - Subjectivity analysis
  - Time-based sentiment trends
  - Market sentiment aggregation
  - Multi-source news comparison and analysis
  - Source-specific sentiment tracking

- 📈 **Market Data**
  - Real-time and historical price data
  - Volume analysis
  - Key market metrics (P/E ratio, market cap, etc.)
  - Analyst recommendations
  - Company fundamentals

- ⚡ **Performance Features**
  - Async processing
  - Input validation
  - Comprehensive error handling
  - Flexible filtering options
  - Customizable news sources

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/finance-news-api.git
cd finance-news-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create a .env file
touch .env

# Add the following to your .env file
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
```

4. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Key Management

The API includes a built-in admin interface for managing API keys. Access it at `http://localhost:8000/admin`

### Security
- Admin interface is protected with HTTP Basic Authentication
- Admin credentials are configured via environment variables
- All admin actions require authentication
- API keys are securely generated and stored

### Features
- Create new users and generate API keys
- View all existing users and their API keys
- Delete users and their API keys
- Copy API keys to clipboard

### Using the Admin Interface
1. Open `http://localhost:8000/admin` in your browser
2. Enter your admin credentials when prompted
3. Use the form to create new users
4. View and manage existing users in the table
5. Copy API keys using the "Copy" button
6. Delete users using the "Delete" button

## API Usage

### Authentication
All endpoints require API key authentication. Include your API key in the `X-API-Key` header:

```python
import requests

headers = {
    "X-API-Key": "your_api_key_here"
}

response = requests.get("http://localhost:8000/api/news/AAPL", headers=headers)
```

### Example Endpoints

#### Get News for a Stock
```python
response = requests.get(
    "http://localhost:8000/api/news/AAPL",
    params={
        "sentiment_threshold": 0.2,
        "time_range_hours": 24,
        "sources": ["reuters", "bloomberg"]
    },
    headers=headers
)
```

## Documentation

- API Documentation: `/docs` (Swagger UI)
- ReDoc Documentation: `/redoc`
- Full API Documentation: [API.md](API.md)

## Development

### Running Tests
```bash
pytest
```

### Code Style
The project follows PEP 8 style guidelines. To check your code:
```bash
flake8 .
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Project Structure

```
finance-news-api/
├── main.py              # FastAPI application entry point
├── routers/            # API route handlers
│   ├── news.py         # News endpoints
│   ├── users.py        # User registration
│   └── admin.py        # Admin interface
├── services/           # Business logic
│   ├── yahoo.py        # Yahoo Finance integration
│   ├── news_sources.py # News source integrations
│   ├── sentiment.py    # Sentiment analysis
│   └── google.py       # Google News integration
├── templates/          # HTML templates
│   └── admin.html      # Admin interface template
├── middleware/         # Middleware components
│   └── admin_auth.py   # Admin authentication
├── database.py         # Database configuration
├── models.py           # SQLAlchemy models
├── schemas.py          # Pydantic models
├── auth.py            # API key authentication
├── tests/              # Test files
├── .env               # Environment variables
├── requirements.txt   # Project dependencies
├── API.md            # API documentation
└── README.md         # Project documentation
```

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- YFinance - Yahoo Finance API
- TextBlob - Sentiment analysis
- BeautifulSoup4 - Web scraping
- Feedparser - RSS feed parsing
- Playwright - Browser automation
- Python-dotenv - Environment management

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

For support or to request a new API key, please contact:
- Email: pratyushkhanal95@gmail.com
- GitHub: https://github.com/pratyushkhanal

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 