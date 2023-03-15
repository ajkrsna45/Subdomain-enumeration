from flask import Flask, request, jsonify
import subprocess
import pymongo
from bson import json_util
import json
import os

app = Flask(__name__)
mongo_client = pymongo.MongoClient('mongodb+srv://vaibhav:vaib12345@vaibemsec.ioi6mqs.mongodb.net/')
mongo_db = mongo_client['SubTest']

@app.route('/')
def home():
    return "Welcome to the Demo app!"

@app.route('/search', methods=['POST'])
def search():
    req_json = request.json
    domains = req_json['domains']
    results = []

#   CENSYS_API_ID="cde5d4b9-9e77-4dbf-b039-215767500a61"
#   CENSYS_API_SECRET="MMY8nlI42amCyXcBJYEdTs360IaodQZ0"

    for domain in domains:
        db_verify = mongo_db.censys.find_one({'domain': domain})

        if db_verify is None:
            censys_cmd = f"python3 censys-subdomain-finder/censys-subdomain-finder.py {domain}"
            result = subprocess.run(censys_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            censys_out = result.stdout.decode().splitlines()
            subdomains = censys_out[1:]
            with open("censys_subdomains.txt", "w") as f:
                f.write("\n".join(subdomains))

            output_dict = {}
            for subdomain in subdomains:
                nslookup_cmd = f"nslookup {subdomain}"
                result = subprocess.run(nslookup_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ip_address = result.stdout.decode().split()[-1]
                output_dict[subdomain] = ip_address

            with open("censys_output.json", "w") as f:
                json.dump(output_dict, f)

            with open('censys_output.json') as f:
                data = json.load(f)

            mongo_db.censys.insert_one({'domain': domain, 'subdomains': output_dict})

            if os.path.exists('censys_subdomains.txt'):
                os.remove('censys_subdomains.txt')
            else:
                print("File does not exist")
            
            if os.path.exists('censys_output.json'):
                os.remove('censys_output.json')
            else:
                print("File does not exist")

        # Retrieve data from MongoDB
        domain_data = mongo_db.censys.find_one({'domain': domain})
        results.append(domain_data)

    json_results = json_util.dumps(results)
    return jsonify(json_results)

if __name__ == '__main__':
    app.run(debug=True)