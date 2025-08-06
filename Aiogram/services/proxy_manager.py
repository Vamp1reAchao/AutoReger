import logging
import random
from typing import List, Optional, Tuple, Dict
from utils.validators import validate_proxy_format, parse_proxy, test_proxy_connection
from config import Config

logger = logging.getLogger(__name__)

class ProxyManager:
    
    def __init__(self):
        self.config = Config()
        self.proxies: List[str] = []
        self.working_proxies: List[str] = []
        self.used_proxies: List[str] = []
    
    async def load_proxies(self) -> int:
        try:
            with open(self.config.PROXY_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.proxies = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if validate_proxy_format(line):
                        self.proxies.append(line)
                        logger.debug(f"Added proxy: {line}")
                    else:
                        logger.warning(f"Invalid proxy format on line {line_num}: '{line}'")
            
            logger.info(f"Loaded {len(self.proxies)} proxies from file")
            if len(self.proxies) == 0:
                logger.warning("No valid proxies found in file")
            return len(self.proxies)
            
        except FileNotFoundError:
            logger.warning(f"Proxy file not found: {self.config.PROXY_FILE}")
            return 0
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return 0
    
    async def test_all_proxies(self) -> int:
        if not self.proxies:
            logger.warning("No proxies to test")
            return 0
        
        logger.info(f"Testing {len(self.proxies)} proxies...")
        self.working_proxies = []
        
        for proxy in self.proxies:
            logger.info(f"Testing proxy: {proxy}")
            if await test_proxy_connection(proxy):
                self.working_proxies.append(proxy)
                logger.info(f"✓ Proxy working: {proxy}")
            else:
                logger.warning(f"✗ Proxy failed: {proxy}")
        
        logger.info(f"Found {len(self.working_proxies)} working proxies")
        return len(self.working_proxies)
    
    def get_random_proxy(self) -> Optional[str]:
        available_proxies = [p for p in self.working_proxies if p not in self.used_proxies]
        
        if not available_proxies:
            if self.working_proxies:
                self.used_proxies = []
                available_proxies = self.working_proxies
            else:
                return None
        
        proxy = random.choice(available_proxies)
        self.used_proxies.append(proxy)
        return proxy
    
    def get_proxy_config(self, proxy_string: str) -> Optional[Tuple]:
        proxy_data = parse_proxy(proxy_string)
        if not proxy_data:
            return None
        
        ip, port, username, password = proxy_data
        
        try:
            import socks
            return (socks.HTTP, ip, port, True, username, password)
        except ImportError:
            logger.error("PySocks module not found. Install it with: pip install PySocks")
            return None
    
    def reset_used_proxies(self):
        self.used_proxies = []
        logger.info("Reset used proxies list")
    
    def get_stats(self) -> Dict:
        return {
            'total_loaded': len(self.proxies),
            'working_proxies': len(self.working_proxies),
            'used_proxies': len(self.used_proxies),
            'available_proxies': len(self.working_proxies) - len(self.used_proxies)
        }
