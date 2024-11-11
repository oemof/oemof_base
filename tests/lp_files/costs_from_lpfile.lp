\* Source Pyomo model name=Model *\

min 
objective:
+0.5 InvestmentFlowBlock_invest(diesel_b_el1_0)
+3 flow(b_el1_storage_0_0)
+3 flow(b_el1_storage_0_1)
+3 flow(b_el1_storage_0_2)
+3 flow(b_el1_storage_0_3)
+3 flow(b_el1_storage_0_4)
+3 flow(b_el1_storage_0_5)
+3 flow(b_el1_storage_0_6)
+3 flow(b_el1_storage_0_7)
+3 flow(b_el1_storage_0_8)
+3 flow(b_el1_storage_0_9)
+3 flow(b_el1_storage_0_10)
+3 flow(b_el1_storage_0_11)
+3 flow(b_el1_storage_0_12)
+3 flow(b_el1_storage_0_13)
+3 flow(b_el1_storage_0_14)
+3 flow(b_el1_storage_0_15)
+3 flow(b_el1_storage_0_16)
+3 flow(b_el1_storage_0_17)
+3 flow(b_el1_storage_0_18)
+3 flow(b_el1_storage_0_19)
+3 flow(b_el1_storage_0_20)
+3 flow(b_el1_storage_0_21)
+3 flow(b_el1_storage_0_22)
+3 flow(b_el1_storage_0_23)
+2 flow(b_diesel_diesel_0_0)
+2 flow(b_diesel_diesel_0_1)
+2 flow(b_diesel_diesel_0_2)
+2 flow(b_diesel_diesel_0_3)
+2 flow(b_diesel_diesel_0_4)
+2 flow(b_diesel_diesel_0_5)
+2 flow(b_diesel_diesel_0_6)
+2 flow(b_diesel_diesel_0_7)
+2 flow(b_diesel_diesel_0_8)
+2 flow(b_diesel_diesel_0_9)
+2 flow(b_diesel_diesel_0_10)
+2 flow(b_diesel_diesel_0_11)
+2 flow(b_diesel_diesel_0_12)
+2 flow(b_diesel_diesel_0_13)
+2 flow(b_diesel_diesel_0_14)
+2 flow(b_diesel_diesel_0_15)
+2 flow(b_diesel_diesel_0_16)
+2 flow(b_diesel_diesel_0_17)
+2 flow(b_diesel_diesel_0_18)
+2 flow(b_diesel_diesel_0_19)
+2 flow(b_diesel_diesel_0_20)
+2 flow(b_diesel_diesel_0_21)
+2 flow(b_diesel_diesel_0_22)
+2 flow(b_diesel_diesel_0_23)
+1 flow(diesel_b_el1_0_0)
+1 flow(diesel_b_el1_0_1)
+1 flow(diesel_b_el1_0_2)
+1 flow(diesel_b_el1_0_3)
+1 flow(diesel_b_el1_0_4)
+1 flow(diesel_b_el1_0_5)
+1 flow(diesel_b_el1_0_6)
+1 flow(diesel_b_el1_0_7)
+1 flow(diesel_b_el1_0_8)
+1 flow(diesel_b_el1_0_9)
+1 flow(diesel_b_el1_0_10)
+1 flow(diesel_b_el1_0_11)
+1 flow(diesel_b_el1_0_12)
+1 flow(diesel_b_el1_0_13)
+1 flow(diesel_b_el1_0_14)
+1 flow(diesel_b_el1_0_15)
+1 flow(diesel_b_el1_0_16)
+1 flow(diesel_b_el1_0_17)
+1 flow(diesel_b_el1_0_18)
+1 flow(diesel_b_el1_0_19)
+1 flow(diesel_b_el1_0_20)
+1 flow(diesel_b_el1_0_21)
+1 flow(diesel_b_el1_0_22)
+1 flow(diesel_b_el1_0_23)
+2.5 flow(storage_b_el2_0_0)
+2.5 flow(storage_b_el2_0_1)
+2.5 flow(storage_b_el2_0_2)
+2.5 flow(storage_b_el2_0_3)
+2.5 flow(storage_b_el2_0_4)
+2.5 flow(storage_b_el2_0_5)
+2.5 flow(storage_b_el2_0_6)
+2.5 flow(storage_b_el2_0_7)
+2.5 flow(storage_b_el2_0_8)
+2.5 flow(storage_b_el2_0_9)
+2.5 flow(storage_b_el2_0_10)
+2.5 flow(storage_b_el2_0_11)
+2.5 flow(storage_b_el2_0_12)
+2.5 flow(storage_b_el2_0_13)
+2.5 flow(storage_b_el2_0_14)
+2.5 flow(storage_b_el2_0_15)
+2.5 flow(storage_b_el2_0_16)
+2.5 flow(storage_b_el2_0_17)
+2.5 flow(storage_b_el2_0_18)
+2.5 flow(storage_b_el2_0_19)
+2.5 flow(storage_b_el2_0_20)
+2.5 flow(storage_b_el2_0_21)
+2.5 flow(storage_b_el2_0_22)
+2.5 flow(storage_b_el2_0_23)
+0.4 GenericInvestmentStorageBlock_invest(storage_0)

