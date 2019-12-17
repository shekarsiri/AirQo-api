
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#import seaborn as sns

from math import sqrt
from numpy import split
from numpy import array
from pandas import read_csv
from sklearn.metrics import mean_squared_error

from multiprocessing import cpu_count
from joblib import Parallel
from joblib import delayed
from warnings import catch_warnings
from warnings import filterwarnings
from statsmodels.tsa.statespace.sarimax import SARIMAX

from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.graphics.tsaplots import plot_pacf

import datetime
import time 

import psutil
import ast

import json

import datamanagement 


# Creating a list of channels to iterate through
static_channel_list = datamanagement.get_all_static_channels()
data = datamanagement.query_data()
#TODO: READ DATA FROM BIGQUERY....
hourly_data = datamanagement.calculate_hourly_averages(data)

print(hourly_data.head())

def full_days_only(d):
    ###  Interpolating gaps within the data and presenting in necessary format ####
    d = d.set_index('time')
    d = d.interpolate(method='time');
    # drop any remaining nans from the start
    d =  d.dropna().reset_index();
    print(d)
    # Setting first complete day and last complete day to assist with training quality
    first_full_day = pd.to_datetime(d.loc[d.time.dt.hour == 0.00, 'time'][:1].values[0], utc=True)
    last_full_day = pd.to_datetime(d.loc[d.time.dt.hour == 23.00, 'time'][-1:].values[0], utc=True)  
    # Then correct Kampala values are applied
    d_whole_days = d.loc[(d.time >= first_full_day) & (d.time <= last_full_day)]
    d_whole_days = d_whole_days.set_index('time')
    #print(d_whole_days)
    return d_whole_days


# THis should be unecessary but every time i take it out it causes issues
def out_of_sample(d, oos_size):
    df = d.iloc[:-oos_size, 1]
    oos = d.iloc[-oos_size:, 1]
    return df, oos



def plot_acf_pcf(df, lags):
    # plots specifying number of lags to include
    plt.figure(figsize=(20,6))
    # acf
    axis = plt.subplot(2, 1, 1)
    plot_acf(df, ax=axis, lags=lags)
    # pacf
    axis = plt.subplot(2, 1, 2)
    plot_pacf(df, ax=axis, lags=lags)
    # show plot
    #print(chan)
    plt.show()


def split_dataset(data):
    # split into standard weeks with 1 week validation and 1 day oos test
    train, test = data[0:-192], data[-192:-24]
    final_test = data[-24:]
    # restructure into windows of weekly data
    train = array(split(train, (len(train)/24)))
    test = array(split(test, (len(test)/24)))
#     print(train, test, final_test)
    return train, test, final_test


 # convert windows of weekly multivariate data into a series of total power
def to_series(data):
    # extract just the total power from each week
    series = [day for day in data]
    # flatten into a single series
    series = array(series).flatten()
    return series


# sarima forecast
# Takes the history (train set plus day by day testing) and configuration
# converts history values to a single long series
# generates the sarima model based on config parameters
# fits the sarima model to the series data
# creates yhat, a prediction of the next 24 hours int he test set
def sarima_forecast(history, config):
    order, sorder, trend = config
    # convert history into a univariate series
    series = to_series(history)
    # define model
    model = SARIMAX(series, order=order, seasonal_order=sorder, trend = trend,enforce_stationarity=False, enforce_invertibility=False)
#     model = SARIMAX(history, order=order, seasonal_order=sorder, trend=trend, enforce_stationarity=False, enforce_invertibility=False)
    # fit model
    model_fit = model.fit(disp=False)
    # make one step forecast
    yhat = model_fit.predict(len(series), len(series)+23)
    return yhat



# evaluate a single model which creates a prediction for ech day and each hour
# This is then fed into the evaluate forecast function to generate overall scores for the model
# for the model
# This needs to happen for every incarnation of the model
def evaluate_model(model_func, train, test, config):
    # history is a list of weekly data
    history = [x for x in train]
    # walk-forward validation over each week
    predictions = list()
    for i in range(len(test)):
        # predict the week

        yhat_sequence = model_func(history, config)
        # store the predictions
        predictions.append(yhat_sequence)
        # get real observation and add to history for predicting the next week
        history.append(test[i, :])
    predictions = array(predictions)
    # evaluate predictions days for each week
    score, scores = evaluate_forecasts(test, predictions)
    return score, scores


def evaluate_forecasts(actual, predicted):
#     print('actual.shape : ', actual.shape)
#     print('predicted.shape', predicted.shape)
    scores = list()
    # calculate an RMSE score for each day
    for i in range(actual.shape[1]):
        # calculate mse
        print('i', i)
        mse = mean_squared_error(actual[:, i], predicted[:, i])
        print('mse', mse)
        # calculate rmse
        rmse = sqrt(mse)
        print('rmse', rmse)
        # store
        scores.append(rmse)
    s = 0
    for row in range(actual.shape[0]):
        for col in range(actual.shape[1]):
            s += (actual[row, col] - predicted[row, col])**2
    score = sqrt(s / (actual.shape[0] * actual.shape[1]))
#     return score, scores
#     print('score, scores: ', score, scores)

    return score, scores


# summarize scores
#Takes the name, model score and list of hourly mean scores
#print
def summarize_scores(name, score, scores):
    s_scores = ', '.join(['%.1f' % s for s in scores])
    print('%s: [%.3f]' % (name, score))



# create a set of sarima configs to try
def sarima_configs():
    models = list()
    # define config lists
#     p_params = [0,1,2]
    p_params = [2]
    d_params = [0]
#     q_params = [0,1,2]        
    q_params = [24]
