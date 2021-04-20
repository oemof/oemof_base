\* Source Pyomo model name=Model *\

min
objective:
+0 ONE_VAR_CONSTANT

s.t.

c_e_limit_storage_constraint(0)_:
+0.5 GenericStorageBlock_storage_content(storage1_0)
+1.25 GenericStorageBlock_storage_content(storage2_0)
-1 limit_storage(0)
= 0

c_e_limit_storage_constraint(1)_:
+0.5 GenericStorageBlock_storage_content(storage1_1)
+1.25 GenericStorageBlock_storage_content(storage2_1)
-1 limit_storage(1)
= 0

c_e_limit_storage_constraint(2)_:
+0.5 GenericStorageBlock_storage_content(storage1_2)
+1.25 GenericStorageBlock_storage_content(storage2_2)
-1 limit_storage(2)
= 0

c_e_Bus_balance(bus_0)_:
-1 flow(bus_storage1_0)
-1 flow(bus_storage2_0)
+1 flow(storage1_bus_0)
+1 flow(storage2_bus_0)
= 0

c_e_Bus_balance(bus_1)_:
-1 flow(bus_storage1_1)
-1 flow(bus_storage2_1)
+1 flow(storage1_bus_1)
+1 flow(storage2_bus_1)
= 0

c_e_Bus_balance(bus_2)_:
-1 flow(bus_storage1_2)
-1 flow(bus_storage2_2)
+1 flow(storage1_bus_2)
+1 flow(storage2_bus_2)
= 0

c_e_GenericStorageBlock_balance(storage1_0)_:
+1 GenericStorageBlock_storage_content(storage1_0)
-1 GenericStorageBlock_storage_content(storage1__1)
-1 flow(bus_storage1_0)
+1 flow(storage1_bus_0)
= 0

c_e_GenericStorageBlock_balance(storage1_1)_:
-1 GenericStorageBlock_storage_content(storage1_0)
+1 GenericStorageBlock_storage_content(storage1_1)
-1 flow(bus_storage1_1)
+1 flow(storage1_bus_1)
= 0

c_e_GenericStorageBlock_balance(storage1_2)_:
-1 GenericStorageBlock_storage_content(storage1_1)
+1 GenericStorageBlock_storage_content(storage1_2)
-1 flow(bus_storage1_2)
+1 flow(storage1_bus_2)
= 0

c_e_GenericStorageBlock_balance(storage2_0)_:
+1 GenericStorageBlock_storage_content(storage2_0)
-1 GenericStorageBlock_storage_content(storage2__1)
-1 flow(bus_storage2_0)
+1 flow(storage2_bus_0)
= 0

c_e_GenericStorageBlock_balance(storage2_1)_:
-1 GenericStorageBlock_storage_content(storage2_0)
+1 GenericStorageBlock_storage_content(storage2_1)
-1 flow(bus_storage2_1)
+1 flow(storage2_bus_1)
= 0

c_e_GenericStorageBlock_balance(storage2_2)_:
-1 GenericStorageBlock_storage_content(storage2_1)
+1 GenericStorageBlock_storage_content(storage2_2)
-1 flow(bus_storage2_2)
+1 flow(storage2_bus_2)
= 0

c_e_GenericStorageBlock_initial_cstr(storage1)_:
-1 GenericStorageBlock_init_content(storage1)
+1 GenericStorageBlock_storage_content(storage1__1)
= 0

c_e_GenericStorageBlock_initial_cstr(storage2)_:
-1 GenericStorageBlock_init_content(storage2)
+1 GenericStorageBlock_storage_content(storage2__1)
= 0

c_e_GenericStorageBlock_balanced_cstr(storage1)_:
-1 GenericStorageBlock_storage_content(storage1_2)
+1 GenericStorageBlock_storage_content(storage1__1)
= 0

c_e_GenericStorageBlock_balanced_cstr(storage2)_:
-1 GenericStorageBlock_storage_content(storage2_2)
+1 GenericStorageBlock_storage_content(storage2__1)
= 0

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(bus_storage1_0) <= +inf
   0 <= flow(bus_storage1_1) <= +inf
   0 <= flow(bus_storage1_2) <= +inf
   0 <= flow(bus_storage2_0) <= +inf
   0 <= flow(bus_storage2_1) <= +inf
   0 <= flow(bus_storage2_2) <= +inf
   0 <= flow(storage1_bus_0) <= +inf
   0 <= flow(storage1_bus_1) <= +inf
   0 <= flow(storage1_bus_2) <= +inf
   0 <= flow(storage2_bus_0) <= +inf
   0 <= flow(storage2_bus_1) <= +inf
   0 <= flow(storage2_bus_2) <= +inf
   0 <= limit_storage(0) <= 7
   0 <= limit_storage(1) <= 7
   0 <= limit_storage(2) <= 7
   0 <= GenericStorageBlock_storage_content(storage1__1) <= 5
   0 <= GenericStorageBlock_storage_content(storage1_0) <= 5
   0 <= GenericStorageBlock_storage_content(storage1_1) <= 5
   0 <= GenericStorageBlock_storage_content(storage1_2) <= 5
   0 <= GenericStorageBlock_storage_content(storage2__1) <= 5
   0 <= GenericStorageBlock_storage_content(storage2_0) <= 5
   0 <= GenericStorageBlock_storage_content(storage2_1) <= 5
   0 <= GenericStorageBlock_storage_content(storage2_2) <= 5
   0 <= GenericStorageBlock_init_content(storage1) <= 5
   0 <= GenericStorageBlock_init_content(storage2) <= 5
end