s.t.

c_e_BusBlock_balance(b_el1_0_0)_:
-1 flow(b_el1_storage_0_0)
+1 flow(diesel_b_el1_0_0)
= 0

c_e_BusBlock_balance(b_el1_0_1)_:
-1 flow(b_el1_storage_0_1)
+1 flow(diesel_b_el1_0_1)
= 0

c_e_BusBlock_balance(b_el1_0_2)_:
-1 flow(b_el1_storage_0_2)
+1 flow(diesel_b_el1_0_2)
= 0

c_e_BusBlock_balance(b_el1_0_3)_:
-1 flow(b_el1_storage_0_3)
+1 flow(diesel_b_el1_0_3)
= 0

c_e_BusBlock_balance(b_el1_0_4)_:
-1 flow(b_el1_storage_0_4)
+1 flow(diesel_b_el1_0_4)
= 0

c_e_BusBlock_balance(b_el1_0_5)_:
-1 flow(b_el1_storage_0_5)
+1 flow(diesel_b_el1_0_5)
= 0

c_e_BusBlock_balance(b_el1_0_6)_:
-1 flow(b_el1_storage_0_6)
+1 flow(diesel_b_el1_0_6)
= 0

c_e_BusBlock_balance(b_el1_0_7)_:
-1 flow(b_el1_storage_0_7)
+1 flow(diesel_b_el1_0_7)
= 0

c_e_BusBlock_balance(b_el1_0_8)_:
-1 flow(b_el1_storage_0_8)
+1 flow(diesel_b_el1_0_8)
= 0

c_e_BusBlock_balance(b_el1_0_9)_:
-1 flow(b_el1_storage_0_9)
+1 flow(diesel_b_el1_0_9)
= 0

c_e_BusBlock_balance(b_el1_0_10)_:
-1 flow(b_el1_storage_0_10)
+1 flow(diesel_b_el1_0_10)
= 0

c_e_BusBlock_balance(b_el1_0_11)_:
-1 flow(b_el1_storage_0_11)
+1 flow(diesel_b_el1_0_11)
= 0

c_e_BusBlock_balance(b_el1_0_12)_:
-1 flow(b_el1_storage_0_12)
+1 flow(diesel_b_el1_0_12)
= 0

c_e_BusBlock_balance(b_el1_0_13)_:
-1 flow(b_el1_storage_0_13)
+1 flow(diesel_b_el1_0_13)
= 0

c_e_BusBlock_balance(b_el1_0_14)_:
-1 flow(b_el1_storage_0_14)
+1 flow(diesel_b_el1_0_14)
= 0

c_e_BusBlock_balance(b_el1_0_15)_:
-1 flow(b_el1_storage_0_15)
+1 flow(diesel_b_el1_0_15)
= 0

c_e_BusBlock_balance(b_el1_0_16)_:
-1 flow(b_el1_storage_0_16)
+1 flow(diesel_b_el1_0_16)
= 0

c_e_BusBlock_balance(b_el1_0_17)_:
-1 flow(b_el1_storage_0_17)
+1 flow(diesel_b_el1_0_17)
= 0

c_e_BusBlock_balance(b_el1_0_18)_:
-1 flow(b_el1_storage_0_18)
+1 flow(diesel_b_el1_0_18)
= 0

c_e_BusBlock_balance(b_el1_0_19)_:
-1 flow(b_el1_storage_0_19)
+1 flow(diesel_b_el1_0_19)
= 0

c_e_BusBlock_balance(b_el1_0_20)_:
-1 flow(b_el1_storage_0_20)
+1 flow(diesel_b_el1_0_20)
= 0

c_e_BusBlock_balance(b_el1_0_21)_:
-1 flow(b_el1_storage_0_21)
+1 flow(diesel_b_el1_0_21)
= 0

c_e_BusBlock_balance(b_el1_0_22)_:
-1 flow(b_el1_storage_0_22)
+1 flow(diesel_b_el1_0_22)
= 0

