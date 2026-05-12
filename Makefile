# Convenience targets for the TEP NAT agentic RCA workbench.

.PHONY: demo-nat demo-tools test-nat-tools eval-tools eval-agent

demo-nat:
	python backend/nat_runner.py --fault fault1 \
	    --question "Diagnose the current TEP anomaly and recommend operator review steps."

demo-tools:
	python backend/nat_runner.py --fault fault1 --tools-only \
	    --question "Diagnose the current TEP anomaly and recommend operator review steps."

test-nat-tools:
	python backend/evaluation/evaluate_nat_rca.py --tools-only

eval-tools:
	python backend/evaluation/evaluate_nat_rca.py --tools-only

eval-agent:
	python backend/evaluation/evaluate_nat_rca.py --run-agent
