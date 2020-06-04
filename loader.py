import requests
import json
from pprint import pprint
import csv
import time
from datetime import datetime, timedelta
from zipfile import ZipFile

def get_items_ids(shop_api_key, client_id):
	print("Getting ids...")
	headers = {
	  'Client-Id': str(client_id),
	  'Api-Key': shop_api_key,
	  'Content-Type': 'application/json'
	}
	payload = "{\n  \"filter\": {\n    \"visibility\": \"ALL\"\n  },\n  \"page\": 1,\n  \"page_size\": 1000\n}"
	r = requests.post(url="http://api-seller.ozon.ru/v1/product/list", headers=headers, data=payload)
	return r.json()

def get_product_parameters(product_id, offer_id, shop_api_key, client_id):
	headers = {
	  'Client-Id': str(client_id),
	  'Api-Key': shop_api_key,
	  'Content-Type': 'application/json'
	}
	payload = {
		"filter": {
			"offer_id": offer_id,
			"product_id": product_id
		}
	}
	return requests.post(url="http://api-seller.ozon.ru/v2/products/info/attributes", headers=headers, json=payload).json()

def get_sku(r):
	fbo, fbs = "", ""
	for i in r.get("sources", []):
		if i["source"] == "fbo":
			fbo = i["sku"]
		elif i["source"] == "fbs":
			fbs = i["sku"]
	return {
		"fbo": fbo,
		"fbs": fbs
	}

def get_item_state(state):
	if state == "": return ""
	if state == "processing": return "Информация о товаре добавляется в систему, ожидайте"
	if state == "moderating": return "Товар проходит модерацию, ожидайте"
	if state == "processed": return "Информация обновлена"
	if state == "failed_moderation": return "Товар не прошел модерацию"
	if state == "failed_validation": return "Товар не прошел валидацию"
	if state == "failed": return "Возникла неизвестная ошибка"
'''"Ширина, мм": str(params.get("width", "")).replace(".", ","),
		"Высота, мм": str(params.get("height", "")).replace(".", ","),
		"Глубина, мм": str(params.get("depth", "")).replace(".", ","),'''

def parse_date_short(s):
	if not s: return ""
	date = datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
	return date.strftime('%H:%M:%S %d-%m-%Y')

def parse_date_long(s):
	if not s: return ""
	date = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
	return date.strftime('%H:%M:%S %d-%m-%Y')

def get_item_info(product_id, offer_id, shop_api_key, client_id):
	headers = {
	  'Client-Id': str(client_id),
	  'Api-Key': shop_api_key,
	  'Content-Type': 'application/json'
	}
	payload = {
		"offer_id": offer_id,
		"product_id": product_id
	}
	r = requests.post(url="http://api-seller.ozon.ru/v2/product/info", headers=headers, json=payload).json()["result"]
	#arams = get_product_parameters(product_id, offer_id, shop_api_key, client_id)
	sku_ids = get_sku(r)
	result = {
		"Артикул": offer_id,
		"Ozon Product ID": product_id,
		"FBO OZON SKU ID": sku_ids["fbo"],
		"FBS OZON SKU ID": sku_ids["fbs"],
		"Barcode": r["barcode"],
		"Наименование товара": r["name"],
		"Статус товара": get_item_state(r.get("state", "")),
		"Видимость на сайте": "да" if r.get("visible", 0) else "нет",
		"Дата создания": parse_date_long(r.get("created_at", "")),
		"Доступно на складе, шт": str(r.get("stocks", {}).get("present", "")).replace(".", ","),
		"Текущая цена с учетом скидки, руб.": str(r.get("price", ""),).replace(".", ","),
		"Цена до скидки (перечеркнутая цена), руб.": str(r.get("old_price", "")).replace(".", ","),
		"Цена Premium, руб.": str(r.get("premium_price", "")).replace(".", ","),
		"Рыночная цена, руб.": str(r.get("recommended_price", "")).replace(".", ","),
		"Размер НДС, %": {"": "0", "0.000000": "0", "0.100000": "10%", "0.200000": "20%", }[str(r.get("vat", "0"))]
	}
	return result

def get_items_info(shop_api_key, client_id):
	init_time = time.time()
	print("Getting items...")
	id_list = get_items_ids(shop_api_key, client_id)["result"]["items"]
	print("Got", len(id_list), "items in:", str(time.time() - init_time), "s")
	items = []
	for item in id_list:
		product_id, offer_id = item["product_id"], item["offer_id"]
		items.append(get_item_info(product_id, offer_id, shop_api_key, client_id))
		print("+" + str(time.time() - init_time), "s")
	print("Got in:", str(time.time() - init_time), "s")
	return items

def dump_items_csv(shop_api_key, client_id, name):
	print("Dumping to", name + "_" + str(datetime.now()) + '_products.csv')
	employee_data = get_items_info(shop_api_key, client_id)
	client_id = str(client_id)
	filename = name + "_" + '_products.csv'
	data_file = open(filename, 'w+', encoding='utf-8-sig', newline='')
	csv_writer = csv.writer(data_file, delimiter=';')
	count = 0
	for emp in employee_data: 
	    if count == 0:
	        header = emp.keys() 
	        csv_writer.writerow(header) 
	        count += 1
	    csv_writer.writerow(emp.values())
	data_file.close()
	print("Dumped successfully.")

