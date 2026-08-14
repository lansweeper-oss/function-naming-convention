# function-naming-convention

A [Crossplane composition function][functions] designed to enforce consistent naming conventions and labelling/tagging
standards for composed resources.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Global Configuration (Function Inputs)](#global-configuration-function-inputs)
  - [Per-Resource Configuration (Annotations)](#per-resource-configuration-annotations)
- [Complete Examples](#complete-examples)
- [Advanced Features](#advanced-features)

## Overview

This function automatically mutates Crossplane managed resources to enforce naming conventions and tagging standards.
It can modify:

- `metadata.name` - The resource name in the management cluster
- `metadata.labels` - Standard Kubernetes labels
- `metadata.annotations["crossplane.io/external-name"]` - The external cloud provider name
- `spec.forProvider.name` - The name field in the provider spec
- `spec.initProvider.name` - The name field in the init provider spec
- `spec.forProvider.tags` - Cloud provider tags (AWS, etc.)
- `spec.forProvider.tags.Name` - The Name tag specifically

The function generates names by joining customizable **fields** with a **delimiter** (default: `-`).
For example, with fields `[tenant, accountCode, regionCode, domain]`, it generates names like:
`<tenant>-<accountCode>-<regionCode>-<domain>-<resourceName>` where `<foo>` is the corresponding value for key `foo`.

## How It Works

### Configuration Precedence

The function reads configuration from multiple sources with the following precedence (highest to lowest):

1. **Resource annotations** (per-resource, highest priority).
2. **Function input** (global to all resources).
3. **Function defaults** (built-in defaults).

### Data Sources

Field values for the naming template come from:

1. **Context** - Typically from `apiextensions.crossplane.io/environment` or any other custom context key.
2. **Function input values** - Static values defined in the function spec.
3. **Resource annotations** - Dynamic per-resource overrides.

### Name Generation Process

1. Read the environment context (e.g., from `EnvironmentConfig`).
2. Apply any value mappings (e.g., map `kind: Bucket` to `kindCode: s3`).
3. Build the name prefix from template fields.
4. Append the original resource name.
5. Sanitize to [RFC 1123][] compliance.
6. Apply to `metadata.name`, `external-name` annotation, `forProvider.name` and/or `initProvider.name`
  (or any other field as configured), labels and tags.

## Installation

```yaml
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-naming-convention
spec:
  package: REGISTRY/function-naming-convention:latest
  packagePullPolicy: Always
  revisionActivationPolicy: Automatic
  revisionHistoryLimit: 10
```

### Command line arguments

This function accepts the following arguments:

- `--address`: The address at which to listen for requests.
- `--tls-certs-dir`: The credentials used to authenticate requests.
- `--insecure`: Run without mTLS credentials. If you supply this flag --tls-certs-dir will be ignored.
- `--grpc-message-size`: Maximum gRPC message size in MiB for both send and receive
  (e.g. `4` for 4 MiB, which is gRPC's default).
- `--debug | -d`: Emit debug logs.

## Configuration

### Global Configuration (Function Inputs)

Global configuration applies to **all resources** processed by the function unless overridden by resource-specific
annotations.

#### Basic Naming Convention

Define the naming template and static values:

```yaml
- step: enforce-naming-convention
  functionRef:
    name: function-naming-convention
  input:
    apiVersion: naming-convention.fn.crossplane.com/v1alpha1
    kind: Input
    spec:
      # Define the order of fields in the name template
      nameTemplateFields:
        - tenant
        - accountCode
        - regionCode
        - domain

      # Override the default separator (default: "-")
      templateItemsSeparator: "-"

      # Provide static values (merged with context)
      values:
        fixedValue: production
```

**Example Result:**

- Context: `{tenant: "acme", accountCode: "prod", regionCode: "us1", domain: "api"}`.
- Resource name: `my_bucket`.
- Generated name: `acme-prod-us1-api-my-bucket` (Kubernetes) and `acme-prod-us1-api-my_bucket` (provider).

> Beware that the Kubernetes name is kebab-cased in order to comply to [RFC 1123][].

#### Context Configuration

Specify which Crossplane context to read:

```yaml
spec:
  # Use default environment context
  context: apiextensions.crossplane.io/environment

  # Or use a custom context
  context: custom-context

  # Or use a namespaced context with sub-key
  context: acme.org/my-context/sub-key
```

#### Environment

This function merges the context, inputs and annotations to create a per-invocation and per-resource in-memory
map that we refer to as _environment_.

#### Label Configuration

Map environment variables to Kubernetes labels:

```yaml
spec:
  # List of context keys to convert to labels
  envToLabel:
    - account
    - accountCode
    - region
    - regionCode
    - tenant
    - environment

  labels:
    # Add prefix to all generated labels (default: "")
    prefix: company

    # Separator between prefix and label key (default: "/")
    separator: "/"

    # Copy labels to spec.forProvider.tags (default: false)
    labelsAsTags: true

  # Convert label/tag keys to kebab-case (default: true)
  kebabCaseLabelsAndTags: true
```

**Example Result:**

```yaml
metadata:
  labels:
    company/account: production
    company/account-code: prod
    company/region: us-east-1
    company/region-code: us1
    company/tenant: acme
```

#### Tag Configuration

Inject tags into resources that support them (by default, under `spec.forProvider.tags`):

```yaml
spec:
  # Context field containing tags to inject
  tagsField: customTags

  # Static tags to add to all resources, added as-is
  tags:
    Environment: production
    ManagedBy: crossplane
    CostCenter: engineering
```

With a context like:

```yaml
customTags:
  foo: bar
```

**Example Result:**

```yaml
spec:
  forProvider:
    tags:
      foo: bar
      Environment: production
      ManagedBy: crossplane
      CostCenter: engineering
      # Plus any labels if labelsAsTags: true
```

#### Value Mapping

Map resource field values to template variables:

```yaml
spec:
  nameTemplateFields:
    - namePrefix
    - kindCode  # Will be populated from mapping

  valuesFromMap:
    - from: kind  # Source field (supports dot notation)
      to: kindCode  # Target template field
      maxLength: 4  # Max length for unmapped values (default: 4)
      fallback: dflt  # Default for unmapped values (default: "dflt")
      map:
        Bucket: s3
        Certificate: cert
        Cluster: eks
        EBSVolume: ebs
        InternetGateway: igw
        NATGateway: nat
        OpenIDConnectProvider: oidc
        Policy: iam
        Record: r53
        RouteTable: rtb
        SecurityGroup: sg
        SecurityGroupRule: sgr
        VPC: vpc
        VPCEndpoint: vpce
```

**Example Result:**

- Resource: `kind: Bucket`, `metadata.name: data`.
- Context: `{namePrefix: "acme-prod"}`.
- Generated name: `acme-prod-s3-data`.

#### Annotation Configuration

Customize the annotation prefix used by this function:

```yaml
spec:
  annotations:
    # Prefix for function-specific annotations (default: "function-naming-convention")
    prefix: fn.naming

    # Separator between prefix and annotation key (default: "/")
    separator: "-"
```

With this configuration, use annotations like: `fn.naming-external-name: "true"`

#### Response TTL

Control how long Crossplane caches the function response before re-running:

```yaml
spec:
  # Custom TTL in seconds (default: 60)
  responseTtl: 300

  # Disable caching entirely (useful for realtime compositions)
  responseTtl: 0
```

When `responseTtl` is set to `0`, the function response is never cached and will not contribute
to periodic reconciliations. This is useful for realtime compositions where resources must always
reflect the latest state.

See [HOWTO.md](HOWTO.md) for complete configuration examples and per-feature recipes.

### Per-Resource Configuration (Annotations)

Per-resource configuration uses annotations to override global settings or enable specific behaviors for individual
resources.
All annotations use the prefix `function-naming-convention/` by default (configurable globally).

**Note:** Function-specific annotations are automatically removed from resources after processing.

All available annotations are listed in the [Resource Annotations](#resource-annotations) reference table below.
Key behaviors:

- **Name control:** `skip-name-modify`, `name-template`, `name-fields-separator`, and custom field overrides via
  `<custom-field>` annotations.
- **Provider name:** `for-provider-name`, `for-provider-name-field`, `for-provider-nameoverride` (and equivalent
  `init-provider-*` variants). Supports dot notation for nested fields.
- **Tags:** `tag-name` (set `Name` tag), `labels-as-tags` (copy labels to tags), `tags-field` (load tags from
  context), `tags-to-field` (write tags to custom field path using dot notation).
- **Labels:** `labels-to-field` (replicate labels to arbitrary field).
- **Name length:** `restrict-rfc1123-name-length`, `crop-on-name-too-long`.

Without `nameoverride`, the function applies the naming convention to the existing value.
With `nameoverride`, it replaces it entirely. An empty provider name is also automatically overwritten.

Both camelCase and kebab-case work in annotations: `function-naming-convention/customField` is equivalent to
`function-naming-convention/custom-field`.

All boolean annotations accept `"true"`, `"yes"`, `"on"`, `"y"` (case-insensitive).

See [HOWTO.md](HOWTO.md) for usage examples and recipes.

## Advanced Features

### Dot Notation for Nested Fields

Both `valuesFromMap.from`, `for-provider-name-field` and `init-provider-name-field` support dot notation:

```yaml
# Map from nested resource field
valuesFromMap:
  - from: spec.forProvider.config.engineVersion
    to: engineVersion
    map:
      "5.7": mysql57
      "8.0": mysql80

# Write to nested forProvider field
metadata:
  annotations:
    function-naming-convention/for-provider-name-field: config.database.name
```

### Context Field Access

Access nested context fields using dot notation:

```yaml
# If context has nested structure:
# context:
#   network:
#     vpc:
#       id: vpc-123
#       cidr: 10.0.0.0/16

nameTemplateFields:
  - tenant
  - network.vpc.id  # Access nested field
```

### Case Conversion

Labels and tags are automatically converted based on configuration:

```yaml
kebabCaseLabelsAndTags: true  # default

# Input: accountCode
# Output: account-code

kebabCaseLabelsAndTags: false

# Input: accountCode
# Output: accountCode
```

### Name Length Limits

By default, `metadata.name` allows up to **253 characters**. This is suitable for most composed resources whose
names are not used for DNS resolution (e.g., AWS resources, Crossplane managed resources that are only addressed
by their external name).

For resources that **are** DNS-addressed (e.g., Kubernetes Services, Ingresses, or any resource whose
`metadata.name` is used as a DNS label), you should restrict the name length to 63 characters using the
`restrict-rfc1123-name-length` annotation or the `restrictRfc1123NameLength` global input.

**When to use the 63-character restriction:**

- Kubernetes **Services**: their name becomes part of the DNS record (`<name>.<namespace>.svc.cluster.local`).
- Kubernetes **Ingresses**: hostname derivation may depend on the resource name.
- Any resource where `metadata.name` is used as a **DNS label** (each label in a DNS name is limited to 63
  characters per [RFC 1123][]).
- Provider resources that enforce their own name length limits.

**Per-resource restriction (annotation):**

```yaml
metadata:
  annotations:
    function-naming-convention/restrict-rfc1123-name-length: "true"
  name: my-service
```

**Global restriction (function input):**

```yaml
spec:
  restrictRfc1123NameLength: true
```

The annotation takes precedence over the global input, so you can set it globally and override per-resource.

#### Name Too Long Behavior (Breaking Change)

By default, if a mutated name exceeds the maximum length (63 or 253 characters depending on configuration),
the function **fails with an error**. The error message includes the full mutated name, the resource reference,
the maximum allowed length, and the actual length.

Previous versions silently truncated (cropped) the name to fit the limit, which could cause hard-to-debug issues
like name collisions or unexpected resource identifiers.

To restore the previous truncation behavior, set `cropOnNameTooLong` globally or use the `crop-on-name-too-long`
annotation per resource:

**Global (function input):**

```yaml
spec:
  cropOnNameTooLong: true
```

**Per-resource (annotation):**

```yaml
metadata:
  annotations:
    function-naming-convention/crop-on-name-too-long: "true"
```

When cropping is enabled, the name is truncated to the maximum length and any trailing hyphens are stripped.

### RFC 1123 Compliance

All names and labels are automatically sanitized:

- Maximum **253 characters** for `metadata.name` (default) or **63 characters** when restricted.
- Maximum 253 characters for label prefixes.
- Only alphanumeric, hyphens, dots (for labels), and underscores (when not kebab-cased, which is made
  mandatory for Kubernetes resource names).
- Lowercase for `metadata.name`.
- Invalid characters replaced with hyphens.

### Tag Processing Order

Tags are applied in this order (later overrides earlier):

1. Tags from context field (via `tagsField`).
2. Static tags from function input (via `tags`).
3. Name tag (via `tag-name` annotation).
4. Labels as tags (via `labels-as-tags`).

## Reference Tables

### Function Input Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `annotations` | object | - | Configure annotation prefix and separator |
| `annotations.prefix` | string | `function-naming-convention` | Prefix for function annotations |
| `annotations.separator` | string | `/` | Separator between prefix and annotation key |
| `context` | string | `apiextensions.crossplane.io/environment` | Context key to read environment from |
| `cropOnNameTooLong` | boolean | `false` | Crop names that exceed the maximum length instead of failing |
| `envToLabel` | array[string] | `[]` | List of context fields to convert to labels |
| `kebabCaseLabelsAndTags` | boolean | `true` | Convert labels/tags to kebab-case |
| `labels` | object | - | Label configuration |
| `labels.labelsAsTags` | boolean | `false` | Copy labels to tags |
| `labels.prefix` | string | `""` | Prefix for generated labels |
| `labels.separator` | string | `/` | Separator between label prefix and key |
| `nameTemplateFields` | array[string] | `[]` | Ordered list of fields for name template |
| `responseTtl` | integer | `60` | Response cache TTL in seconds. Set to `0` to disable caching (no periodic reconciliation) |
| `restrictRfc1123NameLength` | boolean | `false` | Restrict `metadata.name` to 63 characters (DNS label limit) |
| `tags` | object | `{}` | Static tags to add to all resources |
| `tagsField` | string | `""` | Context field containing tags to inject |
| `tagsToField` | string | `""` | Write tags to custom field path instead of `spec.forProvider.tags` (dot notation) |
| `templateItemsSeparator` | string | `-` | Separator between name template items (only `-` or `.`) |
| `values` | object | `{}` | Static values to merge with context |
| `valuesFromMap` | array[object] | `[]` | Field value mappings |
| `valuesFromMap[].fallback` | string | `dflt` | Default value when no mapping found |
| `valuesFromMap[].from` | string | - | Source field path (dot notation) |
| `valuesFromMap[].map` | object | `{}` | Mapping of source values to output values |
| `valuesFromMap[].maxLength` | integer | `4` | Max length for unmapped values |
| `valuesFromMap[].to` | string | - | Target template field name |

### Resource Annotations

| Annotation | Type | Description |
|------------|------|-------------|
| `crop-on-name-too-long` | boolean | Crop names that exceed the maximum length instead of failing |
| `external-name` | boolean | Write mutated name to `crossplane.io/external-name` |
| `for-provider-name` | boolean | Write mutated name to `spec.forProvider.name` |
| `for-provider-name-field` | string | Custom path for provider name field (dot notation) |
| `for-provider-nameoverride` | boolean | Overwrite existing `forProvider.name` value |
| `init-provider-name` | boolean | Write mutated name to `spec.initProvider.name` |
| `init-provider-name-field` | string | Custom path for init provider name field (dot notation) |
| `init-provider-nameoverride` | boolean | Overwrite existing `initProvider.name` value |
| `labels-as-tags` | boolean | Copy labels to `spec.forProvider.tags` |
| `labels-to-field` | string | Copy labels to custom field (dot notation) |
| `name-fields-separator` | string | Override name template separator |
| `name-template` | string | Override name template (separator-separated fields) |
| `restrict-rfc1123-name-length` | boolean | Restrict `metadata.name` to 63 characters (DNS label limit) |
| `skip-name-modify` | boolean | Skip name modification for this resource |
| `tag-name` | boolean | Set `Name` tag to mutated name |
| `tags-field` | string | Context field to load tags from |
| `tags-to-field` | string | Write tags to custom field path instead of `spec.forProvider.tags` (dot notation) |
| `<custom-field>` | string | Override any template field value |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| Default maximum name length | 253 | Kubernetes object name limit |
| Restricted maximum name length | 63 | RFC 1123 DNS label limit |
| Maximum prefixed name length | 253 | RFC 1123 limit for label prefixes |
| Default annotation prefix | `function-naming-convention` | - |
| Default annotation separator | `/` | - |
| Default template separator | `-` | - |
| Default mapped value | `dflt` | Fallback for unmapped values |
| Default mapped value max length | 4 | Max length for unmapped values |

## Troubleshooting

### Name Not Being Modified

1. Check if this function is present in the composition pipeline.
2. Check if `skip-name-modify` annotation is set.
3. Verify `metadata.name` is not empty (empty names trigger auto-generation).
4. Check that all template fields exist in the context.

### Missing Labels

1. Verify fields are listed in `envToLabel`.
2. Check that fields exist in the context.
3. Ensure label keys are RFC 1123 compliant.

### Tags Not Applied

1. Verify resource has `spec.forProvider.tags` or `tagsToField`/`tags-to-field` is configured.
2. Check that `labels-as-tags` or `tag-name` is enabled.
3. Ensure the provider supports the tags field.

### Context Not Found Error

1. Verify the `context` field points to a valid context key.
2. Check that `EnvironmentConfig` or custom context is properly configured.
3. Ensure the context key exists in the composition.

### Template Field Missing Error

When a template field is not found in the context, the function will fail with an error to prevent
resource recreation due to name changes.
Ensure all template fields are present in your context or function values.

## See Also

- [Crossplane Composition Functions Documentation][functions]
- [EnvironmentConfigs Documentation][]
- [RFC 1123 DNS Label Names][]

<!-- Links -->
[EnvironmentConfigs Documentation]: https://docs.crossplane.io/latest/composition/environment-configs
[functions]: https://docs.crossplane.io/latest/composition/compositions/#how-composition-functions-work
[RFC 1123]: https://www.rfc-editor.org/rfc/rfc1123
[RFC 1123 DNS Label Names]: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-label-names
