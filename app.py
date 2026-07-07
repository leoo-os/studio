import streamlit as st
import base64
import json
import os
from core.ai import AIEngine
from core.schema import ProductSchema, MemoryItem
from core.validator import SchemaValidator
from core.exporter import ShopifyExporter
from core.database import DatabaseManager

st.set_page_config(page_title="DODO Studio v2", page_icon="🦖", layout="centered")
st.title("🦖 DODO Studio v2")
st.write("Moduláris termékgenerátor automatizált API és Supabase szinkronizációval.")

# --- API KULCS AUTOMATIKUS BEOLVASÁSA A CONFIGBÓL ---
try:
    with open("config/config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    api_key = config_data["openai"]["api_key"]
    os.environ["OPENAI_API_KEY"] = api_key
except Exception:
    st.error("Kritikus hiba: Nem sikerült beolvasni az OpenAI API kulcsot a config/config.json fájlból!")
    st.stop()

uploaded_file = st.file_uploader("1. Lépés: Dodó kép feltöltése", type=["jpg", "jpeg", "png"])

st.subheader("2. Lépés: Felhasználói metaadatok")
col1, col2 = st.columns(2)
with col1:
    collection = st.text_input("Kollekció (pl. Geese)", value="")
    inventory_qty = st.number_input("Kezdő készlet", min_value=0, value=5, step=1)
with col2:
    function = st.text_input("Funkció (pl. Bowl)", value="")
    variant_name = st.text_input("Variáns név (opcionális)", value="")

if st.button("🚀 Termék feldolgozása és szinkronizálása"):
    if not api_key or api_key.startswith("sk-proj-IDE"):
        st.error("Kérlek add meg a valós OpenAI API kulcsodat a config/config.json fájlban!")
    elif not uploaded_file:
        st.error("Kérlek tölts fel egy termékfotót!")
    elif not collection or not function:
        st.error("A Kollekció és Funkció mezők kitöltése kötelező!")
    else:
        with st.spinner("Moduláris feldolgozás (Vision -> Emlékprofil -> Supabase -> CSV)..."):
            try:
                bytes_data = uploaded_file.getvalue()
                base64_image = base64.b64encode(bytes_data).decode('utf-8')
                full_filename = uploaded_file.name
                sku = full_filename.split('_')[0] if '_' in full_filename else full_filename.split('.')[0]

                ai_engine = AIEngine(api_key=api_key)
                raw_ai_data = ai_engine.analyze_and_generate(
                    base64_image=base64_image,
                    sku=sku,
                    collection=collection,
                    function=function,
                    variant=variant_name
                )

                price = "100.0" if "holder" in function.lower() else "50.0"

                memories_list = []
                for m in raw_ai_data["memories"]:
                    memories_list.append(MemoryItem(**m))

                tags_raw = raw_ai_data["seo"].get("tags", "")
                tags_list = [t.strip() for t in tags_raw.split(",")] if isinstance(tags_raw, str) else []

                product_object = ProductSchema(
                    sku=sku,
                    collection=collection,
                    size=raw_ai_data["visual"].get("Size", "Standard"),
                    function=function,
                    title=raw_ai_data["title"],
                    subtitle=f"A high-fired ceramic {function}",
                    finish=raw_ai_data["visual"].get("Finish", "Glossy"),
                    primary_color=raw_ai_data["visual"].get("Primary Colour", ""),
                    secondary_color=raw_ai_data["visual"].get("Secondary Colour", ""),
                    dimensions=raw_ai_data["visual"].get("Dimensions", ""),
                    character=raw_ai_data["visual"].get("Image ALT", ""),
                    html_description=raw_ai_data["html"].get("html_description", ""),
                    seo_title=raw_ai_data["seo"].get("seo_title", raw_ai_data["title"]),
                    seo_description=raw_ai_data["seo"].get("seo_description", ""),
                    tags=tags_list,
                    image_filename=full_filename,
                    image_public_url=f"https://leoolimited.com/cdn/shop/files/{full_filename}",
                    image_alt=raw_ai_data["visual"].get("Image ALT", ""),
                    memories=memories_list,
                    price=price,
                    inventory_qty=int(inventory_qty),
                    material="Ceramic",
                    variant_name=variant_name
                )

                if not SchemaValidator.validate_product(product_object):
                    st.error("Kritikus hiba: A termékadatok nem felelnek meg a DODO Standardnak!")
                    st.stop()

                csv_filename = f"shopify_import_{sku}.csv"
                csv_buffer = ShopifyExporter.generate_csv_buffer(product_object)

                db_manager = DatabaseManager()
                db_id = db_manager.save_product_flow(product_object, csv_filename)

                st.success(f"🎉 Sikeresen mentve a Supabase-be! (Termék ID: {db_id})")
                
                st.subheader("Előnézet:")
                st.write(f"**Cím:** {product_object.title}")
                st.write(f"**SKU:** {product_object.sku} | **Ár:** {product_object.price} €")
                st.write(f"**Legenerált emberi emlékek száma:** {len(product_object.memories)} db")

                st.download_button(
                    label="💾 Shopify Import CSV Letöltése",
                    data=csv_buffer,
                    file_name=csv_filename,
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"Hiba lépett fel a futtatáskor: {e}")