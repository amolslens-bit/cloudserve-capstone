# A-05 check: customer ID, tier and region (19 Nov 2026)

Development tickets only (500). Input fields only; labels and history not read. Holdout not opened.
Script: analysis/customer_consistency.py

- Tickets with an empty customer ID, tier, region or body: 0 of 500
- Distinct customer IDs: 220; IDs with more than one ticket: 150
- Of those 150: different tiers 112, different regions 130, different names 150
- Example CUST-1131: DEV-0001 standard latin_america; DEV-0221 standard north_america; DEV-0303 enterprise europe; DEV-0499 business asia_pacific

Meaning: the fields are always filled in, but a customer ID does not identify one customer with one tier
and region. The system has no customer list: it reads tier and region from each ticket on its own, and the
fairness check by tier uses each ticket's own tier. A per-customer view (for example repeat contacts by customer) would not be reliable.
