import os
import zipfile
import time
import urllib.request
import ssl
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- Import ajouté pour webdriver-manager ---
from webdriver_manager.chrome import ChromeDriverManager

# --- Paramètres Proxy ---
proxy_host = 'brd.superproxy.io'
proxy_port = 33335
proxy_user = 'brd-customer-hl_6f4c5bd7-zone-datacenter1'
proxy_pass = 'v5ttvuka2n0x'

# --- Paramètres Vinted ---
VINTED_URL = "https://www.vinted.fr/catalog/1242-trainers"
OUTPUT_FILE = "vinted_elements_global_pages.json"
MAX_PAGES = 10

# --- Créer l'extension proxy ---
def create_proxy_extension():
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost"]
            }}
          }};

    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """

    pluginfile = 'proxy_auth_plugin.zip'

    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return pluginfile

# --- Fonction de Scraping Vinted (Méthode globale avec pagination) ---
def scrape_vinted_global_elements_with_proxy_pagination():
    print("Création de l'extension proxy...")
    pluginfile = create_proxy_extension()

    chrome_options = Options()
    chrome_options.add_extension(pluginfile)
    # --- Options Headless décommentées pour Render ---
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # --- Fin des options Headless ---
    chrome_options.add_argument("--start-maximized") # Utile en mode non headless

    # --- Code de gestion manuelle de chromedriver supprimé/commenté ---
    # driver_path = os.path.join(os.getcwd(), 'chromedriver')
    # if not os.path.exists(driver_path):
    #     print(f"Erreur : chromedriver non trouvé à l'emplacement : {driver_path}")
    #     print("Veuillez télécharger le chromedriver correspondant à votre version de Chrome et le placer au même endroit que le script.")
    #     return
    # service = Service(driver_path)
    # --- Fin du code supprimé/commenté ---


    print("Lancement de Chrome avec proxy pour Vinted...")
    driver = None
    # Liste globale pour stocker les articles de toutes les pages
    all_sneaker_items = []

    try:
        # --- Initialisation du Service via ChromeDriverManager ---
        print("Utilisation de webdriver-manager pour obtenir chromedriver...")
        service = Service(ChromeDriverManager().install())
        # --- Fin de l'initialisation ---

        driver = webdriver.Chrome(service=service, options=chrome_options)

        # --- Boucle sur les pages ---
        for page_num in range(1, MAX_PAGES + 1):
            print(f"\n--- Scraping de la page {page_num} ---")

            # Construire l'URL pour la page courante
            if page_num == 1:
                page_url = VINTED_URL
            else:
                # Ajoute &page=X. Vérifie si l'URL contient déjà des paramètres (?)
                if '?' in VINTED_URL:
                    page_url = f"{VINTED_URL}&page={page_num}"
                else:
                    # Si l'URL de base n'a pas de ?, ajoute ?page=X
                    page_url = f"{VINTED_URL}?page={page_num}"

            print(f"Ouverture de la page : {page_url}")
            driver.get(page_url)

            # --- Gérer les popups de cookies ou autres sur chaque page (peut apparaître à nouveau) ---
            try:
                WebDriverWait(driver, 5).until( # Temps d'attente réduit pour le popup sur les pages suivantes
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="cookie-banner"]'))
                )
                # Essayer de trouver et cliquer sur le bouton d'acceptation principal
                accept_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.web_ui__Button__primary'))
                )
                accept_button.click()
                print("Popup de cookies géré sur cette page.")
                WebDriverWait(driver, 5).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="cookie-banner"]'))
                )
            except (NoSuchElementException, TimeoutException):
                pass # Ignorer silencieusement si pas de popup
            except Exception as e:
                 print(f"Erreur lors de la gestion du popup sur la page {page_num} : {e}")


            # --- Extraction des données pour la page courante (Méthode globale) ---

            # Attendre la présence d'au moins UN des types d'éléments que l'on cherche
            print("Attente du chargement des éléments (images) sur la page courante...")
            try:
                # On attend plus longtemps pour le chargement initial des éléments sur chaque page
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.new-item-box__image img'))
                )
                print("Éléments (images) détectés sur la page courante.")
            except TimeoutException:
                print(f"Erreur : Timeout en attendant la présence des éléments images sur la page {page_num}. Passage à la page suivante.")
                continue # Passer à la prochaine itération de la boucle (prochaine page)


            # Trouver TOUS les éléments correspondant aux classes spécifiées sur toute la page courante
            print("Extraction des éléments par classe sur la page courante...")
            image_elements = driver.find_elements(By.CSS_SELECTOR, 'div.new-item-box__image img')
            description_elements = driver.find_elements(By.CSS_SELECTOR, 'div.new-item-box__description')
            price_elements = driver.find_elements(By.CSS_SELECTOR, 'span.web_ui__Text__text.web_ui__Text__subtitle.web_ui__Text__left.web_ui__Text__clickable.web_ui__Text__underline-none')

            print(f"Images trouvées : {len(image_elements)}")
            print(f"Descriptions trouvées : {len(description_elements)}")
            print(f"Prix trouvés : {len(price_elements)}")

            # Déterminer le nombre minimum d'éléments trouvés pour éviter les erreurs d'index
            min_elements = min(len(image_elements), len(description_elements), len(price_elements))

            if min_elements == 0:
                print(f"Aucun des éléments clés n'a été trouvé sur la page {page_num}.")
            else:
                print(f"Association et ajout de {min_elements} articles trouvés sur la page {page_num}...")
                # Parcourir jusqu'au minimum trouvé et associer les données par index
                for i in range(min_elements):
                    item_data = {}
                    try:
                        # Extraire l'image (src ou data-src)
                        img_elem = image_elements[i]
                        item_data['image'] = img_elem.get_attribute('src') if img_elem.get_attribute('src') else img_elem.get_attribute('data-src')

                        # Extraire le prix (texte)
                        price_elem = price_elements[i]
                        item_data['price'] = price_elem.text.strip()

                        # Extraire la description (texte)
                        desc_elem = description_elements[i]
                        item_data['name'] = desc_elem.text.strip()

                        # L'URL ne peut pas être associée de manière fiable avec cette méthode globale.
                        # item_data['url'] = None

                        # Ajouter l'article extrait à la liste globale
                        all_sneaker_items.append(item_data)

                    except IndexError:
                        print(f"Erreur d'index inattendue à l'élément {i} sur la page {page_num}.")
                        break # Arrêter l'association pour cette page
                    except Exception as e:
                        print(f"Erreur inattendue lors du traitement de l'élément {i} sur la page {page_num} : {e}. Élément ignoré.")
                        continue


            # --- Délai entre les pages ---
            if page_num < MAX_PAGES: # Pas besoin d'attendre après la dernière page
                 sleep_time = 2 # Délai en secondes
                 print(f"Attente de {sleep_time} secondes avant la page suivante...")
                 time.sleep(sleep_time)


        # --- Fin de la boucle sur les pages ---
        print(f"\n--- Scraping terminé. Total des articles collectés sur {MAX_PAGES} pages : {len(all_sneaker_items)} ---")


        # --- Sauvegarde des données (après avoir scrapé toutes les pages) ---
        if all_sneaker_items:
            try:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_sneaker_items, f, indent=4, ensure_ascii=False)

                print(f"Données de tous les articles extraits sauvegardées dans {OUTPUT_FILE}")
            except IOError as e:
                print(f"Erreur lors de l'écriture du fichier {OUTPUT_FILE} : {e}")
        else:
            print("Aucun article n'a pu être extrait sur toutes les pages. Fichier de sortie non créé.")

    except Exception as e:
        print(f"Une erreur majeure est survenue pendant le processus de scraping : {e}")

    finally:
        if driver:
            print("Fermeture du navigateur.")
            driver.quit()
        else:
            print("Le navigateur n'a pas pu être initialisé.")

# --- Point d'entrée du script ---
if __name__ == "__main__":
    scrape_vinted_global_elements_with_proxy_pagination()