c_e_BusBlock_balance(b_el1_0_23)_:
-1 flow(b_el1_storage_0_23)
+1 flow(diesel_b_el1_0_23)
= 0

c_e_BusBlock_balance(b_el2_0_0)_:
+1 flow(storage_b_el2_0_0)
= 0.0

c_e_BusBlock_balance(b_el2_0_1)_:
+1 flow(storage_b_el2_0_1)
= 100

c_e_BusBlock_balance(b_el2_0_2)_:
+1 flow(storage_b_el2_0_2)
= 100

c_e_BusBlock_balance(b_el2_0_3)_:
+1 flow(storage_b_el2_0_3)
= 100

c_e_BusBlock_balance(b_el2_0_4)_:
+1 flow(storage_b_el2_0_4)
= 100

c_e_BusBlock_balance(b_el2_0_5)_:
+1 flow(storage_b_el2_0_5)
= 100

c_e_BusBlock_balance(b_el2_0_6)_:
+1 flow(storage_b_el2_0_6)
= 100

c_e_BusBlock_balance(b_el2_0_7)_:
+1 flow(storage_b_el2_0_7)
= 100

c_e_BusBlock_balance(b_el2_0_8)_:
+1 flow(storage_b_el2_0_8)
= 100

c_e_BusBlock_balance(b_el2_0_9)_:
+1 flow(storage_b_el2_0_9)
= 100

c_e_BusBlock_balance(b_el2_0_10)_:
+1 flow(storage_b_el2_0_10)
= 100

c_e_BusBlock_balance(b_el2_0_11)_:
+1 flow(storage_b_el2_0_11)
= 100

c_e_BusBlock_balance(b_el2_0_12)_:
+1 flow(storage_b_el2_0_12)
= 100

c_e_BusBlock_balance(b_el2_0_13)_:
+1 flow(storage_b_el2_0_13)
= 100

c_e_BusBlock_balance(b_el2_0_14)_:
+1 flow(storage_b_el2_0_14)
= 100

c_e_BusBlock_balance(b_el2_0_15)_:
+1 flow(storage_b_el2_0_15)
= 100

c_e_BusBlock_balance(b_el2_0_16)_:
+1 flow(storage_b_el2_0_16)
= 100

c_e_BusBlock_balance(b_el2_0_17)_:
+1 flow(storage_b_el2_0_17)
= 100

c_e_BusBlock_balance(b_el2_0_18)_:
+1 flow(storage_b_el2_0_18)
= 100

c_e_BusBlock_balance(b_el2_0_19)_:
+1 flow(storage_b_el2_0_19)
= 100

c_e_BusBlock_balance(b_el2_0_20)_:
+1 flow(storage_b_el2_0_20)
= 100

c_e_BusBlock_balance(b_el2_0_21)_:
+1 flow(storage_b_el2_0_21)
= 100

c_e_BusBlock_balance(b_el2_0_22)_:
+1 flow(storage_b_el2_0_22)
= 100

c_e_BusBlock_balance(b_el2_0_23)_:
+1 flow(storage_b_el2_0_23)
= 100

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_0)_:
+2 flow(b_diesel_diesel_0_0)
-1 flow(diesel_b_el1_0_0)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_1)_:
+2 flow(b_diesel_diesel_0_1)
-1 flow(diesel_b_el1_0_1)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_2)_:
+2 flow(b_diesel_diesel_0_2)
-1 flow(diesel_b_el1_0_2)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_3)_:
+2 flow(b_diesel_diesel_0_3)
-1 flow(diesel_b_el1_0_3)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_4)_:
+2 flow(b_diesel_diesel_0_4)
-1 flow(diesel_b_el1_0_4)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_5)_:
+2 flow(b_diesel_diesel_0_5)
-1 flow(diesel_b_el1_0_5)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_6)_:
+2 flow(b_diesel_diesel_0_6)
-1 flow(diesel_b_el1_0_6)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_7)_:
+2 flow(b_diesel_diesel_0_7)
-1 flow(diesel_b_el1_0_7)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_8)_:
+2 flow(b_diesel_diesel_0_8)
-1 flow(diesel_b_el1_0_8)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_9)_:
+2 flow(b_diesel_diesel_0_9)
-1 flow(diesel_b_el1_0_9)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_10)_:
+2 flow(b_diesel_diesel_0_10)
-1 flow(diesel_b_el1_0_10)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_11)_:
+2 flow(b_diesel_diesel_0_11)
-1 flow(diesel_b_el1_0_11)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_12)_:
+2 flow(b_diesel_diesel_0_12)
-1 flow(diesel_b_el1_0_12)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_13)_:
+2 flow(b_diesel_diesel_0_13)
-1 flow(diesel_b_el1_0_13)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_14)_:
+2 flow(b_diesel_diesel_0_14)
-1 flow(diesel_b_el1_0_14)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_15)_:
+2 flow(b_diesel_diesel_0_15)
-1 flow(diesel_b_el1_0_15)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_16)_:
+2 flow(b_diesel_diesel_0_16)
-1 flow(diesel_b_el1_0_16)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_17)_:
+2 flow(b_diesel_diesel_0_17)
-1 flow(diesel_b_el1_0_17)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_18)_:
+2 flow(b_diesel_diesel_0_18)
-1 flow(diesel_b_el1_0_18)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_19)_:
+2 flow(b_diesel_diesel_0_19)
-1 flow(diesel_b_el1_0_19)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_20)_:
+2 flow(b_diesel_diesel_0_20)
-1 flow(diesel_b_el1_0_20)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_21)_:
+2 flow(b_diesel_diesel_0_21)
-1 flow(diesel_b_el1_0_21)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_22)_:
+2 flow(b_diesel_diesel_0_22)
-1 flow(diesel_b_el1_0_22)
= 0

