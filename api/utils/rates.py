from decimal import Decimal, ROUND_DOWN

from django.core.cache import cache

import requests


class Rates:
    """
    Provides convenient methods to convert a given amount of bitcoins to the
    equivalent number of currency. We used an external API to query bitcoins rates.
    Caching is used to improve the performance of the application.
    For simplicity we used only one API to query bitcoins rates.
    Bitpay API Documentation con be found here: https://bitpay.com/api/#rest-api
    """

    API_URL = "https://bitpay.com/rates/BTC/"
    API_NOT_AVAILABLE = "Not available at the moment"

    @classmethod
    def api_call(cls, currency):
        """
        Performs the requests to the external API to query bitcoins rates.
        """
        headers = {"x-accept-version": "2.0.0", "Accept": "application/json"}
        r = requests.get(cls.API_URL + currency, headers=headers)
        r.raise_for_status()
        return r.json()["data"]["rate"]

    @classmethod
    def bitcoins_to_currency(cls, currency, amount):
        """
        Converts a given amount of bitcoins to the equivalent number of currency.
        Caching is used to improve the performance of the application.
        """
        if not (rate := cache.get(currency)):
            try:
                api_rate = cls.api_call(currency)
                decimals = Decimal("0.01")
                total = amount * Decimal(str(api_rate))
                rate = total.quantize(decimals, rounding=ROUND_DOWN).normalize()
            except Exception:
                # Don't retry. Just send empty flag
                rate = cls.API_NOT_AVAILABLE
            if rate and rate != cls.API_NOT_AVAILABLE:
                cache.set(currency, rate)
        return rate

    @classmethod
    def bitcoins_to_usd(cls, amount):
        return cls.bitcoins_to_currency("usd", amount)
