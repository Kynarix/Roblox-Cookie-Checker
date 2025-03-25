import requests
from api.roblox_api import RobloxAPI

class AuthHandler:
    def __init__(self, roblox_api):
        self.roblox_api = roblox_api
        
    async def login(self):
        try:
            init_success = await self.roblox_api.initialize_client()
            if not init_success:
                return False, "API client başlatılamadı"
            client = self.roblox_api.client
            
            try:
                user_info_url = "https://users.roblox.com/v1/users/authenticated"
                response = requests.get(user_info_url, headers=self.roblox_api.get_headers())
                
                if response.status_code == 200:
                    user_data = response.json()
                    user_id = user_data.get("id")
                    
                    detailed_info_url = f"https://users.roblox.com/v1/users/{user_id}"
                    detailed_response = requests.get(detailed_info_url)
                    if detailed_response.status_code == 200:
                        detailed_data = detailed_response.json()
                        
                        class User:
                            def __init__(self, data):
                                self.id = data.get("id")
                                self.name = data.get("name")
                                self.display_name = data.get("displayName")
                                self.roblox_api = None
                                
                            async def get_robux(self):
                                try:
                                    currency_url = "https://economy.roblox.com/v1/user/currency"
                                    robux_response = requests.get(currency_url, headers=self.roblox_api.get_headers())
                                    if robux_response.status_code == 200:
                                        return robux_response.json().get("robux", 0)
                                    return 0
                                except:
                                    return 0
                                    
                            async def get_premium_membership(self):
                                try:
                                    premium_url = "https://premiumfeatures.roblox.com/v1/users/validate-membership"
                                    premium_response = requests.get(premium_url, headers=self.roblox_api.get_headers())
                                    return premium_response.status_code == 200
                                except:
                                    return False
                                    
                            async def get_friends(self):
                                try:
                                    friends_url = f"https://friends.roblox.com/v1/users/{self.id}/friends"
                                    friends_response = requests.get(friends_url)
                                    if friends_response.status_code == 200:
                                        return friends_response.json().get("data", [])
                                    return []
                                except:
                                    return []
                                    
                            async def get_games(self):
                                try:
                                    games_url = f"https://games.roblox.com/v2/users/{self.id}/games"
                                    games_response = requests.get(games_url)
                                    if games_response.status_code == 200:
                                        games_data = games_response.json().get("data", [])
                                        
                                        class Game:
                                            def __init__(self, game_data):
                                                self.id = game_data.get("id", 0)
                                                self.name = game_data.get("name", "Bilinmeyen Oyun")
                                                
                                        return [Game(game) for game in games_data]
                                    return []
                                except:
                                    return []
                            
                            async def get_inventory_items(self):
                                inventory = []
                                
                                try:
                                    item_types = [
                                        {"url": f"https://inventory.roblox.com/v1/users/{self.id}/items/Asset/", "name": "Genel Öğeler"},
                                        {"url": f"https://inventory.roblox.com/v1/users/{self.id}/items/GamePass/", "name": "Oyun Geçişleri"},
                                        {"url": f"https://inventory.roblox.com/v1/users/{self.id}/assets/collectibles", "name": "Koleksiyon Öğeleri"},
                                        {"url": f"https://avatar.roblox.com/v1/users/{self.id}/outfits", "name": "Kıyafetler"}
                                    ]
                                    
                                    for item_type in item_types:
                                        response = requests.get(item_type["url"], headers=self.roblox_api.get_headers())
                                        
                                        if response.status_code == 200:
                                            data = response.json()
                                            
                                            if "data" in data:
                                                items = data["data"]
                                            elif "items" in data:
                                                items = data["items"]
                                            else:
                                                items = []
                                            class Item:
                                                def __init__(self, item_data, category):
                                                    self.id = item_data.get("id", 0)
                                                    self.name = item_data.get("name", "")
                                                    self.type = item_data.get("type", "")
                                                    self.category = category
                                                    self.assetId = item_data.get("assetId", 0)
                                                    self.price = item_data.get("price", 0)
                                                    self.serial = item_data.get("serialNumber", None)
                                                    self.recent_average_price = item_data.get("recentAveragePrice", 0)
                                                    self.asset_stock = item_data.get("assetStock", 0)
                                                    
                                            for item in items:
                                                inventory.append(Item(item, item_type["name"]))
                                except Exception as e:
                                    print(f"Envanter öğeleri alınırken hata: {str(e)}")
                                    
                                return inventory
                        
                        user = User(detailed_data)
                        return True, user
                    
                return False, "Kullanıcı bilgileri alınamadı"
                
            except Exception as e:
                return False, f"Kullanıcı bilgileri alınırken hata: {str(e)}"
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid cookie" in error_msg or "Unauthorized" in error_msg:
                return False, "Geçersiz cookie. Lütfen doğru bir .ROBLOSECURITY cookie değeri girin."
            return False, f"Giriş yapılırken bir hata oluştu: {error_msg}" 