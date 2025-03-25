import os
import json
from datetime import datetime

def read_cookie_from_file(file_path):
    try:
        if not os.path.exists(file_path):
            print(f"Hata: {file_path} dosyası bulunamadı.")
            return None
            
        with open(file_path, 'r') as file:
            cookie = file.read().strip()
            if not cookie:
                print(f"Hata: {file_path} dosyası boş.")
                return None
            return cookie
    except Exception as e:
        print(f"Cookie dosyası okunurken hata oluştu: {str(e)}")
        return None 

def read_cookies_from_file(file_path):
    try:
        if not os.path.exists(file_path):
            print(f"Hata: {file_path} dosyası bulunamadı.")
            return []
            
        with open(file_path, 'r') as file:
            content = file.read().strip()
            if not content:
                print(f"Hata: {file_path} dosyası boş.")
                return []
                
            cookies = [line.strip() for line in content.split('\n') if line.strip()]
            return cookies
            
    except Exception as e:
        print(f"Cookie dosyası okunurken hata oluştu: {str(e)}")
        return []
        
def save_account_info(account_data, base_folder="hesaplar"):
    try:
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
            
        category = categorize_account(account_data)
        category_folder = os.path.join(base_folder, category)
        
        if not os.path.exists(category_folder):
            os.makedirs(category_folder)
            
        file_name = f"{account_data['username']}_{account_data['id']}.json"
        file_path = os.path.join(category_folder, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            account_data['scan_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            json.dump(account_data, file, indent=4, ensure_ascii=False)
            
        print(f"Hesap bilgileri kaydedildi: {file_path}")
        return True
        
    except Exception as e:
        print(f"Hesap bilgileri kaydedilirken hata oluştu: {str(e)}")
        return False
        
def categorize_account(account_data):
    is_premium = account_data.get('is_premium', False)
    
    robux = account_data.get('robux', 0)
    
    friend_count = account_data.get('friend_count', 0)
    
    game_count = account_data.get('game_count', 0)
    
    item_count = account_data.get('item_count', 0)
    
    if is_premium and robux >= 10000:
        return "premium_zengin"
    elif is_premium:
        return "premium"
    elif robux >= 10000:
        return "zengin"
    elif robux >= 1000:
        return "orta_seviye"
    elif game_count > 5 or item_count > 50:
        return "aktif_oyuncu"
    else:
        return "standart" 