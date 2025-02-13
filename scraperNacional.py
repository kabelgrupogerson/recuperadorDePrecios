import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def scrape_data():
    data = []
    page = 1
    while True:
        url = f"https://nalelectricos.co/?filter=true&product_cat=conductores-electricos&page={page}"
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        products = soup.select("li.product")
        if not products:
            break

        for p in products:
            name_el = p.select_one("h3.entry-title.de_title_module.product_title")
            price_elems = p.select("span.woocommerce-Price-amount.amount")
            name = name_el.get_text(strip=True) if name_el else "No name"
            final_price = price_elems[-1].get_text(strip=True) if price_elems else "No price"
            data.append((name, final_price))

        next_link = soup.select_one("a.page-numbers.next")
        if not next_link:
            break
        page += 1

    return data

def update_sheet(data):
    SERVICE_ACCOUNT_FILE = "service_account.json"
    SPREADSHEET_ID = "19Mjib83ZDFXCGZ60ph99F6rBgmNKk26lmMGERPU_-Ao"

    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # Read existing data
    all_rows = sheet.get_all_values()  # Row 0 is headers: ["product-title", "price"]
    existing_map = {}
    for i, row in enumerate(all_rows[1:], start=2):  # actual sheet row is i
        if row:
            product_title = row[0]
            existing_map[product_title] = i

    # Prepare batch updates (existing rows) and a single append for new rows
    batch_updates = []
    new_rows = []

    for (name, price) in data:
        if name in existing_map:
            row_idx = existing_map[name]
            # We'll update column B at row_idx
            batch_updates.append({
                "range": f"B{row_idx}:B{row_idx}",
                "values": [[price]]
            })
        else:
            new_rows.append([name, price])

    # Send one batch update request
    if batch_updates:
        sheet.batch_update(batch_updates)

    # Append all new rows at once
    if new_rows:
        sheet.append_rows(new_rows, value_input_option="RAW")

def main():
    scraped_data = scrape_data()
    update_sheet(scraped_data)

if __name__ == "__main__":
    main()
