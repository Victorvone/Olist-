import pandas as pd
import numpy as np
from olist.utils import haversine_distance
from olist.data import Olist


class Order:
    '''
    DataFrames containing all orders as index,
    and various properties of these orders as columns
    '''
    def __init__(self):
        # Assign an attribute ".data" to all new instances of Order
        self.data = Olist().get_data()

    def get_wait_time(self):
        """
        Returns a DataFrame with:
        [order_id, wait_time, expected_wait_time, delay_vs_expected, order_status]
        and filters out non-delivered orders unless specified
        """
        # filter by delivered orders
        orders = self.data['orders']
        # filter by delivered orders
        orders = orders[orders['order_status'] == 'delivered'].copy()

        #Convert all dates to datetime
        orders[['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date']] = orders.iloc[:,[3,6,7]].apply(pd.to_datetime)

        #Compute wait_time
        orders.loc[:,'wait_time'] = orders.loc[:,'order_delivered_customer_date'
            ] - orders.loc[:,'order_purchase_timestamp']
        orders['wait_time'] = orders['wait_time'] / pd.to_timedelta(1, unit='D')

        #expected_wait_time
        orders.loc[:,'expected_wait_time'] = orders['order_estimated_delivery_date'
            ] - orders['order_purchase_timestamp']
        orders['expected_wait_time'] = orders['expected_wait_time'] / pd.to_timedelta(1, unit='D')

        #delay_vs_expected
        orders.loc[:,'temp_delay_vs_expected'] = orders['wait_time'
            ] - orders['expected_wait_time']

        orders['delay_vs_expected'] = orders['temp_delay_vs_expected'].apply(lambda x: 0 if x <= 0 else x)

        #delete unnecessary columns
        orders.drop('order_purchase_timestamp', inplace=True, axis = 1)
        orders.drop('order_delivered_carrier_date', inplace=True, axis = 1)
        orders.drop('order_approved_at', inplace=True, axis = 1)
        orders.drop('order_delivered_customer_date', inplace=True, axis = 1)
        orders.drop('order_estimated_delivery_date', inplace=True, axis = 1)
        orders.drop('customer_id', inplace=True, axis = 1)
        orders.drop('temp_delay_vs_expected', inplace=True, axis = 1)
        return orders

    def get_review_score(self):
        """
        Returns a DataFrame with:
        order_id, dim_is_five_star, dim_is_one_star, review_score
        """
        reviews = self.data['order_reviews']
        review_scores = reviews[['order_id','review_score']].copy()

        def is_5(x):
            if x == 5:
                return 1
            else:
                return 0

        def is_1(x):
            if x == 1:
                return 1
            else:
                return 0

        review_scores['dim_is_five_star'] = review_scores['review_score'].apply(is_5)
        review_scores['dim_is_one_star'] = review_scores['review_score'].apply(is_1)
        return review_scores

    def get_number_products(self):
        """
        Returns a DataFrame with:
        order_id, number_of_products
        """
        order_items = self.data['order_items']
        order_items_unique = pd.DataFrame(order_items.groupby(['order_id'])['order_id'].count())
        order_items_unique.columns = ['number_of_products']
        order_items_unique = order_items_unique.reset_index()
        return order_items_unique

    def get_number_sellers(self):
        """
        Returns a DataFrame with:
        order_id, number_of_sellers
        """
        order_items = self.data['order_items']
        order_items_sellers = pd.DataFrame(order_items.groupby(['order_id'])['seller_id'].count())
        order_items_sellers.columns = ['number_of_sellers']
        order_items_sellers.reset_index(inplace = True)
        return order_items_sellers

    def get_price_and_freight(self):
        """
        Returns a DataFrame with:
        order_id, price, freight_value
        """
        order_items = self.data['order_items']
        order_items_price = pd.DataFrame(order_items.groupby(['order_id'])[['price','freight_value']].sum())
        order_items_price.columns = ['price','freight_value']
        order_items_price.reset_index(inplace = True)
        return order_items_price

    # Optional
    def get_distance_seller_customer(self):
        """
        Returns a DataFrame with:
        order_id, distance_seller_customer
        """
        from math import radians, sin, cos, asin, sqrt


        seller_geo = self.data['geolocation'].copy().rename(columns={'geolocation_zip_code_prefix': 'seller_zip_code_prefix'})\
        .drop_duplicates(subset='seller_zip_code_prefix')

        #Merge tables of order, seller and geo to get seller geodata. Rename Geodatae afterwards
        all_orders = self.data['order_items'].copy()\
        .merge(self.data['orders'].copy(), on='order_id', how ='inner')\
        .merge(self.data['sellers'].copy(), on='seller_id', how = 'inner')\
        .merge(seller_geo, on='seller_zip_code_prefix', how = 'inner')\
        .rename(columns={'geolocation_lat': 'seller_geolocation_lat', 'geolocation_lng': 'seller_geolocation_lng'})


        #Merge previous table with customer details and geodata
        customer_geo = self.data['geolocation'].copy().rename(columns={'geolocation_zip_code_prefix': 'customer_zip_code_prefix'})\
        .drop_duplicates(subset='customer_zip_code_prefix')

        all_orders = all_orders.merge(self.data['customers'].copy(), on='customer_id', how = 'inner')\
        .merge(customer_geo, on='customer_zip_code_prefix', how='inner')\
        .rename(columns={'geolocation_lat': 'customer_geolocation_lat', 'geolocation_lng': 'customer_geolocation_lng'})

        #Get new dataframe with only order id, product id, customer geo and seller geo
        distances = all_orders[['order_id', 'product_id', 'customer_geolocation_lat', 'customer_geolocation_lng', 'seller_geolocation_lat','seller_geolocation_lng']]
        distances

        #haversine_distance 
        from olist.utils import haversine_distance
        distances['distance_seller_customer'] = distances\
            .apply(lambda x: haversine_distance(x['customer_geolocation_lng'],\
                                                x['customer_geolocation_lat'],\
                                                x['seller_geolocation_lng'],\
                                                x['seller_geolocation_lat']), axis=1)

        #[['customer_geolocation_lng','seller_geolocation_lng','customer_geolocation_lat', 'seller_geolocation_lat']]
        distance_clean = pd.DataFrame(distances.groupby(['order_id'])['distance_seller_customer'].mean())

        distance_clean.reset_index(inplace = True)
        return distance_clean

    def get_training_data(self,
                          is_delivered=True,
                          with_distance_seller_customer=False):
        """
        Returns a clean DataFrame (without NaN), with the all following columns:
        ['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected',
        'order_status', 'dim_is_five_star', 'dim_is_one_star', 'review_score',
        'number_of_products', 'number_of_sellers', 'price', 'freight_value',
        'distance_seller_customer']
        """
        complete_dataframe = self.get_wait_time().merge(self.get_review_score(), on='order_id', how = 'inner')\
        .merge(self.get_number_products(), on='order_id', how = 'inner')\
        .merge(self.get_number_sellers(), on='order_id', how = 'inner')\
        .merge(self.get_price_and_freight(), on='order_id', how = 'inner')\
        .merge(self.get_distance_seller_customer(), on='order_id', how = 'inner')
        complete_dataframe.dropna(inplace=True)
        return complete_dataframe
        # Hint: make sure to re-use your instance methods defined above
