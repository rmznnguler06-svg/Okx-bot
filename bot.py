

import hmac
import hashlib
import base64
import time
import urllib.request
import urllib.error
import json

# --- OKX API AYARLARI ---
API_KEY = "d891a0b2-61f1-4f45-b41f-99f783c5f770"
API_SECRET = "4EB7E48BA71705331CFF56088EBDE3D9"
PASSPHRASE = "06Mekan18Vatan"

BASE_URL = "https://www.okx.com"

# --- RİSK YÖNETİMİ VE KASA AYARLARI ---
TOPLAM_KASA = 16.44         
Riske_Atilacak_Oran = 0.01   
STOP_CARPAN = 0.45           
HEDEF_CARPAN = 0.40          

STRATEGY_LIST = 

[

    {

        "coin": "PEPE-USDT-SWAP",

        "destek":0.4925 ,

        "direnc": 0.4725,

        "oran_050": 0.5,

        "ortalama_aralik": 2.75

    },

    {

        "coin": "TNSR-USDT-SWAP",

        "destek": 0.02648,

        "direnc":0.02679 ,

        "oran_050": 0.5,

        "ortalama_aralik": 1.15

    },

    {

        "coin": "DOGE-USDT-SWAP",

        "destek": 0.07384,

        "direnc":0.07457 ,

        "oran_050": 0.5,

        "ortalama_aralik": 0.98

    },

    {

        "coin": "ARKM-USDT-SWAP",

        "destek": 0.1126,

        "direnc": 0.1154,

        "oran_050": 0.5,

        "ortalama_aralik": 2.37

    }

]





   

def get_okx_sign(timestamp, method, request_path, body, secret_key):
    message = timestamp + method.upper() + request_path + body
    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode('utf-8')