c_e_ConverterBlock_relation(diesel_b_diesel_b_el1_0_23)_:
+2 flow(b_diesel_diesel_0_23)
-1 flow(diesel_b_el1_0_23)
= 0

c_e_InvestmentFlowBlock_total_rule(b_el1_storage_0)_:
-1 InvestmentFlowBlock_invest(b_el1_storage_0)
+1 InvestmentFlowBlock_total(b_el1_storage_0)
= 0

c_e_InvestmentFlowBlock_total_rule(storage_b_el2_0)_:
-1 InvestmentFlowBlock_invest(storage_b_el2_0)
+1 InvestmentFlowBlock_total(storage_b_el2_0)
= 0

c_e_InvestmentFlowBlock_total_rule(diesel_b_el1_0)_:
-1 InvestmentFlowBlock_invest(diesel_b_el1_0)
+1 InvestmentFlowBlock_total(diesel_b_el1_0)
= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_0)_:
+1 flow(b_el1_storage_0_0)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_1)_:
+1 flow(b_el1_storage_0_1)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_2)_:
+1 flow(b_el1_storage_0_2)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_3)_:
+1 flow(b_el1_storage_0_3)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_4)_:
+1 flow(b_el1_storage_0_4)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_5)_:
+1 flow(b_el1_storage_0_5)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_6)_:
+1 flow(b_el1_storage_0_6)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_7)_:
+1 flow(b_el1_storage_0_7)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_8)_:
+1 flow(b_el1_storage_0_8)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_9)_:
+1 flow(b_el1_storage_0_9)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_10)_:
+1 flow(b_el1_storage_0_10)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_11)_:
+1 flow(b_el1_storage_0_11)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_12)_:
+1 flow(b_el1_storage_0_12)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_13)_:
+1 flow(b_el1_storage_0_13)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_14)_:
+1 flow(b_el1_storage_0_14)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_15)_:
+1 flow(b_el1_storage_0_15)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_16)_:
+1 flow(b_el1_storage_0_16)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_17)_:
+1 flow(b_el1_storage_0_17)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_18)_:
+1 flow(b_el1_storage_0_18)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_19)_:
+1 flow(b_el1_storage_0_19)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_20)_:
+1 flow(b_el1_storage_0_20)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_21)_:
+1 flow(b_el1_storage_0_21)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_22)_:
+1 flow(b_el1_storage_0_22)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(b_el1_storage_0_23)_:
+1 flow(b_el1_storage_0_23)
-1 InvestmentFlowBlock_total(b_el1_storage_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_0)_:
+1 flow(storage_b_el2_0_0)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_1)_:
+1 flow(storage_b_el2_0_1)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_2)_:
+1 flow(storage_b_el2_0_2)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_3)_:
+1 flow(storage_b_el2_0_3)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_4)_:
+1 flow(storage_b_el2_0_4)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_5)_:
+1 flow(storage_b_el2_0_5)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_6)_:
+1 flow(storage_b_el2_0_6)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_7)_:
+1 flow(storage_b_el2_0_7)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_8)_:
+1 flow(storage_b_el2_0_8)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_9)_:
+1 flow(storage_b_el2_0_9)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_10)_:
+1 flow(storage_b_el2_0_10)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_11)_:
+1 flow(storage_b_el2_0_11)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_12)_:
+1 flow(storage_b_el2_0_12)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_13)_:
+1 flow(storage_b_el2_0_13)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_14)_:
+1 flow(storage_b_el2_0_14)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_15)_:
+1 flow(storage_b_el2_0_15)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_16)_:
+1 flow(storage_b_el2_0_16)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_17)_:
+1 flow(storage_b_el2_0_17)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_18)_:
+1 flow(storage_b_el2_0_18)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_19)_:
+1 flow(storage_b_el2_0_19)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_20)_:
+1 flow(storage_b_el2_0_20)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_21)_:
+1 flow(storage_b_el2_0_21)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_22)_:
+1 flow(storage_b_el2_0_22)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(storage_b_el2_0_23)_:
+1 flow(storage_b_el2_0_23)
-1 InvestmentFlowBlock_total(storage_b_el2_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_0)_:
+1 flow(diesel_b_el1_0_0)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_1)_:
+1 flow(diesel_b_el1_0_1)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_2)_:
+1 flow(diesel_b_el1_0_2)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_3)_:
+1 flow(diesel_b_el1_0_3)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_4)_:
+1 flow(diesel_b_el1_0_4)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_5)_:
+1 flow(diesel_b_el1_0_5)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_6)_:
+1 flow(diesel_b_el1_0_6)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_7)_:
+1 flow(diesel_b_el1_0_7)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_8)_:
+1 flow(diesel_b_el1_0_8)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_9)_:
+1 flow(diesel_b_el1_0_9)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_10)_:
+1 flow(diesel_b_el1_0_10)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_11)_:
+1 flow(diesel_b_el1_0_11)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_12)_:
+1 flow(diesel_b_el1_0_12)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_13)_:
+1 flow(diesel_b_el1_0_13)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_14)_:
+1 flow(diesel_b_el1_0_14)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_15)_:
+1 flow(diesel_b_el1_0_15)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_16)_:
+1 flow(diesel_b_el1_0_16)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_17)_:
+1 flow(diesel_b_el1_0_17)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_18)_:
+1 flow(diesel_b_el1_0_18)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_19)_:
+1 flow(diesel_b_el1_0_19)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_20)_:
+1 flow(diesel_b_el1_0_20)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_21)_:
+1 flow(diesel_b_el1_0_21)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_22)_:
+1 flow(diesel_b_el1_0_22)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_u_InvestmentFlowBlock_max(diesel_b_el1_0_23)_:
+1 flow(diesel_b_el1_0_23)
-1 InvestmentFlowBlock_total(diesel_b_el1_0)
<= 0

