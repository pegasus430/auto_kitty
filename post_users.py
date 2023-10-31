import requests
import base64
import json
import os
import csv
import re

url = "https://wanderlusttstg.wpengine.com//wp-json/wp/v2/users"
users_csv_file = 'author_names.csv'
user_id = "mihailo"
user_app_password = "bWOV MTvf MEB3 hWts DVKd zGpu"

credentials = user_id + ':' + user_app_password
token = base64.b64encode(credentials.encode())
header = {
        'Authorization': 'Basic ' + token.decode('utf-8')
    }

try:
    with open(users_csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        total_urls = sum(1 for row in csv_reader)  # Count the total number of URLs
        file.seek(0)  # Reset the file position to the beginning
        next(csv_reader)  # Skip the header row

        for index, row in enumerate(csv_reader, start=1):
            if index > 280:
                first_name = row.get('First Name')
                second_name = row.get('Second Name')
                payload = {
                    'username': f'{first_name} {second_name}',
                    'email': f'{first_name.lower()}{second_name.lower()}@example.com',
                    'password': 'password',
                    'roles': ["author"]
                }
                # print(payload)

                response = requests.request("POST", url, headers=header, data=payload)
                if response.status_code == 201:
                    print(f'  {index} user {first_name} has been added')
                           
            # print(extracted_data)
except FileNotFoundError:
        print(f"CSV file '{users_csv_file}' not found.")


response = requests.get(url, headers=header)
response = response.json()



