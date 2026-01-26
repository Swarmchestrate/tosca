.PHONY: parse install

parse:
	@success=0; \
	fail=0; \
	for file in $(shell find templates -name "*.yaml"); do \
		echo "Processing $$file"; \
		if /usr/bin/puccini-tosca parse $$file -x data_types.string.permissive > /dev/null 2>&1; then \
			echo "✔️  Success: $$file"; \
			success=$$((success + 1)); \
		else \
			echo "❌ Failed: $$file"; \
			fail=$$((fail + 1)); \
			echo "---- Error Output ----"; \
			/usr/bin/puccini-tosca parse $$file -x data_types.string.permissive; \
			echo "----------------------"; \
		fi; \
	done; \
	echo "----------------------------"; \
	echo "✅ Total Successful: $$success"; \
	echo "❌ Total Failed: $$fail"; \
	echo "----------------------------"; \
	if [ $$fail -gt 0 ]; then \
		exit 1; \
	fi

install:
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv sync
	wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb && \
	sudo dpkg -i go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb || sudo apt --fix-broken install -y && \
	rm -f go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