#     t_params = ['n','c','t','ct']
    t_params = ['c']
    P_params = [1]
    D_params = [0]
    Q_params = [1]
    m_params = [24]
    # create config instances
    for p in p_params:
        for d in d_params:
            for q in q_params:
                for t in t_params:
                    for P in P_params:
                        for D in D_params:
                            for Q in Q_params:
                                for m in m_params:
                                    cfg = [(p,d,q), (P,D,Q,m), t]
                                    models.append(cfg)
    return models


# root mean squared error or rmse
def measure_rmse(actual, predicted):
    return sqrt(mean_squared_error(actual, predicted))


# grid search configs
# Using train, test data and the list of configurations
# working in parallel


# def grid_search(data, cfg_list, n_test, parallel=True):
def grid_search(model_func, train, test, cfg_list, parallel=True):
    scores = None
    if parallel:
        # execute configs in parallel
        executor = Parallel(n_jobs=cpu_count(), backend='multiprocessing', verbose=1)
#         executor = Parallel(n_jobs=psutil.cpu_count(), verbose=1)
        tasks = (delayed(score_model)(model_func,train, test, cfg) for cfg in cfg_list)
        scores = executor(tasks)
#         print('scores2', scores)
    else:
        scores = [score_model(model_func,train, test, cfg) for cfg in cfg_list]
#         print('scores1', scores)
    # remove empty results
#     print('scores', scores)
    scores = [r for r in scores if r[1] != None]
    # sort configs by error, asc
    scores.sort(key=lambda tup: tup[1])
    return scores


# score a model, return None on failure

def score_model(model_func,train, test, cfg, debug=False):
#     print('score_model')
    result = None
    # convert config to a key
    key = str(cfg)
    # show all warnings and fail on exception if debugging
    if debug:
#         result = walk_forward_validation(data, n_test, cfg)
        result = evaluate_model(model_func,train, test, cfg)[0]
#         print('DEBUG')
    else:
        # one failure during model validation suggests an unstable config
        try:
            # never show warnings when grid searching, too noisy
            with catch_warnings():
                filterwarnings("ignore")
                result = evaluate_model(model_func,train, test, cfg)[0]
#                 print('RESULT')
        except:
            error = None
    # check for an interesting result
    if result is not None:
        print(' > Model[%s] %.3f' % (key, result))
    return (key, result)


def train_channels_in_range_inclusive(a, b):
# Generating a dataframe for each channel
    best_config_dict = {}
    #empty channels
    empty_channels = []
#     for chan in chanlist[lower_limit:(upper_limit+1)]:
    for chan in static_channel_list[a:b+1]:
    #     # selecting only rows relating to the given channel
        d = hourly_data.loc[hourly_data.channel_id == chan]

        ##check to ensure that dataframe is not empty
        if d.empty:
        	empty_channels.append(chan)
        else:
	        # removing partial days at start and end of sample
	        df = full_days_only(d)
	        # set size of out of sample test data
	        oos_size = 24
	        df, oos = out_of_sample(df, oos_size)
	        # Generating train and test
	        train, test, final_test = split_dataset(df)[0:3]
	    
	        # define the names and functions for the models we wish to evaluate
	        models = dict()
	        models['sarima'] = sarima_forecast

	        print('channel', chan)
	        # model configs
	        n_test = 24
	        cfg_list = sarima_configs()
	        # print(cfg_list)
	        # grid search
	    #     count=0
	        scores = grid_search(sarima_forecast, train, test, cfg_list)
	#     print('channel: '+str(chan) +' done')
	        # list top 3 configs
	        for cfg, error in scores[:5]:
	            print(cfg, error)
	    #     print('SCORES',scores)    
	        # best_config = scores[:1]
	        best_config = ast.literal_eval(scores[:1][0][0])
	        print('best config', best_config)
	        ## For calculating out of sample score
	#         best_oos_yhat = sarima_forecast(df, best_config)
	#         oos_rmse = measure_rmse(final_test, best_oos_yhat)
	#         print('Out of sample rmse: ', oos_rmse)
	        # Add best config to the current best_config_dict
	        best_config_dict[chan] = best_config
	        print(best_config_dict)
    return best_config, best_config_dict

#for chan in static_channel_list:
    #d = hourly_data.loc[hourly_data.channel_id == chan, ['time','pm2_5']]
#     print(d)
    #df = full_days_only(d)
#     print('Channel: ', chan)
    # USE THIS IF WANT TO GENERATE AUTOCORRELATION GRAPHS
#     plot_acf_pcf(df, 24)


if __name__ == '__main__':
    print("richard starts")
    static_channel_list = datamanagement.get_all_static_channels()
    print("richard ends")
    data = datamanagement.query_data() 
    hourly_data = datamanagement.calculate_hourly_averages(data)
    #print("richard starts")
    #print(hourly_data.head())
    #print("richard starts ending")

    '''
    empty_channels = []
    for chan in static_channel_list:
    	d = hourly_data.loc[hourly_data.channel_id == chan, ['time','pm2_5']]
    	if d.empty:
    		empty_channels.append(chan)
    		print('channel {0} is empty'.format(chan))
    	else:
    		print(d)

    		d.to_csv(str(chan)+"dat.csv")
    		df = full_days_only(d)
    		df.to_csv("df"+str(chan)+"df.csv")

    	print(empty_channels)
    	#df = full_days_only(d)
#     print('Channel: ', chan)
	'''

    last_channel_best_config, obtained_best_config_dict = train_channels_in_range_inclusive(0,len(static_channel_list))

    with open('best_config_dict.json', 'w') as fp:
    	json.dump(obtained_best_config_dict, fp)



   