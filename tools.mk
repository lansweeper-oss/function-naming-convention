HOST_ARCH := $(shell uname -m)
HOST_RAW_OS := $(shell uname -s)
HOST_OS := $(shell echo $(HOST_RAW_OS) | tr '[:upper:]' '[:lower:]')

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

TIME := `date +%H:%M:%S`

define LOG_ECHO
	echo -e "# \033[0;36m${TIME} \033[0;32m[INFO]\033[0m${1}"
endef

define LOG_INFO
	@$(if $(filter $(V), 1 2), $(call LOG_ECHO, $(strip $(1))))
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

CROSSPLANE_CLI_VERSION ?= v2.2.0
CROSSPLANE_CLI_DOWNLOAD_URL ?= https://raw.githubusercontent.com/crossplane/crossplane/refs/tags/$(CROSSPLANE_CLI_VERSION)/install.sh

CROSSPLANE ?= $(TOOLS_BIN_DIR)/crossplane

$(CROSSPLANE):
	@$(MAKE) -s tools.prepare
	$(call LOG_INFO, "🌏 Installing Crossplane CLI $(CROSSPLANE_CLI_VERSION)")
	@curl -sL $(CROSSPLANE_CLI_DOWNLOAD_URL) -o $(TOOLS_TMP_DIR)/install.sh
	@XP_VERSION=$(CROSSPLANE_CLI_VERSION) sh $(TOOLS_TMP_DIR)/install.sh > /dev/null
	@mv crossplane $(CROSSPLANE)
	@rm -rf $(TOOLS_TMP_DIR)/install.sh
	$(call LOG_INFO, "🌍 Crossplane CLI $(CROSSPLANE_CLI_VERSION) installed to $(CROSSPLANE)")

# ====================================================================================
# hatch

HATCH_VERSION ?= v1.16.3
HATCH_NUM_VERSION = $(HATCH_VERSION:v%=%)
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
	@$(MAKE) -s tools.prepare
	$(call LOG_INFO, "🌏 Installing Hatch $(HATCH_VERSION)")
	@curl -sL $(HATCH_DOWNLOAD_URL) -o $(TOOLS_TMP_DIR)/hatch.tgz
	@tar xz -C $(TOOLS_TMP_DIR) -f $(TOOLS_TMP_DIR)/hatch.tgz
	@mv $(TOOLS_TMP_DIR)/hatch $(HATCH)
	$(call LOG_INFO, "🌍 Hatch $(HATCH_VERSION) installed to $(HATCH)")

# ====================================================================================
# docker / podman
# if docker is not present, try with podman

DOCKER ?= $(shell command -v docker 2> /dev/null)
PODMAN ?= $(shell command -v podman 2> /dev/null)

ifeq ($(DOCKER),)
DOCKER = $(PODMAN)
endif

# ====================================================================================
# clean

tools.clean:
	$(call LOG_INFO, "🧹 Removing tools directory $(TOOLS_DIR)")
	@rm -rf $(TOOLS_DIR)
