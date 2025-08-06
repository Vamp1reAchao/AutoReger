import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

class GetSMSAPI:
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.config = Config()
        self.base_url = self.config.GETSMS_BASE_URL
        
    async def _make_request(self, method: str = "GET", endpoint: str = "", data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        if headers is None:
            headers = {}
        
        headers['Authorization'] = f'Bearer {self.api_key}'
        headers['Content-Type'] = 'application/json'
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        return result
                else:
                    async with session.get(url, headers=headers) as response:
                        result = await response.json()
                        return result
        except Exception as e:
            logger.error(f"GetSMS API request failed: {e}")
            return {"ok": False, "error_code": "CONNECTION_ERROR"}
    
    async def get_balance(self) -> float:
        response = await self._make_request("GET", "account/get")
        
        if response.get("ok"):
            data = response.get("data", {})
            return float(data.get("balance", 0))
        else:
            logger.error(f"Failed to get balance: {response}")
            return 0.0
    
    async def get_price_and_country_name(self, country: str = "0") -> tuple[float, str]:
        try:
            country_name = await self.get_country_name(country)
            
            services = await self.get_services(country)
            
            telegram_service = None
            for service in services:
                service_name = service.get("name", "").lower()
                if "telegram" in service_name or "телеграм" in service_name:
                    telegram_service = service
                    break
            
            if telegram_service:
                price = telegram_service.get("price", 10.0)
                return float(price), country_name
            else:
                logger.warning(f"Telegram service not found for country {country}")
                return 10.0, country_name
                
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            country_name = "Любая страна" if country == "0" else f"Страна {country}"
            return 10.0, country_name
    
    async def get_countries(self) -> List[Dict]:
        response = await self._make_request("GET", "data/countries")
        
        if response.get("ok"):
            return response.get("items", [])
        else:
            logger.error(f"Failed to get countries: {response}")
            return []
    
    async def get_country_name(self, country_id: str) -> str:
        if country_id == "0":
            return "Любая страна"
            
        try:
            countries = await self.get_countries()
            for country in countries:
                if str(country.get("id")) == country_id:
                    return country.get("name", f"Страна {country_id}")
            return f"Страна {country_id}"
        except Exception as e:
            logger.error(f"Failed to get country name: {e}")
            return f"Страна {country_id}"
    
    async def get_price(self, country: str = "0") -> float:
        price, _ = await self.get_price_and_country_name(country)
        return price
    
    async def get_services(self, country_id: str) -> List[Dict]:
        response = await self._make_request("GET", f"data/services/{country_id}")
        
        if response.get("ok"):
            return response.get("items", [])
        else:
            logger.error(f"Failed to get services: {response}")
            return []
    
    async def search_service(self, country_id: str, query: str = "telegram") -> Optional[int]:
        services = await self.get_services(country_id)
        
        for service in services:
            service_name = service.get("name", "").lower()
            if "telegram" in service_name or "телеграм" in service_name:
                return service.get("id")
        
        logger.error(f"Service '{query}' not found for country {country_id}")
        return None
    
    async def create_order(self, service_id: int, country_id: str = "0") -> Tuple[Optional[str], Optional[str]]:
        data = {
            "service_id": service_id,
            "country_id": int(country_id) if country_id != "0" else 0
        }
        
        response = await self._make_request("POST", "orders/create", data)
        
        if response.get("ok"):
            order = response.get("order", {})
            phone = order.get("phone_number")
            order_id = str(order.get("id"))
            logger.info(f"Created order: {phone}, Order ID: {order_id}")
            return phone, order_id
        else:
            logger.error(f"Failed to create order: {response}")
            return None, None
    
    async def get_order_data(self, order_id: str) -> Optional[Dict]:
        response = await self._make_request("GET", f"orders/data/{order_id}")
        
        if response.get("ok"):
            return response.get("data")
        else:
            logger.error(f"Failed to get order data: {response}")
            return None
    
    async def get_sms(self, order_id: str) -> Optional[str]:
        order_data = await self.get_order_data(order_id)
        
        if order_data:
            sms_list = order_data.get("sms_list", [])
            if sms_list:
                sms_code = sms_list[0]
                logger.info(f"Got SMS code for order {order_id}: {sms_code}")
                return sms_code
        
        return None
    
    async def wait_for_sms(self, order_id: str, timeout: int = 300) -> Optional[str]:
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            sms_code = await self.get_sms(order_id)
            if sms_code:
                return sms_code
            
            await asyncio.sleep(5)
        
        logger.warning(f"SMS timeout for order {order_id}")
        return None
    
    async def finish_order(self, order_id: str) -> bool:
        data = {"order_id": int(order_id)}
        response = await self._make_request("POST", "orders/finish", data)
        
        if response.get("ok"):
            logger.info(f"Finished order {order_id}")
            return True
        else:
            logger.error(f"Failed to finish order {order_id}: {response}")
            return False
    
    async def get_number(self, country_id: str = "0") -> Tuple[Optional[str], Optional[str]]:
        service_id = await self.search_service(country_id, "telegram")
        
        if not service_id:
            logger.error(f"Telegram service not found for country {country_id}")
            return None, None
        
        return await self.create_order(service_id, country_id)
