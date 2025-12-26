import requests
import json
from django.conf import settings

# مقادیر ثابت زرین‌پال
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/"

class ZarinPalService:
    def __init__(self, merchant_id=None):
        # اگر مرچنت آیدی در ستینگز نبود، مقدار تست را بردار
        self.merchant_id = merchant_id or getattr(settings, 'ZARINPAL_MERCHANT_ID', 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')

    def send_request(self, amount, description, callback_url, email=None, mobile=None):
        """
        ارسال درخواست اولیه به زرین‌پال برای گرفتن Authority
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,  # مبلغ به تومان
            "callback_url": callback_url,
            "description": description,
            "metadata": {"email": email, "mobile": mobile}
        }
        
        headers = {'content-type': 'application/json', 'content-length': str(len(json.dumps(data)))}
        
        try:
            response = requests.post(ZP_API_REQUEST, data=json.dumps(data), headers=headers, timeout=10)
            if response.status_code == 200:
                response_json = response.json()
                if response_json['data']['code'] == 100:
                    return {
                        'status': True,
                        'url': f"{ZP_API_STARTPAY}{response_json['data']['authority']}",
                        'authority': response_json['data']['authority']
                    }
            return {'status': False, 'message': 'خطا در اتصال به درگاه'}
            
        except requests.exceptions.Timeout:
            return {'status': False, 'message': 'تایم‌اوت در اتصال به زرین‌پال'}
        except requests.exceptions.ConnectionError:
            return {'status': False, 'message': 'خطای ارتباط با اینترنت'}

    def verify_payment(self, authority, amount):
        """
        تایید تراکنش پس از بازگشت کاربر از بانک
        """
        data = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "authority": authority
        }
        headers = {'content-type': 'application/json', 'content-length': str(len(json.dumps(data)))}

        try:
            response = requests.post(ZP_API_VERIFY, data=json.dumps(data), headers=headers, timeout=10)
            if response.status_code == 200:
                response_json = response.json()
                if response_json['data']['code'] == 100:
                    return {
                        'status': True,
                        'ref_id': response_json['data']['ref_id'],
                        'message': 'تراکنش موفق'
                    }
                elif response_json['data']['code'] == 101:
                    return {
                        'status': True,
                        'ref_id': response_json['data']['ref_id'],
                        'message': 'تراکنش قبلاً تایید شده است'
                    }
            return {'status': False, 'message': 'تراکنش ناموفق یا لغو شده'}
            
        except Exception as e:
            return {'status': False, 'message': str(e)}