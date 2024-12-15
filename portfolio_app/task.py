from django.db import models
from celery import shared_task
import requests
from .models import Stock
import os
import sys
import json
import os
# Add the project root directory to the Python path
@shared_task
def update_stock_prices_task():
    api_url = "https://data.irbe7.com/api/data/principaux"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        stock_data = response.json()

        for item in stock_data:
            symbol = item['referentiel']['ticker']
            price = item['referentiel']['last']

            try:
                stock = Stock.objects.get(symbol=symbol)
                stock.price = price
                stock.save()
            except Stock.DoesNotExist:
                continue

    except requests.exceptions.RequestException as e:
        print(f"Error updating stock prices: {e}")
