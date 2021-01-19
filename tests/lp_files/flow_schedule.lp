\* Source Pyomo model name=Model *\

min
objective:
+999 Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_0)
+999 Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_1)
+999 Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_2)
+800 Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_1)
+900 Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_2)

s.t.

c_e_Bus_balance(bus_gas_0)_:
+1 flow(bus_gas_boiler_penalty_0)
= 0

c_e_Bus_balance(bus_gas_1)_:
+1 flow(bus_gas_boiler_penalty_1)
= 0

c_e_Bus_balance(bus_gas_2)_:
+1 flow(bus_gas_boiler_penalty_2)
= 0

c_e_Bus_balance(bus_th_penalty_0)_:
+1 flow(boiler_penalty_bus_th_penalty_0)
= 0

c_e_Bus_balance(bus_th_penalty_1)_:
+1 flow(boiler_penalty_bus_th_penalty_1)
= 0

c_e_Bus_balance(bus_th_penalty_2)_:
+1 flow(boiler_penalty_bus_th_penalty_2)
= 0

c_e_Transformer_relation(boiler_penalty_bus_gas_bus_th_penalty_0)_:
-1 flow(boiler_penalty_bus_th_penalty_0)
+1 flow(bus_gas_boiler_penalty_0)
= 0

c_e_Transformer_relation(boiler_penalty_bus_gas_bus_th_penalty_1)_:
-1 flow(boiler_penalty_bus_th_penalty_1)
+1 flow(bus_gas_boiler_penalty_1)
= 0

c_e_Transformer_relation(boiler_penalty_bus_gas_bus_th_penalty_2)_:
-1 flow(boiler_penalty_bus_th_penalty_2)
+1 flow(bus_gas_boiler_penalty_2)
= 0

c_e_Flow_schedule_constr(boiler_penalty_bus_th_penalty_1)_:
-1 Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_1)
+1 Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_1)
+1 flow(boiler_penalty_bus_th_penalty_1)
= 300

c_e_Flow_schedule_constr(boiler_penalty_bus_th_penalty_2)_:
-1 Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_2)
+1 Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_2)
+1 flow(boiler_penalty_bus_th_penalty_2)
= 50

c_e_ONE_VAR_CONSTANT:
ONE_VAR_CONSTANT = 1.0

bounds
   0 <= flow(boiler_penalty_bus_th_penalty_0) <= 200
   0 <= flow(boiler_penalty_bus_th_penalty_1) <= 200
   0 <= flow(boiler_penalty_bus_th_penalty_2) <= 200
   0 <= flow(bus_gas_boiler_penalty_0) <= +inf
   0 <= flow(bus_gas_boiler_penalty_1) <= +inf
   0 <= flow(bus_gas_boiler_penalty_2) <= +inf
   0 <= Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_1) <= +inf
   0 <= Flow_schedule_slack_pos(boiler_penalty_bus_th_penalty_2) <= +inf
   0 <= Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_0) <= +inf
   0 <= Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_1) <= +inf
   0 <= Flow_schedule_slack_neg(boiler_penalty_bus_th_penalty_2) <= +inf
end
