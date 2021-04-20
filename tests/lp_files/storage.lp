\* Source Pyomo model name=Model *\

min
objective:
+56 flow(electricityBus_storage_no_invest_0)
+56 flow(electricityBus_storage_no_invest_1)
+56 flow(electricityBus_storage_no_invest_2)
+24 flow(storage_no_invest_electricityBus_0)
+24 flow(storage_no_invest_electricityBus_1)
+24 flow(storage_no_invest_electricityBus_2)

s.t.

c_e_Bus_balance(electricityBus_0)_:
-1 flow(electricityBus_storage_no_invest_0)
+1 flow(storage_no_invest_electricityBus_0)
= 0

c_e_Bus_balance(electricityBus_1)_:
-1 flow(electricityBus_storage_no_invest_1)
+1 flow(storage_no_invest_electricityBus_1)
= 0

c_e_Bus_balance(electricityBus_2)_:
-1 flow(electricityBus_storage_no_invest_2)
+1 flow(storage_no_invest_electricityBus_2)
= 0

c_e_GenericStorageBlock_balance(storage_no_invest_0)_:
+1 GenericStorageBlock_storage_content(storage_no_invest_0)
-0.87 GenericStorageBlock_storage_content(storage_no_invest__1)
-0.96999999999999997 flow(electricityBus_storage_no_invest_0)
+1.1627906976744187 flow(storage_no_invest_electricityBus_0)
= 0

c_e_GenericStorageBlock_balance(storage_no_invest_1)_:
-0.87 GenericStorageBlock_storage_content(storage_no_invest_0)
+1 GenericStorageBlock_storage_content(storage_no_invest_1)
-0.96999999999999997 flow(electricityBus_storage_no_invest_1)
+1.1627906976744187 flow(storage_no_invest_electricityBus_1)
= 0

c_e_GenericStorageBlock_balance(storage_no_invest_2)_:
-0.87 GenericStorageBlock_storage_content(storage_no_invest_1)
+1 GenericStorageBlock_storage_content(storage_no_invest_2)
-0.96999999999999997 flow(electricityBus_storage_no_invest_2)
+1.1627906976744187 flow(storage_no_invest_electricityBus_2)
= 0

c_e_GenericStorageBlock_initial_cstr(storage_no_invest)_:
+1 GenericStorageBlock_storage_content(storage_no_invest__1)
= 40000

c_e_GenericStorageBlock_balanced_cstr(storage_no_invest)_:
-1 GenericStorageBlock_storage_content(storage_no_invest_2)
+1 GenericStorageBlock_storage_content(storage_no_invest__1)
= 0

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(electricityBus_storage_no_invest_0) <= 16667
   0 <= flow(electricityBus_storage_no_invest_1) <= 16667
   0 <= flow(electricityBus_storage_no_invest_2) <= 16667
   0 <= flow(storage_no_invest_electricityBus_0) <= 16667
   0 <= flow(storage_no_invest_electricityBus_1) <= 16667
   0 <= flow(storage_no_invest_electricityBus_2) <= 16667
   0 <= GenericStorageBlock_storage_content(storage_no_invest__1) <= 100000
   0 <= GenericStorageBlock_storage_content(storage_no_invest_0) <= 100000
   0 <= GenericStorageBlock_storage_content(storage_no_invest_1) <= 100000
   0 <= GenericStorageBlock_storage_content(storage_no_invest_2) <= 100000
end
