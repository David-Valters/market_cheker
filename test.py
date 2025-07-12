data_file = 'data.json'
import json
data = {}

with open(data_file, 'r') as file:
    data = json.load(file)

for item in data:
    if "rarity:le" in item["tags"][0]:
        skin_id = item["id"]
        name = item.get("name", "Unknown Skin")
        print(f"Name: {name}")