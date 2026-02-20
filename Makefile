# This file requires GNU Make
SHELL := /bin/bash
.PHONY: all build build-all clean deploy deploy-all docs dump e2e fne2e lint new print publish readme render render-all render-dependencies run schema schemas test validate template
.ONESHELL:

-include tools.mk

ifndef arch
	arch := linux/amd64 linux/arm64
endif

ifndef tag
	tag := latest
endif

build_args :=
cmd_args :=
flavour :=
name := function-naming-convention
render_flags :=
temp_dir :=

ifdef builder
	build_args += --builder $(builder)
endif

ifdef V
	render_flags += -x -v
	verbose := true
ifeq ($(V), 2)
	render_flags += -V
endif
else
	build_args += -q
endif

define PRE_CLI
	$(if $(filter $(V), 1), $(call LOG_ECHO, "🔊 Verbose mode enabled"))
	$(if $(filter $(V), 2), $(call LOG_ECHO, "🗣️ Chatterbox mode enabled"))
	@temp_dir=`mktemp -d`
endef

define POST_CLI
	@$(if $(filter $(V), 1 2), $(call LOG_ECHO, "📂 Temporary files left intact in: $$temp_dir"), rm -rf $$temp_dir)
endef

build: $(CROSSPLANE) $(DOCKER) $(HATCH)
	@$(call PRE_CLI)
	@$(HATCH) clean
	@echo "🔨 Building $(name) for arch $(arch)..."
	@for arch in $(arch)
	@do
		@suffix=$$(echo $$arch | tr '/' '-')
		@$(DOCKER) buildx build $(build_args) --no-cache --platform $$arch . --output=type=docker,dest=$$temp_dir/runtime-$$suffix.tar
		@$(CROSSPLANE) xpkg build -f package --embed-runtime-image-tarball=$$temp_dir/runtime-$$suffix.tar -o $(name)-$$suffix.xpkg || { \
			$(call LOG_ECHO, "❌ Failed to build $(name)-$$suffix.xpkg"); \
			exit 1; \
		}
		@$(call LOG_ECHO, "✅ Function successfully built as $(name)-$$suffix.xpkg")
	@done
	@$(call POST_CLI)

lint: $(HATCH)
	$(HATCH) clean && $(HATCH) run lint:check || exit $$?
	@yamllint .

publish: $(CROSSPLANE) $(DOCKER)
	@for arch in $(arch)
	@do
		@suffix=$$(echo $$arch | tr '/' '-')
		@package=$${package:+$${package},}$(name)-$$suffix.xpkg
	@done

	@$(MAKE) -s build || { \
		$(call LOG_ECHO, "❌ Build failed"); \
		exit $$?; \
	}

	@image=ghcr.io/$(owner)/$(name):$(tag)
	@$(call LOG_ECHO, "🌏 Pushing package $(name) as $$image...")
	@$(CROSSPLANE) xpkg push -f $$package $$image || { \
		$(call LOG_ECHO, "❌ Failed to push $(name) as $$image"); \
		exit 1; \
	}
	@$(call LOG_ECHO, "🌍 Package $(name) successfully pushed as $$image")

	@image=xpkg.upbound.io/$(owner)/$(name):$(tag)
	@$(call LOG_ECHO, "🌏 Pushing package $(name) as $$image...")
	@$(CROSSPLANE) xpkg push -f $$(echo *.xpkg|tr ' ' ,) $$image || { \
		$(call LOG_ECHO, "❌ Failed to push $(name) as $$image"); \
		exit 1; \
	}
	@$(call LOG_ECHO, "🌍 Package $(name) successfully pushed as $$image")


run: $(HATCH)
	@$(call PRE_CLI)
	@$(HATCH) run development || exit $$?

test: $(HATCH)
	@$(HATCH) run test:unit || exit $$?

validate: $(HATCH)
	@$(MAKE) -s lint || exit $$?
	@$(MAKE) -s test || exit $$?
