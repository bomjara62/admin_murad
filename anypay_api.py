import hashlib
import aiohttp
import asyncio
import requests


class AnyPay:
    API_BASE_URL = "https://anypay.io/api/"
    MERCHANT_BASE_URL = "https://anypay.io/merchant"

    def __init__(self, api_id, api_key, project_id):
        self.api_id = api_id
        self.api_key = api_key
        self.project_id = project_id

    def get_str_to_hash(self, method: str, list_of_args: list = None):
        if list_of_args is None:
            list_of_args = []
        return f"{method}{self.api_id}{''.join(map(str, list_of_args))}{self.api_key}"

    def get_hash(self, text: str):
        return hashlib.sha256(text.encode()).hexdigest()

    async def send_request(self, method: str, json: dict) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "multipart/form-data"
        }
        url = self.API_BASE_URL + method + "/" + api_id + "?"

        for key, value in json.items():
            url += key + "=" + str(value) + "&"

        url = url[:-1]
        async with aiohttp.ClientSession() as session:
            # resp = await session.post(url=self.API_BASE_URL + method + "/" + api_id, json = json, headers = headers)
            resp = await session.get(url=url, headers=headers)

            if resp.status != 200:
                print(await resp.text(content_type=None))

            resp_json = await resp.json(content_type=None)
            return resp_json

    async def create_payment(self, pay_id: int, amount: float, email: str, method: str = 'card', currency: str = "RUB",
                             desc: str = 'Вип Ани'):
        str_to_hash = f'''create-payment{self.api_id}{self.project_id}{pay_id}{amount}{currency}{desc}{method}{self.api_key}'''
        json = {
            "project_id": self.project_id,
            "pay_id": pay_id,
            "amount": amount,
            "email": email,
            "method": method,
            "currency": currency,
            "desc": desc,
            "sigh": self.get_hash(str_to_hash)
        }
        return await self.send_request(method="create-payment", json=json)

    async def get_payments(self, pay_id: int):
        str_to_hash = self.get_str_to_hash("payments", [self.project_id])
        json = {
            "project_id": self.project_id,
            "pay_id": pay_id,
            "sign": self.get_hash(str_to_hash)
        }

        return await self.send_request(method="payments", json=json)

    async def get_balance(self):
        str_to_hash = self.get_str_to_hash("balance")
        json = {"sign": self.get_hash(str_to_hash)}

        return await self.send_request(method="balance", json=json)

    async def create_form_of_payment(self, pay_id: int, amount: float, currency="RUB"):
        secret_key = "rtbZzc9AtCnUTF$"
        sign = hashlib.md5(f"{currency}:{amount}:{secret_key}:{self.project_id}:{pay_id}".encode()).hexdigest()

        return self.MERCHANT_BASE_URL + f"?merchant_id={self.project_id}&pay_id={pay_id}&amount={amount}&currency={currency}&sign={sign}"


api_id = "F2C0FE20CB16A393F8"
api_key = "CguQG1UzE9tiihi4bd6RxZFFzFMCbnWM6mQVlVE"
project_id = 10530

any_pay = AnyPay(api_id=api_id, api_key=api_key, project_id=project_id)


async def main():
    #responce = requests.get(f"https://anypay.io/api/balance/{ANYPAY_API_ID()}", params={"sign": sign.hexdigest()})
    a = await any_pay.create_payment(pay_id=4124, amount=10, email="fafeqs@gmail.com")
    print(a)


loop = asyncio.get_event_loop()

#loop.run_until_complete(main())

