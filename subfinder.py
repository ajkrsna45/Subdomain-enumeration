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
    return "Welcome to the subfinder app!"

@app.route('/search', methods=['POST'])
def search():
    req_json = request.json
    domains = req_json['domains']
    results = []

    for domain in domains:
        db_verify = mongo_db.subfinder.find_one({'domain': domain})

        if db_verify is None:
            subfinder_output = subprocess.check_output(['subfinder', '-d', domain, '-o', 'subfinder_output.json', '-oJ', '-nW']).decode()
            subdomains = subfinder_output.strip().split('\n')

            with open('subfinder_output.json') as f:
                output_data = []
                for line in f:
                    output_data.append(json.loads(line))

            mongo_db.subfinder.insert_one({
                'domain': domain,
                'subdomains': subdomains,
                'output': output_data,
            })

            # Remove subfinder output file
            if os.path.exists('subfinder_output.json'):
                os.remove('subfinder_output.json')
            else:
                print("File does not exist")

        # Retrieve data from MongoDB
        domain_data = mongo_db.subfinder.find_one({'domain': domain},{"output.host":1, "output.ip":1,"_id":0 ,"domain":domain})
        results.append(domain_data)

    json_results = json_util.dumps(results)
    return jsonify(json_results)

if __name__ == '__main__':
    app.run(debug=True)