c_e_GenericInvestmentStorageBlock_total_storage_rule(storage_0)_:
-1 GenericInvestmentStorageBlock_invest(storage_0)
+1 GenericInvestmentStorageBlock_total(storage_0)
= 0

c_e_GenericInvestmentStorageBlock_init_content_fix(storage)_:
+1 GenericInvestmentStorageBlock_init_content(storage)
= 0

c_e_GenericInvestmentStorageBlock_balance_first(storage)_:
-1 flow(b_el1_storage_0_0)
+1.25 flow(storage_b_el2_0_0)
-1 GenericInvestmentStorageBlock_init_content(storage)
+1 GenericInvestmentStorageBlock_storage_content(storage_0)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_1)_:
-1 flow(b_el1_storage_0_1)
+1.25 flow(storage_b_el2_0_1)
-1 GenericInvestmentStorageBlock_storage_content(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_1)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_2)_:
-1 flow(b_el1_storage_0_2)
+1.25 flow(storage_b_el2_0_2)
-1 GenericInvestmentStorageBlock_storage_content(storage_1)
+1 GenericInvestmentStorageBlock_storage_content(storage_2)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_3)_:
-1 flow(b_el1_storage_0_3)
+1.25 flow(storage_b_el2_0_3)
-1 GenericInvestmentStorageBlock_storage_content(storage_2)
+1 GenericInvestmentStorageBlock_storage_content(storage_3)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_4)_:
-1 flow(b_el1_storage_0_4)
+1.25 flow(storage_b_el2_0_4)
-1 GenericInvestmentStorageBlock_storage_content(storage_3)
+1 GenericInvestmentStorageBlock_storage_content(storage_4)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_5)_:
-1 flow(b_el1_storage_0_5)
+1.25 flow(storage_b_el2_0_5)
-1 GenericInvestmentStorageBlock_storage_content(storage_4)
+1 GenericInvestmentStorageBlock_storage_content(storage_5)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_6)_:
-1 flow(b_el1_storage_0_6)
+1.25 flow(storage_b_el2_0_6)
-1 GenericInvestmentStorageBlock_storage_content(storage_5)
+1 GenericInvestmentStorageBlock_storage_content(storage_6)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_7)_:
-1 flow(b_el1_storage_0_7)
+1.25 flow(storage_b_el2_0_7)
-1 GenericInvestmentStorageBlock_storage_content(storage_6)
+1 GenericInvestmentStorageBlock_storage_content(storage_7)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_8)_:
-1 flow(b_el1_storage_0_8)
+1.25 flow(storage_b_el2_0_8)
-1 GenericInvestmentStorageBlock_storage_content(storage_7)
+1 GenericInvestmentStorageBlock_storage_content(storage_8)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_9)_:
-1 flow(b_el1_storage_0_9)
+1.25 flow(storage_b_el2_0_9)
-1 GenericInvestmentStorageBlock_storage_content(storage_8)
+1 GenericInvestmentStorageBlock_storage_content(storage_9)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_10)_:
-1 flow(b_el1_storage_0_10)
+1.25 flow(storage_b_el2_0_10)
-1 GenericInvestmentStorageBlock_storage_content(storage_9)
+1 GenericInvestmentStorageBlock_storage_content(storage_10)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_11)_:
-1 flow(b_el1_storage_0_11)
+1.25 flow(storage_b_el2_0_11)
-1 GenericInvestmentStorageBlock_storage_content(storage_10)
+1 GenericInvestmentStorageBlock_storage_content(storage_11)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_12)_:
-1 flow(b_el1_storage_0_12)
+1.25 flow(storage_b_el2_0_12)
-1 GenericInvestmentStorageBlock_storage_content(storage_11)
+1 GenericInvestmentStorageBlock_storage_content(storage_12)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_13)_:
-1 flow(b_el1_storage_0_13)
+1.25 flow(storage_b_el2_0_13)
-1 GenericInvestmentStorageBlock_storage_content(storage_12)
+1 GenericInvestmentStorageBlock_storage_content(storage_13)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_14)_:
-1 flow(b_el1_storage_0_14)
+1.25 flow(storage_b_el2_0_14)
-1 GenericInvestmentStorageBlock_storage_content(storage_13)
+1 GenericInvestmentStorageBlock_storage_content(storage_14)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_15)_:
-1 flow(b_el1_storage_0_15)
+1.25 flow(storage_b_el2_0_15)
-1 GenericInvestmentStorageBlock_storage_content(storage_14)
+1 GenericInvestmentStorageBlock_storage_content(storage_15)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_16)_:
-1 flow(b_el1_storage_0_16)
+1.25 flow(storage_b_el2_0_16)
-1 GenericInvestmentStorageBlock_storage_content(storage_15)
+1 GenericInvestmentStorageBlock_storage_content(storage_16)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_17)_:
-1 flow(b_el1_storage_0_17)
+1.25 flow(storage_b_el2_0_17)
-1 GenericInvestmentStorageBlock_storage_content(storage_16)
+1 GenericInvestmentStorageBlock_storage_content(storage_17)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_18)_:
-1 flow(b_el1_storage_0_18)
+1.25 flow(storage_b_el2_0_18)
-1 GenericInvestmentStorageBlock_storage_content(storage_17)
+1 GenericInvestmentStorageBlock_storage_content(storage_18)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_19)_:
-1 flow(b_el1_storage_0_19)
+1.25 flow(storage_b_el2_0_19)
-1 GenericInvestmentStorageBlock_storage_content(storage_18)
+1 GenericInvestmentStorageBlock_storage_content(storage_19)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_20)_:
-1 flow(b_el1_storage_0_20)
+1.25 flow(storage_b_el2_0_20)
-1 GenericInvestmentStorageBlock_storage_content(storage_19)
+1 GenericInvestmentStorageBlock_storage_content(storage_20)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_21)_:
-1 flow(b_el1_storage_0_21)
+1.25 flow(storage_b_el2_0_21)
-1 GenericInvestmentStorageBlock_storage_content(storage_20)
+1 GenericInvestmentStorageBlock_storage_content(storage_21)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_22)_:
-1 flow(b_el1_storage_0_22)
+1.25 flow(storage_b_el2_0_22)
-1 GenericInvestmentStorageBlock_storage_content(storage_21)
+1 GenericInvestmentStorageBlock_storage_content(storage_22)
= 0

