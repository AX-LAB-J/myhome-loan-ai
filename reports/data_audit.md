# CSV audit

- home_ids_unique: True
- customer_ids_unique: True
- loan_ids_unique: True
- loan_customers_present: True
- customer_details_join: True
- all_customer_profiles_join: True
- all_debts_join: True
- all_accounts_join: True
- real_estate_details_join: True
- reference_trade_ids_present: True
- prices_positive: True
- area_positive: True
- model_inputs_finite: True
- purchase_loans_reconcile: True

Home purchases cover only the purchaser subset; complete profiles include non-owners.
Non-purchaser monthly consumption is a budget, not observed spending.
Non-purchaser region is a province; district and target home are search defaults.
The saved model was trained before this CSV import and was not retrained.
Reference purchases are not current listings or loan approvals.