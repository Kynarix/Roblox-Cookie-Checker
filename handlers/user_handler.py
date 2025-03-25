class UserHandler:
    
    def __init__(self, roblox_api):
        self.roblox_api = roblox_api
        
    async def get_user_info(self, user):
        try:
            print("\n===== KULLANICI BİLGİLERİ =====")
            print(f"Kullanıcı adı: {user.name}")
            print(f"Kullanıcı ID: {user.id}")
            print(f"Görüntüleme adı: {user.display_name}")
            
            robux = await user.get_robux()
            print(f"Robux miktarı: {robux}")
            
            try:
                is_premium = await user.get_premium_membership()
                print(f"Premium üyelik: {'Var' if is_premium else 'Yok'}")
            except Exception:
                print("Premium üyelik bilgisi alınamadı")
            
            try:
                friends = await user.get_friends()
                print(f"Arkadaş sayısı: {len(friends)}")
            except Exception:
                print("Arkadaş listesi alınamadı")
                
        except Exception as e:
            print(f"Kullanıcı bilgileri alınırken hata: {str(e)}")
            
    async def get_user_games(self, user):
        try:
            games = await user.get_games()
            
            print("\n===== KULLANICININ OYUNLARI =====")
            if not games or len(games) == 0:
                print("Kullanıcının oyunu bulunamadı.")
                return
                
            for i, game in enumerate(games, 1):
                print(f"{i}. {game.name} (ID: {game.id})")
                
        except Exception as e:
            print(f"Oyunlar listelenirken bir hata oluştu: {str(e)}")

    async def get_user_inventory(self, user):
        try:
            items = await user.get_inventory_items()
            
            print("\n===== KULLANICININ ENVANTER ÖĞELERİ =====")
            if not items or len(items) == 0:
                print("Kullanıcının envanter öğesi bulunamadı veya görüntülenemiyor.")
                return
            categories = {}
            for item in items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)
            
            for category, items in categories.items():
                print(f"\n--- {category} ({len(items)} öğe) ---")
                for i, item in enumerate(items[:20], 1): 
                    price_info = ""
                    if item.recent_average_price:
                        price_info = f" | Son ortalama fiyat: {item.recent_average_price} Robux"
                    elif item.price:
                        price_info = f" | Fiyat: {item.price} Robux"
                    serial_info = f" | Seri No: {item.serial}" if item.serial else ""
                    
                    print(f"{i}. {item.name} (ID: {item.id}){price_info}{serial_info}")
                if len(items) > 20:
                    print(f"... ve {len(items) - 20} öğe daha")
                
        except Exception as e:
            print(f"Envanter öğeleri listelenirken bir hata oluştu: {str(e)}") 