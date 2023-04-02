from flask import Flask, request, jsonify
import subprocess
import pymongo
from bson import json_util
from bson import ObjectId
import json
import os
import glob
from apscheduler.schedulers.background import BackgroundScheduler

job_defaults = {
    'coalesce': False,
    'max_instances': 1
}

scheduler = BackgroundScheduler()

mongo_client = pymongo.MongoClient(
    'mongodb+srv://vaibhav:vaib12345@vaibemsec.ioi6mqs.mongodb.net/')
mongo_db = mongo_client['Madhukar']   # Write your Collection Name

# create app
app = Flask(__name__)


def assetfinder(domain):

    assetfinder_cmd = f"assetfinder -subs-only {domain}"
    result = subprocess.run(assetfinder_cmd.split(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    subdomains = result.stdout.decode().splitlines()
    with open("assetfinder_subdomains.txt", "w") as f:
        f.write("\n".join(subdomains))

    output_dict = {}
    for subdomain in subdomains:
        nslookup_cmd = f"nslookup {subdomain}"
        result = subprocess.run(nslookup_cmd.split(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ip_address = result.stdout.decode().split()[-1]
        output_dict[subdomain] = ip_address

    with open("assetfinder_output.json", "w") as f:
        json.dump(output_dict, f)

    with open('assetfinder_output.json') as f:
        data = json.load(f)

    mongo_db.assetfinder.insert_one({
        'domain': domain,
        'subdomains': output_dict
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
    # domain_data = mongo_db.assetfinder.find_one({'domain': domain})


def censys(domain):

    censys_cmd = f"python3 censys-subdomain-finder/censys-subdomain-finder.py {domain}"
    result = subprocess.run(
        censys_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    censys_out = result.stdout.decode().splitlines()
    subdomains = censys_out[1:]
    with open("censys_subdomains.txt", "w") as f:
        f.write("\n".join(subdomains))

    output_dict = {}
    for subdomain in subdomains:
        nslookup_cmd = f"nslookup {subdomain}"
        result = subprocess.run(nslookup_cmd.split(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    # domain_data = mongo_db.censys.find_one({'domain': domain})


def knockpy(domain):

    knockpy_output = os.system(f'knockpy {domain}')

    directory_path = "/home/er_x/Downloads/Demo/knockpy_report/"  # your path
    all_files = glob.glob(os.path.join(directory_path, "*"))
    all_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = all_files[0]
    os.rename(latest_file, os.path.join(directory_path, "knockpy_output.json"))

    with open('knockpy_report/knockpy_output.json', 'r') as f:
        subdomain = json.load(f)

    mongo_db.knockpy.insert_one({'domain': domain, 'subdomains': subdomain})

    # domain_data = mongo_db.knockpy.find_one({'domain': domain})

    clear_space = os.system('rm knockpy_report/knockpy_output.json')


def subfinder(domain):

    subfinder_output = os.system(
        f'subfinder -d {domain} -o subfinder_output.json -oJ -nW')

    with open('subfinder_output.json') as f:
        output_data = []
        for line in f:
            output_data.append(json.loads(line))

    mongo_db.subfinder.insert_one({
        'domain': domain,
        'output': output_data,
    })

    if os.path.exists('subfinder_output.json'):
        os.remove('subfinder_output.json')
    else:
        print("File does not exist")

    # domain_data = mongo_db.subfinder.find_one({'domain': domain}, {"output.host": 1, "output.ip": 1, "_id": 0, "domain": 1})


@app.route('/search', methods=['POST'])
def search():
    req_json = request.json
    domains = req_json['domains']
    for domain in domains:
        db_verify = mongo_db.common_collection.find_one({'domain': domain})
        if db_verify is None:
            mongo_db.common_collection.insert_one(
                {'domain': domain, 'status': 'Scheduled'})

    return jsonify({"status": 200, "msg": "Collecting Subdomain Information. Use /getsubdomain and /getcompleteresult after 10 minutes for subdomain"})


@app.route('/getcompleteresult', methods=['POST'])
def final_result():
    req_json = request.json
    domains = req_json['domains']
    for domain in domains:
        db_verify = mongo_db.final.find_one({'domain': domain})
        if db_verify is None:
            return jsonify({"status": 404, "msg": "This domain does not exist. Please Wait"})
        else:
            doc = mongo_db.final.find_one({'domain': domain}, {'_id': 0, })
            return jsonify(doc)


@app.route('/getsubdomainresult', methods=['POST'])
def subdomain_result():
    req_json = request.json
    domains = req_json['domains']
    for domain in domains:
        db_verify = mongo_db.finalsubdomain.find_one({'domain': domain})
        if db_verify is None:
            return jsonify({"status": 404, "msg": "This domain does not exist. Please Wait"})
        else:
            doc = mongo_db.finalsubdomain.find_one(
                {'domain': domain}, {'_id': 0, })
            return jsonify(doc)


def all_tool():
    global flag
    if mongo_db.common_collection.count_documents({'status': 'Scheduled'}) > 0 and mongo_db.common_collection.count_documents({'status': 'Running'}) == 0:
        result = mongo_db.common_collection.find_one({'status': 'Scheduled'})

        mongo_db.common_collection.update_one({'_id': result.get("_id")}, {
                                              '$set': {'status': "Running"}})
        subdomain_list = set()
        knockpy(result.get("domain"))
        print("Knockpy compelted")
        sub1 = mongo_db.knockpy.find_one({'domain': result.get("domain")})
        for key in sub1['subdomains']:
            if key != '_meta':
                subdomain_list.add(key)

        subfinder(result.get("domain"))
        print("Subfinder compelted")
        sub2 = mongo_db.subfinder.find_one({'domain': result.get("domain")})
        for key in sub2['output']:
            subdomain_list.add(key['host'])

        censys(result.get("domain"))
        print("Censys compelted")
        sub3 = mongo_db.censys.find_one({'domain': result.get("domain")})
        for key in sub3['subdomains']:
            subdomain_list.add(key)

        assetfinder(result.get("domain"))
        print("Assetfinder compelted")
        sub4 = mongo_db.assetfinder.find_one({'domain': result.get("domain")})
        for key in sub4['subdomains']:
            subdomain_list.add(key)

        arr = []
        for subdomain in subdomain_list:
            ip = []

            if subdomain in sub1['subdomains'].keys():
                for knip in sub1['subdomains'][subdomain]['ipaddr']:
                    ip.append(knip)

            if subdomain in sub4['subdomains'].keys():
                ip.append(sub4['subdomains'][subdomain])

            if subdomain in sub3['subdomains'].keys():
                ip.append(sub3['subdomains'][subdomain])

            for key in sub2['output']:
                if subdomain == key['host']:
                    ip.append(key['ip'])

            obj = {"subdomain": subdomain, "ip": ip}

            arr.append(obj)

        if mongo_db.finalsubdomain.count_documents({'domain': result.get("domain")}) > 0:
            mongo_db.finalsubdomain.update_one({'domain': result.get("domain")}, {
                                               '$set': {'subdomain': list(subdomain_list)}})
        else:
            mongo_db.finalsubdomain.insert_one(
                {'domain': result.get("domain"), 'subdomain': list(subdomain_list)})

        if mongo_db.final.count_documents({'domain': result.get("domain")}) > 0:
            mongo_db.final.update_one({'domain': result.get("domain")}, {
                                      '$set': {'subdomain': arr}})
        else:
            mongo_db.final.insert_one(
                {'domain': result.get("domain"), 'subdomain': arr})

        mongo_db.assetfinder.drop()
        mongo_db.knockpy.drop()
        mongo_db.subfinder.drop()
        mongo_db.censys.drop()

        mongo_db.common_collection.update_one({'_id': result.get("_id")}, {
                                              '$set': {'status': "Done"}})


scheduler.add_job(all_tool, 'interval', seconds=60)

# Starts the Scheduled jobs
scheduler.start()

# Runs an infinite loop
if __name__ == '__main__':
    app.run(debug=True)
