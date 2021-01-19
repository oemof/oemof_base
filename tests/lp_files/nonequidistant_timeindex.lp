\* Source Pyomo model name=Model *\

min
objective:
+100 flow(gas_boiler_0)
+100 flow(gas_boiler_1)
+100 flow(gas_boiler_2)
+200 flow(gas_boiler_3)
+200 flow(gas_boiler_4)
+50 flow(gas_boiler_5)
+50 flow(gas_boiler_6)
+50 flow(gas_boiler_7)
+56 flow(heat_storage_0)
+56 flow(heat_storage_1)
+56 flow(heat_storage_2)
+112 flow(heat_storage_3)
+112 flow(heat_storage_4)
+28 flow(heat_storage_5)
+28 flow(heat_storage_6)
+28 flow(heat_storage_7)
+24 flow(storage_heat_0)
+24 flow(storage_heat_1)
+24 flow(storage_heat_2)
+48 flow(storage_heat_3)
+48 flow(storage_heat_4)
+12 flow(storage_heat_5)
+12 flow(storage_heat_6)
+12 flow(storage_heat_7)

s.t.

c_e_Bus_balance(gas_0)_:
+1 flow(gas_boiler_0)
= 0

c_e_Bus_balance(gas_1)_:
+1 flow(gas_boiler_1)
= 0

c_e_Bus_balance(gas_2)_:
+1 flow(gas_boiler_2)
= 0

c_e_Bus_balance(gas_3)_:
+1 flow(gas_boiler_3)
= 0

c_e_Bus_balance(gas_4)_:
+1 flow(gas_boiler_4)
= 0

c_e_Bus_balance(gas_5)_:
+1 flow(gas_boiler_5)
= 0

c_e_Bus_balance(gas_6)_:
+1 flow(gas_boiler_6)
= 0

c_e_Bus_balance(gas_7)_:
+1 flow(gas_boiler_7)
= 0

c_e_Bus_balance(heat_0)_:
+1 flow(boiler_heat_0)
-1 flow(heat_storage_0)
+1 flow(storage_heat_0)
= 0

c_e_Bus_balance(heat_1)_:
+1 flow(boiler_heat_1)
-1 flow(heat_storage_1)
+1 flow(storage_heat_1)
= 0

c_e_Bus_balance(heat_2)_:
+1 flow(boiler_heat_2)
-1 flow(heat_storage_2)
+1 flow(storage_heat_2)
= 0

c_e_Bus_balance(heat_3)_:
+1 flow(boiler_heat_3)
-1 flow(heat_storage_3)
+1 flow(storage_heat_3)
= 0

c_e_Bus_balance(heat_4)_:
+1 flow(boiler_heat_4)
-1 flow(heat_storage_4)
+1 flow(storage_heat_4)
= 0

c_e_Bus_balance(heat_5)_:
+1 flow(boiler_heat_5)
-1 flow(heat_storage_5)
+1 flow(storage_heat_5)
= 0

c_e_Bus_balance(heat_6)_:
+1 flow(boiler_heat_6)
-1 flow(heat_storage_6)
+1 flow(storage_heat_6)
= 0

c_e_Bus_balance(heat_7)_:
+1 flow(boiler_heat_7)
-1 flow(heat_storage_7)
+1 flow(storage_heat_7)
= 0

c_e_Transformer_relation(boiler_gas_heat_0)_:
-1 flow(boiler_heat_0)
+1 flow(gas_boiler_0)
= 0

c_e_Transformer_relation(boiler_gas_heat_1)_:
-1 flow(boiler_heat_1)
+1 flow(gas_boiler_1)
= 0

c_e_Transformer_relation(boiler_gas_heat_2)_:
-1 flow(boiler_heat_2)
+1 flow(gas_boiler_2)
= 0

c_e_Transformer_relation(boiler_gas_heat_3)_:
-1 flow(boiler_heat_3)
+1 flow(gas_boiler_3)
= 0

c_e_Transformer_relation(boiler_gas_heat_4)_:
-1 flow(boiler_heat_4)
+1 flow(gas_boiler_4)
= 0

c_e_Transformer_relation(boiler_gas_heat_5)_:
-1 flow(boiler_heat_5)
+1 flow(gas_boiler_5)
= 0

c_e_Transformer_relation(boiler_gas_heat_6)_:
-1 flow(boiler_heat_6)
+1 flow(gas_boiler_6)
= 0

c_e_Transformer_relation(boiler_gas_heat_7)_:
-1 flow(boiler_heat_7)
+1 flow(gas_boiler_7)
= 0

