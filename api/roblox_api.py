import requests
from ro_py import Client
from config.settings import USER_AGENT

class RobloxAPI:
    def __init__(self, cookie):
        self.cookie = self._format_cookie(cookie)
        self.headers = {
            'Cookie': self.cookie,
            'User-Agent': USER_AGENT,
        }
        self.client = None
        
    def _format_cookie(self, cookie):
        if not cookie.startswith('.ROBLOSECURITY='):
            return f'.ROBLOSECURITY={cookie}'
        return cookie
        
    async def initialize_client(self):
        try:
            self.client = Client(self.cookie)
            
            return True
        except Exception as e:
            print(f"Client başlatılırken hata: {str(e)}")
            return False
            
    def get_headers(self):
        return self.headers 