import streamlit as st
import json
import os
import requests
import uuid

# 1. KONFIGURÁCIÓ ÉS KLIENSEK
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

# 2. ÚJ TÍPUSÚ AUTOMATA TOKEN IGÉNYLÉS (2026+ Shopify OAuth)
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

# 3. KÉPFELTÖLTÉS NYERS MULTIPART KÓDOLÁSSAL (A GOOGLE SIGNATURE MIATT)
def upload_image_to_shopify(token, file_bytes, file_name):
    shop = config["shopify"]["shop_url"]
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    url = f"https://{shop}/admin/api/2026-07/graphql.json"
    
    staged_query = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets { url resourceUrl parameters { name value } }
        userErrors { field message }
      }
    }
    """
    try:
        # Engedély kérése a Shopify-tól
        res = requests.post(url, json={"query": staged_query, "variables": {"input": [{"filename": file_name, "mimeType": "image/jpeg", "resource": "FILE", "fileSize": str(len(file_bytes))}]}}, headers=headers).json()
        
        if "errors" in res or res.get("data", {}).get("stagedUploadsCreate", {}).get("userErrors"):
            st.error(f"Shopify Staged Upload hiba: {res}")
            return None
            
        target = res["data"]["stagedUploadsCreate"]["stagedTargets"][0]
        upload_url = target["url"]
        
        # --- NYERS MULTIPART MEGOLDÁS ---
        # Létrehozunk egy teljesen egyedi boundary-t
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        body_bytes = b""
        
        # 1. Hozzáadjuk a Shopify paramétereit SZIGORÚAN az eredeti sorrendben
        for p in target["parameters"]:
            body_bytes += f"--{boundary}\r\n".encode('utf-8')
            body_bytes += f'Content-Disposition: form-data; name="{p["name"]}"\r\n\r\n'.encode('utf-8')
            body_bytes += f"{p['value']}\r\n".encode('utf-8')
            
        # 2. A legvégére szúrjuk be a konkrét fájlt
        body_bytes += f"--{boundary}\r\n".encode('utf-8')
        body_bytes += f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode('utf-8')
        body_bytes += b"Content-Type: image/jpeg\r\n\r\n"
        body_bytes += file_bytes
        body_bytes += b"\r\n"
        
        # 3. Lezárjuk a teljes kérést
        body_bytes += f"--{boundary}--\r\n".encode('utf-8')
        
        # Elküldjük a Google-nek a kézzel felépített kérést
        gcloud_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        gcloud_res = requests.post(upload_url, data=body_bytes, headers=gcloud_headers)
        
        if gcloud_res.status_code not in [200, 201]:
            st.error(f"Tárhely feltöltési hiba ({gcloud_res.status_code}): {gcloud_res.text}")
            return None
            
        return target["resourceUrl"]
    except Exception as e:
        st.error(f"Képfeltöltési kivétel ({file_name}): {e}")
        return None

# 4. LÉTEZŐ TERMÉK KERESÉSE SKU ALAPJÁN
def find_shopify_product_by_sku(token, sku):
    shop = config["shopify"]["shop_url"]
    url = f"https://{shop}/admin/api/2026-07/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    query = """
    query($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
          }
        }
      }
    }
    """
    try:
        res = requests.post(url, json={"query": query, "variables": {"query": f"sku:{sku}"}}, headers=headers).json()
        edges = res["data"]["products"]["edges"]
        if edges:
            return edges[0]["node"]["id"]
        return None
    except:
        return None

# 5. ÚJ TERMÉK LÉTREHOZÁSA KÉSZLETTEL
def create_shopify_product(token, title, description, price, sku, image_url, quantity, location_id):
    shop = config["shopify"]["shop_url"]
    url = f"https://{shop}/admin/api/2026-07/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    query = """
    mutation productCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
      productCreate(input: $input, media: $media) {
        product { 
          id 
          title 
          variants(first: 1) {
            edges {
              node {
                id
                inventoryItem {
                  id
                }
              }
            }
          }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "title": title, 
            "descriptionHtml": f"<p>{description}</p>", 
            "status": "DRAFT", 
            "variants": [{"price": str(price), "sku": sku}]
        },
        "media": [{"mediaContentType": "IMAGE", "originalSource": image_url}]
    }
    
    res = requests.post(url, json={"query": query, "variables": variables}, headers=headers).json()
    
    if res.get("data", {}).get("productCreate", {}).get("userErrors"):
        st.error(f"Shopify terméklétrehozási hiba: {res['data']['productCreate']['userErrors']}")
    
    try:
        product_data = res["data"]["productCreate"]["product"]
        inventory_item_id = product_data["variants"]["edges"][0]["node"]["inventoryItem"]["id"]
        
        inventory_query = """
        mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
          inventorySetQuantities(input: $input) {
            userErrors { field message }
          }
        }
        """
        inventory_variables = {
            "input": {
                "name": "available",
                "reason": "correction",
                "quantities": [{
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id,
                    "quantity": int(quantity)
                }]
            }
        }
        requests.post(url, json={"query": inventory_query, "variables": inventory_variables}, headers=headers)
    except:
        pass
        
    return res