def place_order(symbol, side, size, stop_price, hedef_price):
    endpoint = "/api/v5/trade/order"
    url = BASE_URL + endpoint
    
    payload = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size),
        "posSide": "long" if side == "buy" else "short",
        "tpTriggerPx": str(hedef_price),  
        "tpOrdPx": "-1",                  
        "slTriggerPx": str(stop_price),   
        "slOrdPx": "-1"                   
    }
    
    body = json.dumps(payload)
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.320Z', time.gmtime())
    sign = get_okx_sign(timestamp, "POST", endpoint, body, API_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE
    }
    
    req = urllib.request.Request(url, data=body.encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("code") == "0":
                print(f"✅ Emir ve Otomatik SL/TP Başarıyla Gönderildi ({symbol} - {side.upper()}) | Boyut: {size}")
                print(f"🎯 Hedef (TP): {hedef_price:.2f} | 🛑 Stop (SL): {stop_price:.2f}")
            else:
                print(f"⚠️ OKX Hata Yanıtı ({symbol}): {res}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ OKX Detaylı Red Yanıtı ({symbol}): {error_body}")
    except Exception as e:
        print(f"❌ Emir hatası ({symbol}): {e}")

def get_market_price(symbol):
    endpoint = f"/api/v5/market/ticker?instId={symbol}"
    url = BASE_URL + endpoint
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("code") == "0" and len(res.get("data", [])) > 0:
                return float(res["data"][0]["last"])
    except Exception as e:
        print(f"Fiyat çekme hatası ({symbol}): {e}")
    return None

def run_trading_bot():
    print(f"🚀 OKX Scalping Botu Başlatıldı (Kasa: {TOPLAM_KASA} USDT)...")
    
    coin_states = {
        item["coin"]: {
            "durum": "bekliyor" 
        } for item in STRATEGY_LIST
    }
    
    while True:
        try:
            zaman = time.strftime('%H:%M:%S')
            print(f"\n--- Tarama Döngüsü [{zaman}] ---")
            
            for item in STRATEGY_LIST:
                coin = item["coin"]
                price = get_market_price(coin)
                
                if price:
                    aralik = item["ortalama_aralik"]
                    stop_yuzde = aralik * STOP_CARPAN 
                    hedef_yuzde = aralik * HEDEF_CARPAN 
                    
                    izin_verilen_risk = TOPLAM_KASA * Riske_Atilacak_Oran
                    stop_oran_ondalik = stop_yuzde / 100
                    hedef_oran_ondalik = hedef_yuzde / 100
                    
                    pozisyon_boyutu_usdt = izin_verilen_risk / stop_oran_ondalik
                    islem_miktari_adet = pozisyon_boyutu_usdt / price
                    
                    print(f"{coin} Fiyat: {price} | Aralık: %{aralik}")
                    
                    destek = item["destek"]
                    direnc = item["direnc"]
                    oran = item["oran_050"] / 100.0  
                    state = coin_states[coin]
                    
                    destek_retest_long = destek * (1 + oran)     
                    destek_kirilim_short = destek * (1 - oran)  
                    direnc_retest_short = direnc * (1 - oran)    
                    direnc_kirilim_long = direnc * (1 + oran)    
                    
                    # --- DESTEK KONTROLLERİ ---
                    if price <= destek and state["durum"] == "bekliyor":
                        state["durum"] = "destek_değdi"
                        print(f"📌 {coin} Desteğe değdi!")
                    
                    if state["durum"] == "destek_değdi" and price >= destek_retest_long:
                        print(f"🚨 LONG ALARMI! (Destek değdi, %0.5 yukarı tepki geldi)")
                        stop_price = price * (1 - stop_oran_ondalik)
                        hedef_price = price * (1 + hedef_oran_ondalik)
                        place_order(coin, "buy", round(islem_miktari_adet, 4), stop_price, hedef_price)
                        state["durum"] = "bekliyor"
                        
                    if price < destek and state["durum"] != "destek_kırıldı":
                        state["durum"] = "destek_kırıldı"
                        print(f"⚠️ {coin} Destek kırıldı!")
                        
                    if state["durum"] == "destek_kırıldı" and price <= destek_kirilim_short:
                        print(f"🚨 SHORT ALARMI! (Destek kırıldı, %0.5 aşağı inildi)")
                        stop_price = price * (1 + stop_oran_ondalik)
                        hedef_price = price * (1 - hedef_oran_ondalik)
                        place_order(coin, "sell", round(islem_miktari_adet, 4), stop_price, hedef_price)
                        state["durum"] = "bekliyor"

                    # --- DİRENÇ KONTROLLERİ ---
                    if price >= direnc and state["durum"] == "bekliyor":
                        state["durum"] = "direnç_değdi"
                        print(f"📌 {coin} Dirence değdi!")
                        
                    if state["durum"] == "direnç_değdi" and price <= direnc_retest_short:
                        print(f"🚨 SHORT ALARMI! (Direnç değdi, %0.5 aşağı geri çekildi)")
                        stop_price = price * (1 + stop_oran_ondalik)
                        hedef_price = price * (1 - hedef_oran_ondalik)
                        place_order(coin, "sell", round(islem_miktari_adet, 4), stop_price, hedef_price)
                        state["durum"] = "bekliyor"
                        
                    if price > direnc and state["durum"] != "direnç_kırıldı":
                        state["durum"] = "direnç_kırıldı"
                        print(f"⚠️ {coin} Direnç kırıldı!")
                        
                    if state["durum"] == "direnç_kırıldı" and price >= direnc_kirilim_long:
                        print(f"🚨 LONG ALARMI! (Direnç kırıldı, %0.5 yukarı yükseldi)")
                        stop_price = price * (1 - stop_oran_ondalik)
                        hedef_price = price * (1 + hedef_oran_ondalik)
                        place_order(coin, "buy", round(islem_miktari_adet, 4), stop_price, hedef_price)
                        state["durum"] = "bekliyor"

                else:
                    print(f"{coin} fiyatı alınamadı.")
        except Exception as e:
            print(f"Döngü hatası: {e}")
        time.sleep(5)

if __name__ == "__main__":
    run_trading_bot()

