import streamlit as st
import json
import os
import requests
import io

# 1. KONFIGURÁCIÓ BETÖLTÉSE
def load_config():
    if not os.path.exists("config/config.json"):
        st.error("Hiba: A config/config.json fájl nem található a helyi gépeden!")
        st.stop()
    with open("config/config.json", "r") as f:
        return json.load(f)

config = load_config()

TERMÉK_ÁRAK = {
    "D": 14900,
    "STANDARD": 14900
}

def get_price_by_sku(sku):
    first_letter = sku[0].upper() if sku else ""
    return TERMÉK_ÁRAK.get(first_letter, TERMÉK_ÁRAK["STANDARD"])

# 2. AUTOMATA TOKEN IGÉNYLÉS (A CSV feltöltéshez szükséges OAuth)
def get_shopify_token():
    shop = config["shopify"]["shop_url"]
    client_id = config["shopify"]["client_id"]
    client_secret = config["shopify"]["client_secret"]
    
    url = f"https://{shop}/admin/oauth/access_token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        st.error(f"Shopify OAuth kapcsolódási hiba: {e}")
        return None

# 3. HIVATALOS CSV IMPORT INDÍTÁSA A SHOPIFY-ON (Képfeltöltés nélkül!)
def import_csv_to_shopify(token, csv_content):
    shop = config["shopify"]["shop_url"]
    # A Shopify REST API /admin/api/2026-07/inventory_items.json helyett a termék importálót hívjuk meg
    url = f"https://{shop}/admin/api/2026-07/product_imports.json"
    headers = {
        "X-Shopify-Access-Token": token
    }
    
    # A CSV tartalmat memóriafájllá alakítjuk a küldéshez
    files = {
        "file": ("products.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }
    
    try:
        res = requests.post(url, files=files, headers=headers)
        if res.status_code in [200, 201, 202]:
            return True
        else:
            st.error(f"Shopify CSV Import hiba ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        st.error(f"Nem sikerült a CSV-t elküldeni a Shopify-nak: {e}")
        return False


# STREAMLIT FELÜLET
st.set_page_config(page_title="DODO Studio v2", page_icon="🦖")
st.title("DODO Studio v2 🚀 (Biztonságos CSV-API Mód)")
st.markdown("---")

uploaded_files = st.file_uploader("Fájlok kiválasztása (pl: D0003_1.jpg)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
quantity = st.number_input("Darabszám (Készlet)", min_value=0, value=1)

if st.button("🚀 FELTÖLTÉS INDÍTÁSA") and uploaded_files:
    with st.spinner("Shopify API hozzáférés egyeztetése..."):
        token = get_shopify_token()
        
    if not token:
        st.error("Nem sikerült tokent szerezni a Shopify-tól.")
        st.stop()
        
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    processed_skus = set()
    
    # CSV Fejléc összeállítása a hivatalos Shopify formátumnak megfelelően
    csv_lines = ["Handle,Title,Body (HTML),Vendor,Custom Product Type,Tags,Published,Variant SKU,Variant Inventory Tracker,Variant Inventory Qty,Variant Inventory Policy,Variant Fulfillment Service,Variant Price,Variant Requires Shipping,Variant Taxable,Status"]
    
    for f in sorted_files:
        raw_filename = os.path.splitext(f.name)[0]
        
        if "_" in raw_filename:
            sku = raw_filename.split("_")[0].upper()
        else:
            sku = raw_filename.upper()
            
        if sku in processed_skus:
            continue
            
        product_price = get_price_by_sku(sku)
        st.write(f"✓ `{f.name}` feldolgozva $\rightarrow$ **SKU: {sku}**")
        
        handle = f"dodo-art-{sku.lower()}"
        title = f"DODO Art - [{sku}]"
        body = "<p>AI által generált leírás helye...</p>"
        
        # Egy sor hozzáadása a CSV-hez (fontos az idézőjelek kezelése a címeknél)
        line = f'{handle},"{title}","{body}",DODO Studio,Art,"DODO, Art",false,{sku},shopify,{int(quantity)},deny,manual,{float(product_price)},true,true,draft'
        csv_lines.append(line)
        processed_skus.add(sku)
        
    # Teljes CSV összefűzése szöveggé
    full_csv_content = "\n".join(csv_lines)
    
    with st.spinner("CSV generálása és háttér-import indítása a Shopify-on..."):
        # Beküldjük a Shopify-nak, hogy dolgozza fel a háttérben
        success = import_csv_to_shopify(token, full_csv_content)
        
        if success:
            st.success("🎉 A CSV-t a Shopify sikeresen befogadta! A háttérben pár másodpercen belül megjelennek a termékek a Products -> Drafts fül alatt.")
            st.balloons()