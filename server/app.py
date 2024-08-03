import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
from helpers.openAPICalls import openApiCall
from helpers.imgurAPIUpload import imgurUpload
import certifi

class AtlasClient():

   def __init__ (self, altas_uri, dbname):
       self.mongodb_client = MongoClient(altas_uri, tlsCAFile=certifi.where())
       self.database = self.mongodb_client[dbname]

   ## A quick way to test if we can connect to Atlas instance
   def ping (self):
       self.mongodb_client.admin.command('ping')

   def get_collection (self, collection_name):
       collection = self.database[collection_name]
       return collection

   def find (self, collection_name, filter = {}, limit=0):
       collection = self.database[collection_name]
       items = list(collection.find(filter=filter, limit=limit))
       return items

load_dotenv(".env")

ATLAS_URI = os.getenv('MONGOURL')
DB_NAME = 'TEST'

atlas_client = AtlasClient (ATLAS_URI, DB_NAME)
atlas_client.ping()
print ('Connected to Atlas instance! We are good to go!')

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/testpayload/text', methods=['POST'])
def test_payload_text():
    collection = atlas_client.get_collection('test')
    collection.insert_one({'text': 'adasfsfds',
                            'number': 123})
    return "Success"

@app.route('/uploadImage', methods=['PUT'])
def upload_image():
    key = os.environ.get("OPENAI_API_KEY")
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == '':
        return "No selected file", 400

    if file:
        if os.name == 'nt':  # Windows
            file_path = os.path.join('.', file.filename)
        else:  # Unix-based systems (like Linux and macOS)
            file_path = os.path.join('/tmp', file.filename)

    file.save(file_path)
    image = imgurUpload(file_path)
    print('got image file')
    today = str(datetime.today().date())
    response = openApiCall(key, image)
    
    #Parsing the response into a dictionary
    response.message.content = response.message.content.replace('\n', '').replace('*','').split('content=', 1)[-1].split(', role=',1)[0]
    substrings = ['Description', 'Type of Waste', 'Biodegradable', 'Decompose Time', 'Approximate Weight', 'Dimensions', 'Amount of Liters of Water to Produce']
    
    #adds double quotes around the fields
    for substring in substrings:
        response.message.content = response.message.content.replace(substring, ', \"' + substring + '\"')
    
    #adds double quotes around the values
    response.message.content = response.message.content.replace(', \"', '\", \"').replace(': ', ': \"')
    response.message.content = response.message.content.replace('Title', '\"Title\"')
    response.message.content = '{\"' + response.message.content[1:-1] + '\" , \"image\": \"' + image + '\", \"date\": \"' + today + '\"}'

    collection = atlas_client.get_collection('Image Attributes')
    collection.insert_one(json.loads(response.message.content))
    print(response.message.content)
    return response.message.content

@app.route('/fetchhistory', methods=['GET'])
def fetch_history():
    collection = atlas_client.get_collection('Image Attributes')
    items = list(collection.find())

    # Convert ObjectId to string
    for item in items:
        item['_id'] = str(item['_id'])

    return jsonify(items)
if __name__ == '__main__':
    app.run(debug=True)