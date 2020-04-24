from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from modules import locate_model, locate_helper 
#from flask_cors import CORS, crossorigin
from flask_cors import CORS
import os
import sys
 
app = Flask(__name__)
CORS(app)

# add mongo url to flask config, so that flask_pymongo can use it to make connection
app.config["MONGO_URI"] = os.getenv('MONGO_URI')
mongo = PyMongo(app)

@app.route('/', methods=['GET', 'POST'])
def main():
    return 'ok'

@app.route('/api/v1/parishes', methods=['GET', 'POST'])
def place_sensors():
    '''
    returns recommended parishes based on user input (district/subcounty)
    '''
    district = 'WAKISO'
    subcounty = None
    sensor_number = None
    
    all_parishes = locate_model.get_parishes(district, subcounty)
    if len(all_parishes)<2:
        return 'Invalid input data'
    else:
        all_parishes_df = locate_helper.json_to_df(all_parishes)
        all_parishes_df = locate_helper.process_data(all_parishes_df)
        recommended_parishes = locate_helper.kmeans_algorithm(all_parishes_df, sensor_number)
        return jsonify(recommended_parishes)

@app.route('/api/v1/map/parishes', methods = ['POST'])
def place_sensors_map_trial():
    '''
    Returns parishes recommended by the model given the polygon and must-have coordinates
    '''
    if request.method == 'POST':
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400
        else:
            sensor_number = json_data["sensor_number"]
            #sensor_number = 10
            polygon = json_data["geometry"]["coordinates"]
            must_have_coordinates = json_data["must_have_coordinates"]
            #must_have_coordinates = [[32.59644375916393, 0.3529332145446762], [32.61814535019111, 0.3466625846873538], 
            #[32.61260713509556, 0.3258361619681596], [30.22042048778645, -0.6377219364867135]]

            return locate_helper.recommend_locations(sensor_number, must_have_coordinates, polygon)
            
           
if __name__ == "__main__":
   app.run()