c_e_GenericStorageBlock_balance_first(storage)_:
+1 GenericStorageBlock_storage_content(storage_0)
-1 flow(heat_storage_0)
+1 flow(storage_heat_0)
= 270

c_e_GenericStorageBlock_balance(storage_1)_:
-0.90000000000000002 GenericStorageBlock_storage_content(storage_0)
+1 GenericStorageBlock_storage_content(storage_1)
-1 flow(heat_storage_1)
+1 flow(storage_heat_1)
= 0

c_e_GenericStorageBlock_balance(storage_2)_:
-0.90000000000000002 GenericStorageBlock_storage_content(storage_1)
+1 GenericStorageBlock_storage_content(storage_2)
-1 flow(heat_storage_2)
+1 flow(storage_heat_2)
= 0

c_e_GenericStorageBlock_balance(storage_3)_:
-0.81000000000000005 GenericStorageBlock_storage_content(storage_2)
+1 GenericStorageBlock_storage_content(storage_3)
-2 flow(heat_storage_3)
+2 flow(storage_heat_3)
= 0

c_e_GenericStorageBlock_balance(storage_4)_:
-0.81000000000000005 GenericStorageBlock_storage_content(storage_3)
+1 GenericStorageBlock_storage_content(storage_4)
-2 flow(heat_storage_4)
+2 flow(storage_heat_4)
= 0

c_e_GenericStorageBlock_balance(storage_5)_:
-0.94868329805051377 GenericStorageBlock_storage_content(storage_4)
+1 GenericStorageBlock_storage_content(storage_5)
-0.5 flow(heat_storage_5)
+0.5 flow(storage_heat_5)
= 0

c_e_GenericStorageBlock_balance(storage_6)_:
-0.94868329805051377 GenericStorageBlock_storage_content(storage_5)
+1 GenericStorageBlock_storage_content(storage_6)
-0.5 flow(heat_storage_6)
+0.5 flow(storage_heat_6)
= 0

c_e_GenericStorageBlock_balance(storage_7)_:
-0.94868329805051377 GenericStorageBlock_storage_content(storage_6)
+1 GenericStorageBlock_storage_content(storage_7)
-0.5 flow(heat_storage_7)
+0.5 flow(storage_heat_7)
= 0

c_e_GenericStorageBlock_balanced_cstr(storage)_:
+1 GenericStorageBlock_storage_content(storage_7)
= 300

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(boiler_heat_0) <= 200
   0 <= flow(boiler_heat_1) <= 200
   0 <= flow(boiler_heat_2) <= 200
   0 <= flow(boiler_heat_3) <= 200
   0 <= flow(boiler_heat_4) <= 200
   0 <= flow(boiler_heat_5) <= 200
   0 <= flow(boiler_heat_6) <= 200
   0 <= flow(boiler_heat_7) <= 200
   0 <= flow(gas_boiler_0) <= +inf
   0 <= flow(gas_boiler_1) <= +inf
   0 <= flow(gas_boiler_2) <= +inf
   0 <= flow(gas_boiler_3) <= +inf
   0 <= flow(gas_boiler_4) <= +inf
   0 <= flow(gas_boiler_5) <= +inf
   0 <= flow(gas_boiler_6) <= +inf
   0 <= flow(gas_boiler_7) <= +inf
   0 <= flow(heat_storage_0) <= 100
   0 <= flow(heat_storage_1) <= 100
   0 <= flow(heat_storage_2) <= 100
   0 <= flow(heat_storage_3) <= 100
   0 <= flow(heat_storage_4) <= 100
   0 <= flow(heat_storage_5) <= 100
   0 <= flow(heat_storage_6) <= 100
   0 <= flow(heat_storage_7) <= 100
   0 <= flow(storage_heat_0) <= 100
   0 <= flow(storage_heat_1) <= 100
   0 <= flow(storage_heat_2) <= 100
   0 <= flow(storage_heat_3) <= 100
   0 <= flow(storage_heat_4) <= 100
   0 <= flow(storage_heat_5) <= 100
   0 <= flow(storage_heat_6) <= 100
   0 <= flow(storage_heat_7) <= 100
   0 <= GenericStorageBlock_storage_content(storage_0) <= 300
   0 <= GenericStorageBlock_storage_content(storage_1) <= 300
   0 <= GenericStorageBlock_storage_content(storage_2) <= 300
   0 <= GenericStorageBlock_storage_content(storage_3) <= 300
   0 <= GenericStorageBlock_storage_content(storage_4) <= 300
   0 <= GenericStorageBlock_storage_content(storage_5) <= 300
   0 <= GenericStorageBlock_storage_content(storage_6) <= 300
   0 <= GenericStorageBlock_storage_content(storage_7) <= 300
end