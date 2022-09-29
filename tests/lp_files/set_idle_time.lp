\* Source Pyomo model name=Model *\

min 
objective:
+0 ONE_VAR_CONSTANT

s.t.

c_u_constraint_idle_time(0_0)_:
+1 NonConvexFlowBlock_status(Bus_Sink_0)
+1 NonConvexFlowBlock_status(Source_Bus_0)
<= 1

c_u_constraint_idle_time(1_0)_:
+1 NonConvexFlowBlock_status(Bus_Sink_1)
+1 NonConvexFlowBlock_status(Source_Bus_0)
<= 1

c_u_constraint_idle_time(1_1)_:
+1 NonConvexFlowBlock_status(Bus_Sink_1)
+1 NonConvexFlowBlock_status(Source_Bus_1)
<= 1

c_u_constraint_idle_time(2_1)_:
+1 NonConvexFlowBlock_status(Bus_Sink_2)
+1 NonConvexFlowBlock_status(Source_Bus_1)
<= 1

c_u_constraint_idle_time(2_2)_:
+1 NonConvexFlowBlock_status(Bus_Sink_2)
+1 NonConvexFlowBlock_status(Source_Bus_2)
<= 1

c_e_BusBlock_balance(Bus_0)_:
-1 flow(Bus_Sink_0)
+1 flow(Source_Bus_0)
= 0

c_e_BusBlock_balance(Bus_1)_:
-1 flow(Bus_Sink_1)
+1 flow(Source_Bus_1)
= 0

c_e_BusBlock_balance(Bus_2)_:
-1 flow(Bus_Sink_2)
+1 flow(Source_Bus_2)
= 0

c_u_NonConvexFlowBlock_min(Bus_Sink_0)_:
+0.20000000000000001 NonConvexFlowBlock_status(Bus_Sink_0)
-1 flow(Bus_Sink_0)
<= 0

c_u_NonConvexFlowBlock_min(Bus_Sink_1)_:
+0.20000000000000001 NonConvexFlowBlock_status(Bus_Sink_1)
-1 flow(Bus_Sink_1)
<= 0

c_u_NonConvexFlowBlock_min(Bus_Sink_2)_:
+0.20000000000000001 NonConvexFlowBlock_status(Bus_Sink_2)
-1 flow(Bus_Sink_2)
<= 0

c_u_NonConvexFlowBlock_min(Source_Bus_0)_:
+0.20000000000000001 NonConvexFlowBlock_status(Source_Bus_0)
-1 flow(Source_Bus_0)
<= 0

c_u_NonConvexFlowBlock_min(Source_Bus_1)_:
+0.20000000000000001 NonConvexFlowBlock_status(Source_Bus_1)
-1 flow(Source_Bus_1)
<= 0

c_u_NonConvexFlowBlock_min(Source_Bus_2)_:
+0.20000000000000001 NonConvexFlowBlock_status(Source_Bus_2)
-1 flow(Source_Bus_2)
<= 0

c_u_NonConvexFlowBlock_max(Bus_Sink_0)_:
-1 NonConvexFlowBlock_status(Bus_Sink_0)
+1 flow(Bus_Sink_0)
<= 0

c_u_NonConvexFlowBlock_max(Bus_Sink_1)_:
-1 NonConvexFlowBlock_status(Bus_Sink_1)
+1 flow(Bus_Sink_1)
<= 0

c_u_NonConvexFlowBlock_max(Bus_Sink_2)_:
-1 NonConvexFlowBlock_status(Bus_Sink_2)
+1 flow(Bus_Sink_2)
<= 0

c_u_NonConvexFlowBlock_max(Source_Bus_0)_:
-1 NonConvexFlowBlock_status(Source_Bus_0)
+1 flow(Source_Bus_0)
<= 0

c_u_NonConvexFlowBlock_max(Source_Bus_1)_:
-1 NonConvexFlowBlock_status(Source_Bus_1)
+1 flow(Source_Bus_1)
<= 0

c_u_NonConvexFlowBlock_max(Source_Bus_2)_:
-1 NonConvexFlowBlock_status(Source_Bus_2)
+1 flow(Source_Bus_2)
<= 0

c_e_ONE_VAR_CONSTANT: 
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(Bus_Sink_0) <= 1
   0 <= flow(Bus_Sink_1) <= 1
   0 <= flow(Bus_Sink_2) <= 1
   0 <= flow(Source_Bus_0) <= 1
   0 <= flow(Source_Bus_1) <= 1
   0 <= flow(Source_Bus_2) <= 1
   0 <= NonConvexFlowBlock_status(Bus_Sink_0) <= 1
   0 <= NonConvexFlowBlock_status(Bus_Sink_1) <= 1
   0 <= NonConvexFlowBlock_status(Bus_Sink_2) <= 1
   0 <= NonConvexFlowBlock_status(Source_Bus_0) <= 1
   0 <= NonConvexFlowBlock_status(Source_Bus_1) <= 1
   0 <= NonConvexFlowBlock_status(Source_Bus_2) <= 1
binary
  NonConvexFlowBlock_status(Bus_Sink_0)
  NonConvexFlowBlock_status(Bus_Sink_1)
  NonConvexFlowBlock_status(Bus_Sink_2)
  NonConvexFlowBlock_status(Source_Bus_0)
  NonConvexFlowBlock_status(Source_Bus_1)
  NonConvexFlowBlock_status(Source_Bus_2)
end
