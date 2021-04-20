\* Source Pyomo model name=Model *\

min
objective:
+99 InvestmentFlow_invest(electricityBus_storage3)
+9 InvestmentFlow_invest(storage3_electricityBus)

s.t.

c_e_Bus_balance(electricityBus_0)_:
-1 flow(electricityBus_storage3_0)
+1 flow(storage3_electricityBus_0)
= 0

c_e_Bus_balance(electricityBus_1)_:
-1 flow(electricityBus_storage3_1)
+1 flow(storage3_electricityBus_1)
= 0

c_e_Bus_balance(electricityBus_2)_:
-1 flow(electricityBus_storage3_2)
+1 flow(storage3_electricityBus_2)
= 0

c_u_InvestmentFlow_max(electricityBus_storage3_0)_:
-1 InvestmentFlow_invest(electricityBus_storage3)
+1 flow(electricityBus_storage3_0)
<= 0

c_u_InvestmentFlow_max(electricityBus_storage3_1)_:
-1 InvestmentFlow_invest(electricityBus_storage3)
+1 flow(electricityBus_storage3_1)
<= 0

c_u_InvestmentFlow_max(electricityBus_storage3_2)_:
-1 InvestmentFlow_invest(electricityBus_storage3)
+1 flow(electricityBus_storage3_2)
<= 0

c_u_InvestmentFlow_max(storage3_electricityBus_0)_:
-1 InvestmentFlow_invest(storage3_electricityBus)
+1 flow(storage3_electricityBus_0)
<= 0

c_u_InvestmentFlow_max(storage3_electricityBus_1)_:
-1 InvestmentFlow_invest(storage3_electricityBus)
+1 flow(storage3_electricityBus_1)
<= 0

c_u_InvestmentFlow_max(storage3_electricityBus_2)_:
-1 InvestmentFlow_invest(storage3_electricityBus)
+1 flow(storage3_electricityBus_2)
<= 0

c_e_GenericStorageBlock_balance(storage3_0)_:
+1 GenericStorageBlock_storage_content(storage3_0)
-1 GenericStorageBlock_storage_content(storage3__1)
-1 flow(electricityBus_storage3_0)
+1 flow(storage3_electricityBus_0)
= 0

c_e_GenericStorageBlock_balance(storage3_1)_:
-1 GenericStorageBlock_storage_content(storage3_0)
+1 GenericStorageBlock_storage_content(storage3_1)
-1 flow(electricityBus_storage3_1)
+1 flow(storage3_electricityBus_1)
= 0

c_e_GenericStorageBlock_balance(storage3_2)_:
-1 GenericStorageBlock_storage_content(storage3_1)
+1 GenericStorageBlock_storage_content(storage3_2)
-1 flow(electricityBus_storage3_2)
+1 flow(storage3_electricityBus_2)
= 0

c_e_GenericStorageBlock_initial_cstr(storage3)_:
-1 GenericStorageBlock_init_content(storage3)
+1 GenericStorageBlock_storage_content(storage3__1)
= 0

c_e_GenericStorageBlock_balanced_cstr(storage3)_:
-1 GenericStorageBlock_storage_content(storage3_2)
+1 GenericStorageBlock_storage_content(storage3__1)
= 0

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(electricityBus_storage3_0) <= +inf
   0 <= flow(electricityBus_storage3_1) <= +inf
   0 <= flow(electricityBus_storage3_2) <= +inf
   0 <= flow(storage3_electricityBus_0) <= +inf
   0 <= flow(storage3_electricityBus_1) <= +inf
   0 <= flow(storage3_electricityBus_2) <= +inf
   0 <= InvestmentFlow_invest(electricityBus_storage3) <= +inf
   0 <= InvestmentFlow_invest(storage3_electricityBus) <= +inf
   0 <= GenericStorageBlock_storage_content(storage3__1) <= 5000
   0 <= GenericStorageBlock_storage_content(storage3_0) <= 5000
   0 <= GenericStorageBlock_storage_content(storage3_1) <= 5000
   0 <= GenericStorageBlock_storage_content(storage3_2) <= 5000
   0 <= GenericStorageBlock_init_content(storage3) <= 5000
end
