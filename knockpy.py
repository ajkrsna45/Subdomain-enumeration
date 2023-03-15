from flask import Flask, request, jsonify
import os
import pymongo
from bson import json_util
import json
import glob

app = Flask(__name__)
mongo_client = pymongo.MongoClient('mongodb+srv://vaibhav:vaib12345@vaibemsec.ioi6mqs.mongodb.net/')
mongo_db = mongo_client['SubTest']

@app.route('/')
def home():
    return "Welcome to the knockpy app!"

@app.route('/search', methods=['POST'])
def search():
    req_json = request.json
    domains = req_json['domains']
    results = []

    for domain in domains:
        db_verify = mongo_db.knockpy.find_one({'domain': domain})

        if db_verify is None:
            knockpy_output = os.system(f'knockpy {domain}')
            

            directory_path = "/home/er_x/Downloads/demo/knockpy_report"
            all_files = glob.glob(os.path.join(directory_path, "*"))
            all_files.sort(key=os.path.getmtime, reverse=True)
            latest_file = all_files[0]
            os.rename(latest_file, os.path.join(directory_path, "knockpy_output.json"))


            with open('knockpy_report/knockpy_output.json','r') as f:
                subdomain= json.load(f)
               
            mongo_db.knockpy.insert_one({
                'domain': domain,
                'subdomains' :subdomain,
            })

        # Retrieve data from MongoDB
        
        domain_data = mongo_db.knockpy.find_one({'domain': domain})

        results.append(domain_data)

        clear_space = os.system('rm knockpy_report/knockpy_output.json')

    json_results = json_util.dumps(results)
    return jsonify(json_results)

if __name__ == '__main__':
    app.run(debug=True)
