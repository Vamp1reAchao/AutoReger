import re
import aiohttp
import asyncio
from typing import Tuple, Optional

def validate_proxy_format(proxy_string: str) -> bool:
    pattern = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5}):([^:]+):(.+)$'
    return bool(re.match(pattern, proxy_string))

def parse_proxy(proxy_string: str) -> Optional[Tuple[str, int, str, str]]:
    if not validate_proxy_format(proxy_string):
        return None
    
    parts = proxy_string.split(':')
    try:
        ip = parts[0]
        port = int(parts[1])
        username = parts[2]
        password = parts[3]
        return (ip, port, username, password)
    except (ValueError, IndexError):
        return None

async def test_proxy_connection(proxy_string: str, timeout: int = 10) -> bool:
    proxy_data = parse_proxy(proxy_string)
    if not proxy_data:
        return False
    
    ip, port, username, password = proxy_data
    proxy_url = f"http://{username}:{password}@{ip}:{port}"
    
    try:
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            test_urls = [
                "http://httpbin.org/ip",
                "http://icanhazip.com/"
            ]
            
            for url in test_urls:
                try:
                    async with session.get(
                        url, 
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            if ip in text:
                                return True
                except:
                    continue
            
            return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Proxy test failed for {ip}:{port} - {str(e)}")
        return False

def validate_phone_number(phone: str) -> bool:
    clean_phone = re.sub(r'\D', '', phone)
    
    return 7 <= len(clean_phone) <= 15

def validate_country_id(country_id: str) -> bool:
    return country_id.isdigit() and len(country_id) <= 4
