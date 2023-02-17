This project is based on the publicly available dataset of the brazilian e-commerce store Olist.
The goal of the project is to explore the dataset and imrpove revenue by providing data-driven suggestions to the company.
As part of the project, I preprocessed the data, stored it in accessible tables.
Consequently, I conducted exploratory analyses, regression analyses on the most influential factors for negative reviews and
worked out actionable suggestions for the company with calculatable profit margin improvements.
The main insights generated in this process are as follows:
- `wait_time` is the most significant factor behind low review scores
- `wait_time` is made up of seller's `delay_to_carrier` + `carrier_delivery_time`.
- The latter being outside of Olist's direct control, improving it is not a quick-win recommendation
- On the contrary, a better selection of `sellers` can positively impact the `delay_to_carrier` and reduce the number of bad `review_scores` on Olist.
- Dropping the worst performing 746 sellers from the dataset results in the highest profit margin for Olist, with a profit of 1159342.24 BRL
- However, the profit increase already starts stagnating when around 200 sellers are dropped. Considering this the main recommendation woud be to drop the worst performing 200 sellers from the e-commerce platform.

