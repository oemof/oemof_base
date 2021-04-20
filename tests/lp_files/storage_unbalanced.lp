\* Source Pyomo model name=Model *\

min
objective:
+0 ONE_VAR_CONSTANT

s.t.

c_e_Bus_balance(electricityBus_0)_:
-1 flow(electricityBus_storage1_0)
+1 flow(storage1_electricityBus_0)
= 0

c_e_Bus_balance(electricityBus_1)_:
-1 flow(electricityBus_storage1_1)
+1 flow(storage1_electricityBus_1)
= 0

c_e_Bus_balance(electricityBus_2)_:
-1 flow(electricityBus_storage1_2)
+1 flow(storage1_electricityBus_2)
= 0

c_e_GenericStorageBlock_balance(storage1_0)_:
+1 GenericStorageBlock_storage_content(storage1_0)
-1 GenericStorageBlock_storage_content(storage1__1)
-1 flow(electricityBus_storage1_0)
+1 flow(storage1_electricityBus_0)
= 0

c_e_GenericStorageBlock_balance(storage1_1)_:
-1 GenericStorageBlock_storage_content(storage1_0)
+1 GenericStorageBlock_storage_content(storage1_1)
-1 flow(electricityBus_storage1_1)
+1 flow(storage1_electricityBus_1)
= 0

c_e_GenericStorageBlock_balance(storage1_2)_:
-1 GenericStorageBlock_storage_content(storage1_1)
+1 GenericStorageBlock_storage_content(storage1_2)
-1 flow(electricityBus_storage1_2)
+1 flow(storage1_electricityBus_2)
= 0

c_e_GenericStorageBlock_initial_cstr(storage1)_:
-1 GenericStorageBlock_init_content(storage1)
+1 GenericStorageBlock_storage_content(storage1__1)
= 0

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(electricityBus_storage1_0) <= +inf
   0 <= flow(electricityBus_storage1_1) <= +inf
   0 <= flow(electricityBus_storage1_2) <= +inf
   0 <= flow(storage1_electricityBus_0) <= +inf
   0 <= flow(storage1_electricityBus_1) <= +inf
   0 <= flow(storage1_electricityBus_2) <= +inf
   0 <= GenericStorageBlock_storage_content(storage1__1) <= 1111
   0 <= GenericStorageBlock_storage_content(storage1_0) <= 1111
   0 <= GenericStorageBlock_storage_content(storage1_1) <= 1111
   0 <= GenericStorageBlock_storage_content(storage1_2) <= 1111
   0 <= GenericStorageBlock_init_content(storage1) <= 1111
end
