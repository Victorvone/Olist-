import os
import pandas as pd


class Olist:
    def get_data(self):
        """
        This function returns a Python dict.
        Its keys should be 'sellers', 'orders', 'order_items' etc...
        Its values should be pandas.DataFrames loaded from csv files
        """

        #Create the variable csv_path, which stores the path to your "csv" folder as a string
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/csv/')

        #Create the list file_names containing all csv file names in the csv directory
        file_names = os.listdir(csv_path)
        for name in file_names:
            if not name.endswith('.csv'):
                file_names.remove(name)

        #Create the list of dict key key_names¶
        key_names = [
            name.replace('olist_', '').replace('_dataset', '').replace('.csv', '')
            for name in file_names]

        #Construct the dictionary data
        data = {}
        for key, path in zip(key_names, file_names):
            data[key] = pd.read_csv(os.path.join(csv_path, path))
        return data

