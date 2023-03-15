from flask import Flask, request, jsonify
import subprocess
import pymongo
from bson import json_util
import json
import os

app = Flask(_name_)
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

    for domain in domains:
        db_verify = mongo_db.assetfinder.find_one({'domain': domain})

        if db_verify is None:
            assetfinder_cmd = f"assetfinder -subs-only {domain}"
            result = subprocess.run(assetfinder_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            subdomains = result.stdout.decode().splitlines()
            with open("assetfinder_subdomains.txt", "w") as f:
                f.write("\n".join(subdomains))

            output_dict = {}
            for subdomain in subdomains:
                nslookup_cmd = f"nslookup {subdomain}"
                result = subprocess.run(nslookup_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ip_address = result.stdout.decode().split()[-1]
                output_dict[subdomain] = ip_address

            with open("assetfinder_output.json", "w") as f:
                json.dump(output_dict, f)

            with open('assetfinder_output.json') as f:
                data = json.load(f)

         
            mongo_db.assetfinder.insert_one({
                'domain': domain,
                'subdomains' : output_dict
            })

            if os.path.exists('assetfinder_subdomains.txt'):
                os.remove('assetfinder_subdomains.txt')
            else:
                print("File does not exist")
            
            if os.path.exists('assetfinder_output.json'):
                os.remove('assetfinder_output.json')
            else:
                print("File does not exist")

        # Retrieve data from MongoDB
        domain_data = mongo_db.assetfinder.find_one({'domain': domain})
        results.append(domain_data)

    json_results = json_util.dumps(results)
    return jsonify(json_results)

if _name_ == '_main_':
    app.run(debug=True)