c_e_GenericInvestmentStorageBlock_balance(storage_0_23)_:
-1 flow(b_el1_storage_0_23)
+1.25 flow(storage_b_el2_0_23)
-1 GenericInvestmentStorageBlock_storage_content(storage_22)
+1 GenericInvestmentStorageBlock_storage_content(storage_23)
= 0

c_e_GenericInvestmentStorageBlock_balanced_cstr(storage)_:
-1 GenericInvestmentStorageBlock_init_content(storage)
+1 GenericInvestmentStorageBlock_storage_content(storage_23)
= 0

c_e_GenericInvestmentStorageBlock_storage_capacity_inflow(storage_0)_:
+1 InvestmentFlowBlock_total(b_el1_storage_0)
-0.16666666666666666 GenericInvestmentStorageBlock_total(storage_0)
= 0

c_e_GenericInvestmentStorageBlock_storage_capacity_outflow(storage_0)_:
+1 InvestmentFlowBlock_total(storage_b_el2_0)
-0.16666666666666666 GenericInvestmentStorageBlock_total(storage_0)
= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_0)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_0)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_1)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_1)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_2)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_2)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_3)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_3)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_4)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_4)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_5)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_5)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_6)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_6)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_7)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_7)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_8)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_8)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_9)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_9)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_10)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_10)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_11)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_11)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_12)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_12)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_13)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_13)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_14)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_14)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_15)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_15)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_16)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_16)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_17)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_17)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_18)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_18)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_19)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_19)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_20)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_20)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_21)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_21)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_22)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_22)
<= 0

