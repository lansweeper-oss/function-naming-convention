HOST_ARCH := $(shell uname -m)
HOST_RAW_OS := $(shell uname -s)
HOST_OS := $(shell echo $(HOST_RAW_OS) | tr '[:upper:]' '[:lower:]')
TIME := `date +%H:%M:%S`

# translate x86_64 to amd64
ifeq ($(HOST_ARCH),x86_64)
	TARGET_ARCH := amd64
endif

# translate aarch64 to arm64
ifeq ($(HOST_ARCH),aarch64)
	TARGET_ARCH := arm64
endif

ifeq ($(origin TARGET_ARCH),undefined)
	TARGET_ARCH := $(HOST_ARCH)
endif

define LOG_ECHO
	$(if $(filter-out -1,$(V)), echo -e "\033[0;36m${TIME} \033[0;32m[INFO]\033[0m${1}" 1>&2)
endef

define LOG_INFO
	$(if $(filter $(V), 1 2), $(call LOG_ECHO, $(strip $(1))))
endef

# Install a tool binary.
# $(1) = display name
# $(2) = version
# $(3) = download URL
# $(4) = install commands (use TOOLS_TMP_DIR / TOOLS_BIN_DIR)
define INSTALL_TOOL
	@$(MAKE) -s tools.prepare
	$(call LOG_ECHO, "🌏 Installing $(1) $(2)")
	@curl -sL $(3) -o $(TOOLS_TMP_DIR)/$(1).download
	$(4)
	@chmod +x $@
	$(call LOG_ECHO, "🌍 $(1) $(2) installed to $@")
endef

# ====================================================================================
# Tools directories
TOOLS_DIR ?= $(shell pwd)/.tools
TOOLS_BIN_DIR ?= $(TOOLS_DIR)/bin
TOOLS_TMP_DIR ?= $(TOOLS_DIR)/tmp

tools.prepare:
	@mkdir -p $(TOOLS_BIN_DIR)
	@mkdir -p $(TOOLS_TMP_DIR)

# ====================================================================================
# Crossplane CLI

CROSSPLANE_CLI_VERSION ?= v2.3.3
CROSSPLANE_CLI_DOWNLOAD_URL ?= https://cli.crossplane.io/stable/$(CROSSPLANE_CLI_VERSION)/bin/$(HOST_OS)_$(TARGET_ARCH)/crossplane

CROSSPLANE_CLI ?= $(TOOLS_BIN_DIR)/crossplane-cli

$(CROSSPLANE_CLI):
	@$(call INSTALL_TOOL,crossplane-cli,$(CROSSPLANE_CLI_VERSION),$(CROSSPLANE_CLI_DOWNLOAD_URL),\
		@mv $(TOOLS_TMP_DIR)/crossplane-cli.download $@)

# Keep CROSSPLANE as alias for backwards compatibility with Makefile targets
CROSSPLANE ?= $(CROSSPLANE_CLI)

# ====================================================================================
# hatch

HATCH_VERSION ?= v1.17.0
HATCH_BINARY_NAME = hatch-$(HOST_ARCH)-unknown-$(HOST_OS)-gnu
HATCH = $(TOOLS_BIN_DIR)/hatch

ifeq ($(HOST_OS),darwin)
ifeq ($(HOST_ARCH),arm64)
HATCH_BINARY_NAME = hatch-aarch64-apple-$(HOST_OS)
else
HATCH_BINARY_NAME = hatch-x86_64-apple-$(HOST_OS)
endif
endif

HATCH_DOWNLOAD_URL ?= https://github.com/pypa/hatch/releases/download/hatch-$(HATCH_VERSION)/$(HATCH_BINARY_NAME).tar.gz

$(HATCH):
	@$(call INSTALL_TOOL,hatch,$(HATCH_VERSION),$(HATCH_DOWNLOAD_URL),\
		@tar xzf $(TOOLS_TMP_DIR)/hatch.download -C $(TOOLS_BIN_DIR))

# ====================================================================================
# docker / podman
# if docker is not present, try with podman

DOCKER ?= $(shell command -v docker 2> /dev/null)
PODMAN ?= $(shell command -v podman 2> /dev/null)

ifeq ($(DOCKER),)
DOCKER = $(PODMAN)
endif

# ====================================================================================
# up CLI

UP_VERSION ?= v0.44.3
UP = $(TOOLS_BIN_DIR)/up

$(UP):
	@$(MAKE) -s tools.prepare
	$(call LOG_ECHO, "🌏 Installing Up CLI $(UP_VERSION)")
	@curl -sL "https://cli.upbound.io" | VERSION=$(UP_VERSION) sh
	@mv up $(UP)
	$(call LOG_ECHO, "🌍 Up CLI $(UP_VERSION) installed to $(UP)")

# ====================================================================================
# clean

tools.clean:
	$(call LOG_INFO, "🧹 Removing tools directory $(TOOLS_DIR)")
	@rm -rf $(TOOLS_DIR)
