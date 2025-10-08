import requests
import httpx
from others.models import BkashConfiguration,UddoktapayConfiguration

class BkashPaymentHelper:
    def __init__(self):
        config = BkashConfiguration.objects.first()
        self.base_url = (
            "https://tokenized.sandbox.bka.sh/v1.2.0-beta/tokenized/checkout"
            if config.sandbox else
            "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout"
        )
        self.app_key = config.app_key
        self.app_secret = config.app_secret
        self.username = config.username
        self.password = config.password

    def get_token(self):
        url = f"{self.base_url}/token/grant"
        headers = {
            "accept": "application/json",
            "username": self.username,
            "password": self.password,
            "content-type": "application/json"
        }
        data = {
            "app_key": self.app_key,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json().get("id_token")

    def create_payment(self, amount, merchant_invoice):
        token = self.get_token()
        url = f"{self.base_url}/create"
        headers = {
            "accept": "application/json",
            "Authorization": token,
            "X-APP-Key": self.app_key,
            "Content-Type": "application/json"
        }
        data = {
            "mode": "0011",
            "callbackURL": "https://bdmouza.com/success/",
            "amount": str(amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": merchant_invoice,
            "payerReference": "YourAppName"
        }
        response = requests.post(url, json=data, headers=headers)
        res_json = response.json()
        print(res_json)
        if res_json.get("statusCode") == "0000":
            return res_json.get("bkashURL"), res_json.get("paymentID")
        return None, None

    def execute_payment(self, payment_id):
        token = self.get_token()
        url = f"{self.base_url}/execute"
        headers = {
            "accept": "application/json",
            "Authorization": token,
            "X-APP-Key": self.app_key,
            "Content-Type": "application/json"
        }
        data = {"paymentID": payment_id}
        response = requests.post(url, json=data, headers=headers)
        return response.json()
class UddoktapayPaymentHelper:
    def __init__(self):
        from others.models import UddoktapayConfiguration
        config = UddoktapayConfiguration.objects.first()
        self.api_key = config.api_key
        self.base_url = (
            "https://sandbox.uddoktapay.com/api/checkout-v2"
            if config.sandbox else
            "https://pay.bdmouza.com/api/checkout-v2"
        )

    def create_payment(self, full_name, email, amount, user_id, order_id):
        headers = {
            "accept": "application/json",
            "RT-UDDOKTAPAY-API-KEY": self.api_key,
            "content-type": "application/json",
            "User-Agent": "Thunder Client"
        }

        payload = {
            "full_name": full_name,
            "email": email,
            "amount": str(amount),
            "metadata": {
                "user_id": str(user_id),
                "order_id": str(order_id)
            },
            "redirect_url": "https://bdmouza.com/success",
            "cancel_url": "https://bdmouza.com/",
            "webhook_url": "https://pay.bdmouza.com/callback/e55d9979c0a8812447c3415a2cd3c0f13def69b7"
        }

        try:
            with httpx.Client(verify=False, http2=False) as client:
                response = client.post(self.base_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                res_json = response.json()
                print(res_json)
                if res_json.get("status") and res_json.get("payment_url"):
                    return res_json["payment_url"]
                return None
        except httpx.HTTPError as e:
            print("HTTPX Request failed:", e)
            return None