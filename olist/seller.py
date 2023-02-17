
import pandas as pd
import numpy as np
from olist.data import Olist
from olist.order import Order


class Seller:
    def __init__(self):
        # Import data only once
        olist = Olist()
        self.data = olist.get_data()
        self.order = Order()

    def get_seller_features(self):
        """
        Returns a DataFrame with:
        'seller_id', 'seller_city', 'seller_state'
        """
        sellers = self.data['sellers'].copy(
        )  # Make a copy before using inplace=True so as to avoid modifying self.data
        sellers.drop('seller_zip_code_prefix', axis=1, inplace=True)
        sellers.drop_duplicates(
            inplace=True)  # There can be multiple rows per seller
        return sellers

    def get_seller_delay_wait_time(self):
        """
        Returns a DataFrame with:
        'seller_id', 'delay_to_carrier', 'wait_time'
        """
        # Get data
        order_items = self.data['order_items'].copy()
        orders = self.data['orders'].query("order_status=='delivered'").copy()

        ship = order_items.merge(orders, on='order_id')

        # Handle datetime
        ship.loc[:, 'shipping_limit_date'] = pd.to_datetime(
            ship['shipping_limit_date'])
        ship.loc[:, 'order_delivered_carrier_date'] = pd.to_datetime(
            ship['order_delivered_carrier_date'])
        ship.loc[:, 'order_delivered_customer_date'] = pd.to_datetime(
            ship['order_delivered_customer_date'])
        ship.loc[:, 'order_purchase_timestamp'] = pd.to_datetime(
            ship['order_purchase_timestamp'])

        # Compute delay and wait_time
        def delay_to_logistic_partner(d):
            days = np.mean(
                (d.order_delivered_carrier_date - d.shipping_limit_date) /
                np.timedelta64(24, 'h'))
            if days > 0:
                return days
            else:
                return 0

        def order_wait_time(d):
            days = np.mean(
                (d.order_delivered_customer_date - d.order_purchase_timestamp)
                / np.timedelta64(24, 'h'))
            return days

        delay = ship.groupby('seller_id')\
                    .apply(delay_to_logistic_partner)\
                    .reset_index()
        delay.columns = ['seller_id', 'delay_to_carrier']

        wait = ship.groupby('seller_id')\
                   .apply(order_wait_time)\
                   .reset_index()
        wait.columns = ['seller_id', 'wait_time']

        df = delay.merge(wait, on='seller_id')

        return df

    def get_active_dates(self):
        """
        Returns a DataFrame with:
        'seller_id', 'date_first_sale', 'date_last_sale', 'months_on_olist'
        """
        # First, get only orders that are approved
        orders_approved = self.data['orders'][[
            'order_id', 'order_approved_at'
        ]].dropna()

        # Then, create a (orders <> sellers) join table because a seller can appear multiple times in the same order
        orders_sellers = orders_approved.merge(self.data['order_items'],
                                               on='order_id')[[
                                                   'order_id', 'seller_id',
                                                   'order_approved_at'
                                               ]].drop_duplicates()
        orders_sellers["order_approved_at"] = pd.to_datetime(
            orders_sellers["order_approved_at"])

        # Compute dates
        orders_sellers["date_first_sale"] = orders_sellers["order_approved_at"]
        orders_sellers["date_last_sale"] = orders_sellers["order_approved_at"]
        df = orders_sellers.groupby('seller_id').agg({
            "date_first_sale": min,
            "date_last_sale": max
        })
        df['months_on_olist'] = round(
            (df['date_last_sale'] - df['date_first_sale']) /
            np.timedelta64(1, 'M'))
        return df

    def get_quantity(self):
        """
        Returns a DataFrame with:
        'seller_id', 'n_orders', 'quantity', 'quantity_per_order'
        """
        order_items = self.data['order_items']

        n_orders = order_items.groupby('seller_id')['order_id']\
            .nunique()\
            .reset_index()
        n_orders.columns = ['seller_id', 'n_orders']

        quantity = order_items.groupby('seller_id', as_index=False).agg(
            {'order_id': 'count'})
        quantity.columns = ['seller_id', 'quantity']

        result = n_orders.merge(quantity, on='seller_id')
        result['quantity_per_order'] = result['quantity'] / result['n_orders']
        return result

    def get_sales(self):
        """
        Returns a DataFrame with:
        'seller_id', 'sales'
        """
        return self.data['order_items'][['seller_id', 'price']]\
            .groupby('seller_id')\
            .sum()\
            .rename(columns={'price': 'sales'})

    def get_review_score(self):
        """
        Returns a DataFrame with:
        'seller_id', 'share_of_five_stars', 'share_of_one_stars', 'review_score'
        """

        # $CHALLENGIFY_BEGIN
        orders_reviews = self.order.get_review_score()
        orders_sellers = self.data['order_items'][['order_id', 'seller_id'
                                                   ]].drop_duplicates()

        df = orders_sellers.merge(orders_reviews, on='order_id')
        res = df.groupby('seller_id', as_index=False).agg({
            'dim_is_one_star':
            'mean',
            'dim_is_five_star':
            'mean',
            'review_score':
            'mean'
        })
        # Rename columns
        res.columns = [
            'seller_id', 'share_of_one_stars', 'share_of_five_stars',
            'review_score'
        ]
        return res

    def get_revenue_and_costs(self):
        '''returns a Dataframe with 'seller_id', 'revenue' 'review_costs' and 'profits' '''
        #Revenue
        sales_and_dates = self.get_sales().merge(self.get_active_dates(), on='seller_id').reset_index()
        sales_and_dates['revenue'] = sales_and_dates['sales']*0.1+ sales_and_dates['months_on_olist']*80
        revenue = sales_and_dates[['seller_id', 'revenue']]

        ##Costs of reviews:
        #Get review scores for each order through orders table
        orders_reviews = self.order.get_training_data(with_distance_seller_customer=True)[['order_id','review_score']]
        orders_sellers = self.data['order_items'][['order_id', 'seller_id']].drop_duplicates()

        # Create columns for each review score
        reviews_merge = orders_sellers.merge(orders_reviews, on='order_id')
        reviews_merge['dim_is_five_star'] = reviews_merge['review_score'].apply(lambda x : 1 if x == 5 else 0)
        reviews_merge['dim_is_four_star'] = reviews_merge['review_score'].apply(lambda x : 1 if x == 4 else 0)
        reviews_merge['dim_is_three_star'] = reviews_merge['review_score'].apply(lambda x : 1 if x == 3 else 0)
        reviews_merge['dim_is_two_star'] = reviews_merge['review_score'].apply(lambda x : 1 if x == 2 else 0)
        reviews_merge['dim_is_one_star'] = reviews_merge['review_score'].apply(lambda x : 1 if x == 1 else 0)

        #Count each review score
        seller_costs = reviews_merge.groupby('seller_id').agg(
            {'dim_is_five_star': ['sum'],
             'dim_is_four_star': ['sum'],
             'dim_is_three_star': ['sum'],
             'dim_is_two_star': ['sum'],
             'dim_is_one_star': ['sum']}).reset_index()
        seller_costs.columns = seller_costs.columns.droplevel(1)

        #Calculate costs
        seller_costs['review_costs'] = \
            seller_costs['dim_is_three_star']*40 + seller_costs['dim_is_two_star']*50 + seller_costs['dim_is_one_star']*100

        #Clean up results
        seller_costs.drop([
            'dim_is_five_star',
            'dim_is_four_star',
            'dim_is_three_star',
            'dim_is_two_star',
            'dim_is_one_star'
            ], axis=1, inplace = True)

        #Profits:
        #merge revenue and seller_costs
        Profits = revenue.merge(seller_costs, on='seller_id')
        Profits['profits'] = Profits['revenue'] - Profits['review_costs']
        return Profits


    def get_training_data(self):
        """
        Returns a DataFrame with:
        ['seller_id', 'seller_city', 'seller_state', 'delay_to_carrier',
        'wait_time', 'date_first_sale', 'date_last_sale', 'months_on_olist', 'share_of_one_stars',
        'share_of_five_stars', 'review_score', 'n_orders', 'quantity',
        'quantity_per_order', 'sales']
        """

        training_set =\
            self.get_seller_features()\
                .merge(
                self.get_seller_delay_wait_time(), on='seller_id'
               ).merge(
                self.get_active_dates(), on='seller_id'
               ).merge(
                self.get_quantity(), on='seller_id'
               ).merge(
                self.get_sales(), on='seller_id'
               ).merge(
                self.get_revenue_and_costs(), on='seller_id'
               )

        if self.get_review_score() is not None:
            training_set = training_set.merge(self.get_review_score(),
                                              on='seller_id')

        return training_set
