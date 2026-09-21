.PHONY: bootstrap docker-build test benchmark-retrieval live-gemini qwen-health

bootstrap:
	./scripts/bootstrap.sh

docker-build:
	docker build -t repopilot-runner:py312 -f docker/Dockerfile .

test:
	pytest tests/repopilot -q
	ruff check src/minisweagent/repopilot tests/repopilot

benchmark-retrieval:
	repopilot benchmark-retrieval --output docs/repopilot/results/retrieval-v1.json

live-gemini:
	pytest tests/live/test_gemini_repopilot.py -q -s

qwen-health:
	repopilot-local health