c_u_GenericInvestmentStorageBlock_max_storage_content(storage_0_23)_:
-1 GenericInvestmentStorageBlock_total(storage_0)
+1 GenericInvestmentStorageBlock_storage_content(storage_23)
<= 0

bounds
   0 <= InvestmentFlowBlock_invest(b_el1_storage_0) <= +inf
   0 <= InvestmentFlowBlock_invest(storage_b_el2_0) <= +inf
   0 <= InvestmentFlowBlock_invest(diesel_b_el1_0) <= +inf
   0 <= flow(b_el1_storage_0_0) <= +inf
   0 <= flow(b_el1_storage_0_1) <= +inf
   0 <= flow(b_el1_storage_0_2) <= +inf
   0 <= flow(b_el1_storage_0_3) <= +inf
   0 <= flow(b_el1_storage_0_4) <= +inf
   0 <= flow(b_el1_storage_0_5) <= +inf
   0 <= flow(b_el1_storage_0_6) <= +inf
   0 <= flow(b_el1_storage_0_7) <= +inf
   0 <= flow(b_el1_storage_0_8) <= +inf
   0 <= flow(b_el1_storage_0_9) <= +inf
   0 <= flow(b_el1_storage_0_10) <= +inf
   0 <= flow(b_el1_storage_0_11) <= +inf
   0 <= flow(b_el1_storage_0_12) <= +inf
   0 <= flow(b_el1_storage_0_13) <= +inf
   0 <= flow(b_el1_storage_0_14) <= +inf
   0 <= flow(b_el1_storage_0_15) <= +inf
   0 <= flow(b_el1_storage_0_16) <= +inf
   0 <= flow(b_el1_storage_0_17) <= +inf
   0 <= flow(b_el1_storage_0_18) <= +inf
   0 <= flow(b_el1_storage_0_19) <= +inf
   0 <= flow(b_el1_storage_0_20) <= +inf
   0 <= flow(b_el1_storage_0_21) <= +inf
   0 <= flow(b_el1_storage_0_22) <= +inf
   0 <= flow(b_el1_storage_0_23) <= +inf
   0 <= flow(b_diesel_diesel_0_0) <= +inf
   0 <= flow(b_diesel_diesel_0_1) <= +inf
   0 <= flow(b_diesel_diesel_0_2) <= +inf
   0 <= flow(b_diesel_diesel_0_3) <= +inf
   0 <= flow(b_diesel_diesel_0_4) <= +inf
   0 <= flow(b_diesel_diesel_0_5) <= +inf
   0 <= flow(b_diesel_diesel_0_6) <= +inf
   0 <= flow(b_diesel_diesel_0_7) <= +inf
   0 <= flow(b_diesel_diesel_0_8) <= +inf
   0 <= flow(b_diesel_diesel_0_9) <= +inf
   0 <= flow(b_diesel_diesel_0_10) <= +inf
   0 <= flow(b_diesel_diesel_0_11) <= +inf
   0 <= flow(b_diesel_diesel_0_12) <= +inf
   0 <= flow(b_diesel_diesel_0_13) <= +inf
   0 <= flow(b_diesel_diesel_0_14) <= +inf
   0 <= flow(b_diesel_diesel_0_15) <= +inf
   0 <= flow(b_diesel_diesel_0_16) <= +inf
   0 <= flow(b_diesel_diesel_0_17) <= +inf
   0 <= flow(b_diesel_diesel_0_18) <= +inf
   0 <= flow(b_diesel_diesel_0_19) <= +inf
   0 <= flow(b_diesel_diesel_0_20) <= +inf
   0 <= flow(b_diesel_diesel_0_21) <= +inf
   0 <= flow(b_diesel_diesel_0_22) <= +inf
   0 <= flow(b_diesel_diesel_0_23) <= +inf
   0 <= flow(diesel_b_el1_0_0) <= +inf
   0 <= flow(diesel_b_el1_0_1) <= +inf
   0 <= flow(diesel_b_el1_0_2) <= +inf
   0 <= flow(diesel_b_el1_0_3) <= +inf
   0 <= flow(diesel_b_el1_0_4) <= +inf
   0 <= flow(diesel_b_el1_0_5) <= +inf
   0 <= flow(diesel_b_el1_0_6) <= +inf
   0 <= flow(diesel_b_el1_0_7) <= +inf
   0 <= flow(diesel_b_el1_0_8) <= +inf
   0 <= flow(diesel_b_el1_0_9) <= +inf
   0 <= flow(diesel_b_el1_0_10) <= +inf
   0 <= flow(diesel_b_el1_0_11) <= +inf
   0 <= flow(diesel_b_el1_0_12) <= +inf
   0 <= flow(diesel_b_el1_0_13) <= +inf
   0 <= flow(diesel_b_el1_0_14) <= +inf
   0 <= flow(diesel_b_el1_0_15) <= +inf
   0 <= flow(diesel_b_el1_0_16) <= +inf
   0 <= flow(diesel_b_el1_0_17) <= +inf
   0 <= flow(diesel_b_el1_0_18) <= +inf
   0 <= flow(diesel_b_el1_0_19) <= +inf
   0 <= flow(diesel_b_el1_0_20) <= +inf
   0 <= flow(diesel_b_el1_0_21) <= +inf
   0 <= flow(diesel_b_el1_0_22) <= +inf
   0 <= flow(diesel_b_el1_0_23) <= +inf
   0 <= flow(storage_b_el2_0_0) <= +inf
   0 <= flow(storage_b_el2_0_1) <= +inf
   0 <= flow(storage_b_el2_0_2) <= +inf
   0 <= flow(storage_b_el2_0_3) <= +inf
   0 <= flow(storage_b_el2_0_4) <= +inf
   0 <= flow(storage_b_el2_0_5) <= +inf
   0 <= flow(storage_b_el2_0_6) <= +inf
   0 <= flow(storage_b_el2_0_7) <= +inf
   0 <= flow(storage_b_el2_0_8) <= +inf
   0 <= flow(storage_b_el2_0_9) <= +inf
   0 <= flow(storage_b_el2_0_10) <= +inf
   0 <= flow(storage_b_el2_0_11) <= +inf
   0 <= flow(storage_b_el2_0_12) <= +inf
   0 <= flow(storage_b_el2_0_13) <= +inf
   0 <= flow(storage_b_el2_0_14) <= +inf
   0 <= flow(storage_b_el2_0_15) <= +inf
   0 <= flow(storage_b_el2_0_16) <= +inf
   0 <= flow(storage_b_el2_0_17) <= +inf
   0 <= flow(storage_b_el2_0_18) <= +inf
   0 <= flow(storage_b_el2_0_19) <= +inf
   0 <= flow(storage_b_el2_0_20) <= +inf
   0 <= flow(storage_b_el2_0_21) <= +inf
   0 <= flow(storage_b_el2_0_22) <= +inf
   0 <= flow(storage_b_el2_0_23) <= +inf
   0 <= GenericInvestmentStorageBlock_invest(storage_0) <= +inf
   0 <= InvestmentFlowBlock_total(b_el1_storage_0) <= +inf
   0 <= InvestmentFlowBlock_total(storage_b_el2_0) <= +inf
   0 <= InvestmentFlowBlock_total(diesel_b_el1_0) <= +inf
   0 <= GenericInvestmentStorageBlock_total(storage_0) <= +inf
   0 <= GenericInvestmentStorageBlock_init_content(storage) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_0) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_1) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_2) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_3) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_4) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_5) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_6) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_7) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_8) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_9) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_10) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_11) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_12) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_13) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_14) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_15) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_16) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_17) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_18) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_19) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_20) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_21) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_22) <= +inf
   0 <= GenericInvestmentStorageBlock_storage_content(storage_23) <= +inf
end
