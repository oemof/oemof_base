\* Source Pyomo model name=Model *\

min
objective:
+99 InvestmentFlow_invest(electricityBus_storage5)

s.t.

c_e_Bus_balance(electricityBus_0)_:
-1 flow(electricityBus_storage5_0)
+1 flow(storage5_electricityBus_0)
= 0

c_e_Bus_balance(electricityBus_1)_:
-1 flow(electricityBus_storage5_1)
+1 flow(storage5_electricityBus_1)
= 0

c_e_Bus_balance(electricityBus_2)_:
-1 flow(electricityBus_storage5_2)
+1 flow(storage5_electricityBus_2)
= 0

c_u_InvestmentFlow_max(electricityBus_storage5_0)_:
-1 InvestmentFlow_invest(electricityBus_storage5)
+1 flow(electricityBus_storage5_0)
<= 110

c_u_InvestmentFlow_max(electricityBus_storage5_1)_:
-1 InvestmentFlow_invest(electricityBus_storage5)
+1 flow(electricityBus_storage5_1)
<= 110

c_u_InvestmentFlow_max(electricityBus_storage5_2)_:
-1 InvestmentFlow_invest(electricityBus_storage5)
+1 flow(electricityBus_storage5_2)
<= 110

c_u_InvestmentFlow_max(storage5_electricityBus_0)_:
-1 InvestmentFlow_invest(storage5_electricityBus)
+1 flow(storage5_electricityBus_0)
<= 100

c_u_InvestmentFlow_max(storage5_electricityBus_1)_:
-1 InvestmentFlow_invest(storage5_electricityBus)
+1 flow(storage5_electricityBus_1)
<= 100

c_u_InvestmentFlow_max(storage5_electricityBus_2)_:
-1 InvestmentFlow_invest(storage5_electricityBus)
+1 flow(storage5_electricityBus_2)
<= 100

c_e_GenericStorageBlock_balance(storage5_0)_:
+1 GenericStorageBlock_storage_content(storage5_0)
-1 GenericStorageBlock_storage_content(storage5__1)
-1 flow(electricityBus_storage5_0)
+1 flow(storage5_electricityBus_0)
= 0

c_e_GenericStorageBlock_balance(storage5_1)_:
-1 GenericStorageBlock_storage_content(storage5_0)
+1 GenericStorageBlock_storage_content(storage5_1)
-1 flow(electricityBus_storage5_1)
+1 flow(storage5_electricityBus_1)
= 0

c_e_GenericStorageBlock_balance(storage5_2)_:
-1 GenericStorageBlock_storage_content(storage5_1)
+1 GenericStorageBlock_storage_content(storage5_2)
-1 flow(electricityBus_storage5_2)
+1 flow(storage5_electricityBus_2)
= 0

c_e_GenericStorageBlock_initial_cstr(storage5)_:
-1 GenericStorageBlock_init_content(storage5)
+1 GenericStorageBlock_storage_content(storage5__1)
= 0

c_e_GenericStorageBlock_balanced_cstr(storage5)_:
-1 GenericStorageBlock_storage_content(storage5_2)
+1 GenericStorageBlock_storage_content(storage5__1)
= 0

c_e_GenericStorageBlock_power_coupled(storage5)_:
-1 InvestmentFlow_invest(electricityBus_storage5)
+1.1000000000000001 InvestmentFlow_invest(storage5_electricityBus)
= -1.4210854715202004e-14

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(electricityBus_storage5_0) <= +inf
   0 <= flow(electricityBus_storage5_1) <= +inf
   0 <= flow(electricityBus_storage5_2) <= +inf
   0 <= flow(storage5_electricityBus_0) <= +inf
   0 <= flow(storage5_electricityBus_1) <= +inf
   0 <= flow(storage5_electricityBus_2) <= +inf
   0 <= InvestmentFlow_invest(electricityBus_storage5) <= +inf
   0 <= InvestmentFlow_invest(storage5_electricityBus) <= +inf
   0 <= GenericStorageBlock_storage_content(storage5__1) <= 10000
   0 <= GenericStorageBlock_storage_content(storage5_0) <= 10000
   0 <= GenericStorageBlock_storage_content(storage5_1) <= 10000
   0 <= GenericStorageBlock_storage_content(storage5_2) <= 10000
   0 <= GenericStorageBlock_init_content(storage5) <= 10000
end