def get_postings_list(shop_api_key, client_id):
	print("Getting postings list...")
	init_time = time.time()
	headers = {
	  'Client-Id': str(client_id),
	  'Api-Key': shop_api_key,
	  'Content-Type': 'application/json'
	}
	payload = {
		"dir": "desc",
		"filter": {
			"since": (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z",
			"to": (datetime.now()).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"
		},
		"limit": 50,
		"offset": 0,
		"with": {
			"barcodes": False
		}
	}
	postings = []
	r = requests.post(url="http://api-seller.ozon.ru/v2/posting/fbs/list", headers=headers, json=payload).json()["result"]
	while r:
		postings.extend(r)
		payload["offset"] += 50
		print("Offset:", payload["offset"], "time:", str(time.time() - init_time), "s")
		r = requests.post(url="http://api-seller.ozon.ru/v2/posting/fbs/list", headers=headers, json=payload).json()["result"]
	print("Got", len(postings), "in:", str(time.time() - init_time), "s")
	return postings

def get_posting_status(s):
	if s == "": return ""
	if s == "awaiting_packaging": return "Ожидает упаковки"
	if s == "not_accepted": return "Не принят в сортировочном центре"
	if s == "arbitration": return "Ожидает решения спора"
	if s == "awaiting_deliver": return "Ожидает отгрузки"
	if s == "delivering": return "Доставляется"
	if s == "driver_pickup": return "У водителя"
	if s == "delivered": return "Доставлено"
	if s == "cancelled": return "Отменено"

def get_sum(price_str, q_str):
	if not (price_str and q_str): return ""
	return str(float(price_str) * float(q_str))

def get_posting_info(r):
	product = r.get("products", [{}])[0]
	result = {
		"Номер заказа": r.get("order_number", ""),
		"Номер отправления": r.get("posting_number", ""),
		"Дата создания заказа": parse_date_short(r.get("created_at", "")),
		"Дата отгрузки": parse_date_short(r.get("shipment_date", "")),
		"Статус": get_posting_status(r.get("status", "")),
		"Сумма отправления": get_sum(product.get("price", ""), product.get("quantity", "")).replace(".", ","),
		"Наименование товара": product.get("name", ""),
		"OZON id": product.get("sku", ""),
		"Артикул": product.get("offer_id", ""),
		"Итоговая стоимость товара": str(product.get("price", "")).replace(".", ","),
		"Количество": product.get("quantity", ""),
	}
	return result

def get_postings_info(shop_api_key, client_id):
	return [get_posting_info(i) for i in get_postings_list(shop_api_key, client_id)]

def dump_postings_csv(shop_api_key, client_id, name):
	print("Dumping to", name + "_" + str(datetime.now()) + '_postings.csv')
	employee_data = get_postings_info(shop_api_key, client_id)
	client_id = str(client_id)
	filename = name + "_" + '_postings.csv'
	data_file = open(filename, 'w+', encoding='utf-8-sig', newline='')
	csv_writer = csv.writer(data_file, delimiter=';')
	count = 0
	for emp in employee_data: 
	    if count == 0:
	        header = emp.keys() 
	        csv_writer.writerow(header) 
	        count += 1
	    csv_writer.writerow(emp.values())
	data_file.close()
	print("Dumped successfully.")

keys = {}

def load_keys():
	print("Loading keys...")
	with open('keys.csv', encoding='utf-8-sig') as csvfile:
		reader = csv.reader(csvfile, delimiter=';')
		count = 0
		for row in reader:
			if not count:
				count += 1
				continue
			name, shop_api_key, client_id = row
			keys[name] = {
				"shop_api_key": shop_api_key,
				"client_id": client_id,
			}
	print("Loaded.")

def dump_all_items():
	init_time = time.time()
	print("Dumping items...")
	for i in keys:
		try:
			start_time = time.time()
			print("Start:", start_time)
			dump_items_csv(keys[i]["shop_api_key"], keys[i]["client_id"], i)
			print(i, "--- %s seconds ---" % (time.time() - start_time))
		except Exception as e:
			print(e)
	print("Total items:", str(time.time() - init_time))
	print("Finished dumping items.")

def dump_all_postings():
	init_time = time.time()
	print("Dumping postings...")
	for i in keys:
		try:
			start_time = time.time()
			print("Start:", start_time)
			dump_postings_csv(keys[i]["shop_api_key"], keys[i]["client_id"], i)
			print(i, "--- %s seconds ---" % (time.time() - start_time))
		except Exception as e:
			print(e)
	print("Total postings:", str(time.time() - init_time))
	print("Finished dumping postings.")

def dump_all_markets():
	print("Initializing...")
	load_keys()
	print("Keys:")
	pprint(keys)
	print("==============")
	dump_all_items()
	dump_all_postings()

	print("Done.")
'''
start_time = time.time()
dump_items_csv("ff33baac-ec9e-4925-852c-c6a2fca38565", 49268)
print("--- %s seconds ---" % (time.time() - start_time))'''
#load_keys()
#dump_postings_csv("ff33baac-ec9e-4925-852c-c6a2fca38565", 49268, 'test')
dump_all_markets()