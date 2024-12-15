import requests

# API URL to fetch stock data
api_url = "https://data.irbe7.com/api/data/principaux"  # Replace with your actual API URL

# Django REST API URL to post data
django_api_url = "http://127.0.0.1:8000/api/stocks/"

# Static sector since it's not in the API
static_sector = "Unknown"

def fetch_and_post_stocks():
    try:
        # Fetch data from external API
        response = requests.get(api_url)
        if response.status_code == 200:
            stock_data = response.json()

            # Loop through the stock data and extract required fields
            for item in stock_data:
                name = item['referentiel']['stockName']
                symbol = item['referentiel']['ticker']
                price = item['last']

                # Create payload to post to Django API
                payload = {
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "sector": static_sector,  # Static value since not provided by the API
                }

                # Post data to Django REST API
                post_response = requests.post(django_api_url, json=payload)
                if post_response.status_code == 201:
                    print(f"Successfully added: {symbol} - {name}")
                elif post_response.status_code == 400:
                    print(f"Stock {symbol} already exists or validation error.")
                else:
                    print(f"Failed to add {symbol}. Status code: {post_response.status_code}")
        else:
            print(f"Failed to fetch data. API returned status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the function
fetch_and_post_stocks()
