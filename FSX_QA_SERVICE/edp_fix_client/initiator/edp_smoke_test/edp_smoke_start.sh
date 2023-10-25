

#python3 /Users/tendy/Documents/FSX-DEV-QA/FSX_QA_SERVICE/edp_fix_client/initiator/edp_smoke_test/edp_smoke_application.py  --Data '{
#    "Account": "RSIT_EDP_ACCOUNT_5",
#    "Market": "EDP",
#    "ActionType": "NewAck",
#    "OrderQty": 100,
#    "OrdType": "1",
#    "Side": "2",
#    "Symbol": "5110",
#    "TimeInForce": "3",
#    "CrossingPriceType": "EDP",
#    "Rule80A": "P",
#    "CashMargin": "1",
#    "MarginTransactionType": "0",
#    "MinQty": 0,
#    "OrderClassification": "3",
#    "SelfTradePreventionId": "0"}
#' --account RSIT_EDP_ACCOUNT_5 --Sender RSIT_EDP_5 --Target FSX_SIT_EDP --Host 54.250.107.1 --Port 5005


python3 edp_smoke_application.py --Data '{
    "source": "your_source",
    "ip": "54.250.107.1",
    "pord": "5005",
    "sender": "RSIT_EDP_5",
    "target": "FSX_SIT_EDP",
    "Account": "RSIT_EDP_ACCOUNT_5",
    "Market": "EDP",
    "ActionType": "NewAck",
    "OrderQty": 100,
    "OrdType": "1",
    "Side": "2",
    "Symbol": "5110",
    "TimeInForce": "3",
    "CrossingPriceType": "EDP",
    "Rule80A": "P",
    "CashMargin": "1",
    "MarginTransactionType": "0",
    "MinQty": 0,
    "OrderClassification": "3",
    "SelfTradePreventionId": "0"}
'