# 6. ÚJ KÉP HOZZÁADÁSA LÉTEZŐ TERMÉKHEZ
def append_image_to_product(token, product_id, image_url):
    shop = config["shopify"]["shop_url"]
    url = f"https://{shop}/admin/api/2026-07/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    query = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media { id }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": product_id,
        "media": [{"mediaContentType": "IMAGE", "originalSource": image_url}]
    }
    res = requests.post(url, json={"query": query, "variables": variables}, headers=headers).json()
    if res.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
        st.error(f"Galéria bővítési hiba: {res['data']['productCreateMedia']['userErrors']}")
    return res


# STREAMLIT FELÜLET
st.set_page_config(page_title="DODO Studio v2", page_icon="🦖")
st.title("DODO Studio v2 🚀")

uploaded_files = st.file_uploader("Fájlok kiválasztása (pl: D0001_1.jpg, D0001_2.jpg)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
quantity = st.number_input("Darabszám (Készlet)", min_value=0, value=1)

location_id = config["shopify"]["location_id"]

if st.button("🚀 FELTÖLTÉS INDÍTÁSA") and uploaded_files:
    with st.spinner("Shopify API hozzáférés egyeztetése..."):
        token = get_shopify_token()
        
    if not token:
        st.error("Nem sikerült tokent szerezni a Shopify-tól a megadott Client ID / Secret párossal.")
        st.stop()
        
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    
    for f in sorted_files:
        st.write("---")
        raw_filename = os.path.splitext(f.name)[0]
        
        if "_" in raw_filename:
            sku = raw_filename.split("_")[0].upper()
            view_number = raw_filename.split("_")[1]
        else:
            sku = raw_filename.upper()
            view_number = "1"
            
        product_price = get_price_by_sku(sku)
        st.markdown(f"📂 Fájl: `{f.name}` $\rightarrow$ **SKU: {sku}** (Nézet: {view_number})")
        
        with st.spinner(f"Feldolgozás..."):
            try:
                file_bytes = f.getvalue()
                existing_product_id = find_shopify_product_by_sku(token, sku)
                
                st.write("Kép feltöltése folyamatban...")
                img_url = upload_image_to_shopify(token, file_bytes, f.name)
                
                if not img_url:
                    st.error(f"A(z) {f.name} kép feltöltése megszakadt, ugrom a következőt.")
                    continue
                
                if existing_product_id:
                    st.write("Termék létezik, kép hozzáadása a galériához...")
                    append_image_to_product(token, existing_product_id, img_url)
                    st.success(f"✓ Kép hozzáadva a meglévő `{sku}` galériájához.")
                else:
                    st.write("Új termék létrehozása...")
                    ai_title = f"DODO Art - [{sku}]"
                    create_shopify_product(token, ai_title, "AI által generált leírás helye...", product_price, sku, img_url, quantity, location_id)
                    st.success(f"🎉 Új termék létrehozva `{sku}` néven, {quantity} db készlettel!")
                    
            except Exception as e:
                st.error(f"Hiba történt a fájl közben: {e}")
                
    st.balloons()