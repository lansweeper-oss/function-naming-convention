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
6. Apply to `metadata.name`, `external-name` annotation, `forProvider.name` (or any other field as configured),
  labels and tags.

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

#### Complete Global Configuration Example

```yaml
- step: enforce-naming-convention
  functionRef:
    name: function-naming-convention
  input:
    apiVersion: naming-convention.fn.crossplane.com/v1alpha1
    kind: Input
    spec:
      context: apiextensions.crossplane.io/environment

      nameTemplateFields:
        - tenant
        - accountCode
        - regionCode
        - kindCode

      templateItemsSeparator: "-"

      envToLabel:
        - tenant
        - account
        - region

      labels:
        prefix: company
        separator: "/"
        labelsAsTags: true

      kebabCaseLabelsAndTags: true

      tags:
        ManagedBy: crossplane
        Environment: production

      tagsField: defaultTags

      values:
        staticField: value

      valuesFromMap:
        - from: kind
          to: kindCode
          maxLength: 4
          fallback: res
          map:
            Bucket: s3
            SecurityGroup: sg
            VPC: vpc
```

### Per-Resource Configuration (Annotations)

Per-resource configuration uses annotations to override global settings or enable specific behaviors for individual
resources.
All annotations use the prefix `function-naming-convention/` by default (configurable globally).

**Note:** Function-specific annotations are automatically removed from resources after processing.

#### Skip Name Modification

Preserve the original resource name:

```yaml
metadata:
  annotations:
    function-naming-convention/skip-name-modify: "true"
  name: my-custom-name  # Will not be modified
```

#### External Name Annotation

Copy the mutated name to the external-name annotation (if not already present):

```yaml
metadata:
  annotations:
    function-naming-convention/external-name: "true"
```

**Result:**

```yaml
metadata:
  annotations:
    crossplane.io/external-name: acme-prod-us1-s3-my-bucket
  name: acme-prod-us1-s3-my-bucket
```

#### ForProvider Name Field

Write the mutated name to `spec.forProvider.name`:

```yaml
metadata:
  annotations:
    function-naming-convention/for-provider-name: "true"
```

**Result:**

```yaml
metadata:
  name: acme-prod-us1-s3-my-bucket
spec:
  forProvider:
    name: acme-prod-us1-s3-my-bucket
```

#### Custom ForProvider Name Field

Write to a different field under `spec.forProvider`:

```yaml
metadata:
  annotations:
    function-naming-convention/for-provider-name: "true"
    function-naming-convention/for-provider-name-field: clusterName
```

**Result:**

```yaml
spec:
  forProvider:
    clusterName: acme-prod-us1-eks-cluster
```

Supports dot notation for nested fields:

```yaml
metadata:
  annotations:
    function-naming-convention/for-provider-name: "true"
    function-naming-convention/for-provider-name-field: config.clusterName
```

**Result:**

```yaml
spec:
  forProvider:
    config:
      clusterName: acme-prod-us1-eks-cluster
```

#### ForProvider Name Override

Force overwrite existing `spec.forProvider.name` value:

```yaml
metadata:
  annotations:
    function-naming-convention/for-provider-name: "true"
    function-naming-convention/for-provider-nameoverride: "true"
```

Without `nameoverride`, the function will apply the naming convention to the existing value.
With `nameoverride`, it replaces it entirely.

#### Name Tag

Set the `Name` tag in `spec.forProvider.tags`:

```yaml
metadata:
  annotations:
    function-naming-convention/tag-name: "true"
```

**Result:**

```yaml
spec:
  forProvider:
    tags:
      Name: acme-prod-us1-s3-my-bucket
```

#### Labels as Tags

Copy generated labels to tags (override global setting):

```yaml
# Enable for specific resource (when globally disabled)
metadata:
  annotations:
    function-naming-convention/labels-as-tags: "true"

# Disable for specific resource (when globally enabled)
metadata:
  annotations:
    function-naming-convention/labels-as-tags: "false"
```

#### Replicate Labels to Custom Field

Copy all labels to an arbitrary field:

```yaml
metadata:
  annotations:
    function-naming-convention/labels-to-field: spec.forProvider.customTags
```

**Result:**

```yaml
spec:
  forProvider:
    customTags:
      company/tenant: acme
      company/region: us-east-1
```

#### Override Name Template

Use a different naming template for a specific resource:

```yaml
metadata:
  annotations:
    function-naming-convention/name-template: "tenant,environment,component"
    function-naming-convention/name-fields-separator: "."
  name: api
```

The `name-template` annotation accepts a comma-separated (or any other separator, if configured) list of field names.

**Result:**

- Context: `{tenant: "acme", environment: "prod", component: "web"}`.
- Generated name: `acme.prod.web.api`.

#### Override Template Field Values

Override specific template field values:

```yaml
metadata:
  annotations:
    function-naming-convention/domain: "custom-domain"
    function-naming-convention/component: "special"
  name: resource
```

When the global template is `[tenant, accountCode, domain, component]`:

- Normal resources: `tenant-accountCode-default-standard-resourceName`.
- This resource: `tenant-accountCode-custom-domain-special-resource`.

**Important:** Both camelCase and kebab-case work: `function-naming-convention/customField` is equivalent to `function-naming-convention/custom-field`.

#### Tags from Context Field

Load tags from a specific context field:

```yaml

metadata:
  annotations:
    function-naming-convention/tags-field: environmentTags
```

If the context contains:

```yaml
environmentTags:
  Owner: platform-team
  Project: infrastructure
```

**Result:**

```yaml
spec:
  forProvider:
    tags:
      Owner: platform-team
      Project: infrastructure
```

## Complete Examples

### Example 1: Basic S3 Bucket

**Global Configuration:**

```yaml
- step: enforce-naming-convention
  functionRef:
    name: function-naming-convention
  input:
    apiVersion: naming-convention.fn.crossplane.com/v1alpha1
    kind: Input
    spec:
      nameTemplateFields:
        - tenant
        - environment
        - regionCode

      envToLabel:
        - tenant
        - environment
```

**Context (EnvironmentConfig):**

```yaml
data:
  tenant: acme
  environment: prod
  regionCode: use1
```

**Resource:**

```yaml
apiVersion: s3.aws.upbound.io/v1beta1
kind: Bucket
metadata:
  annotations:
    function-naming-convention/external-name: "true"
    function-naming-convention/tag-name: "true"
  name: data
spec:
  forProvider:
    region: us-east-1
```

**Result:**

```yaml
apiVersion: s3.aws.upbound.io/v1beta1
kind: Bucket
metadata:
  annotations:
    crossplane.io/external-name: acme-prod-use1-data
  labels:
    tenant: acme
    environment: prod
  name: acme-prod-use1-data
spec:
  forProvider:
    region: us-east-1
    tags:
      Name: acme-prod-use1-data
```

### Example 2: EKS Cluster with Custom Field

**Global Configuration:**

```yaml
- step: enforce-naming-convention
  functionRef:
    name: function-naming-convention
  input:
    apiVersion: naming-convention.fn.crossplane.com/v1alpha1
    kind: Input
    spec:
      nameTemplateFields:
        - tenant
        - environment
        - kindCode

      valuesFromMap:
        - from: kind
          to: kindCode
          map:
            Cluster: eks

      labels:
        prefix: company
        labelsAsTags: true

      envToLabel:
        - tenant
        - environment
        - region
```

**Context:**

```yaml
data:
  tenant: acme
  environment: staging
  region: us-west-2
```

**Resource:**

```yaml
apiVersion: eks.aws.upbound.io/v1beta1
kind: Cluster
metadata:
  annotations:
    function-naming-convention/for-provider-name: "true"
    function-naming-convention/for-provider-name-field: name
    function-naming-convention/external-name: "true"
    function-naming-convention/tag-name: "true"
  name: primary
spec:
  forProvider:
    region: us-west-2
    roleArnSelector:
      matchLabels:
        role: eks
```

**Result:**

```yaml
apiVersion: eks.aws.upbound.io/v1beta1
kind: Cluster
metadata:
  annotations:
    crossplane.io/external-name: acme-staging-eks-primary
  labels:
    company/tenant: acme
    company/environment: staging
    company/region: us-west-2
  name: acme-staging-eks-primary
spec:
  forProvider:
    name: acme-staging-eks-primary
    region: us-west-2
    roleArnSelector:
      matchLabels:
        role: eks
    tags:
      Name: acme-staging-eks-primary
      company/tenant: acme
      company/environment: staging
      company/region: us-west-2
```

### Example 3: VPC with Custom Template

**Global Configuration:**

```yaml
- step: enforce-naming-convention
  functionRef:
    name: function-naming-convention
  input:
    apiVersion: naming-convention.fn.crossplane.com/v1alpha1
    kind: Input
    spec:
      nameTemplateFields:
        - tenant
        - environment

      tags:
        ManagedBy: crossplane
```

**Context:**

```yaml
data:
  tenant: acme
  environment: dev
```

**Resource (uses custom template):**

```yaml
apiVersion: ec2.aws.upbound.io/v1beta1
kind: VPC
metadata:
  annotations:
    function-naming-convention/name-template: "tenant,custom-field"
    function-naming-convention/name-fields-separator: "_"
    function-naming-convention/custom-field: "networking"
    function-naming-convention/external-name: "true"
    function-naming-convention/for-provider-name: "true"
    function-naming-convention/tag-name: "true"
  name: main
spec:
  forProvider:
    cidrBlock: 10.0.0.0/16
    region: us-east-1
```

**Result:**

```yaml
apiVersion: ec2.aws.upbound.io/v1beta1
kind: VPC
metadata:
  annotations:
    crossplane.io/external-name: acme_networking_main
  name: acme-networking-main
spec:
  forProvider:
    name: acme_networking_main
    cidrBlock: 10.0.0.0/16
    region: us-east-1
    tags:
      Name: acme_networking_main
      ManagedBy: crossplane
```

### Example 4: Resource with Skip Modification

**Resource:**

```yaml
apiVersion: ec2.aws.upbound.io/v1beta1
kind: SecurityGroup
metadata:
  annotations:
    function-naming-convention/skip-name-modify: "true"
  name: legacy-sg-do-not-change
spec:
  forProvider:
    description: Legacy security group
    region: us-east-1
```

**Result:**

```yaml
apiVersion: ec2.aws.upbound.io/v1beta1
kind: SecurityGroup
metadata:
  labels:
    # Labels still added based on global config
    tenant: acme
    environment: prod
  name: legacy-sg-do-not-change  # Name unchanged
spec:
  forProvider:
    description: Legacy security group
    region: us-east-1
```

## Advanced Features

### Dot Notation for Nested Fields

Both `valuesFromMap.from` and `for-provider-name-field` support dot notation:

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

### RFC 1123 Compliance

All names and labels are automatically sanitized to RFC 1123 compliance:

- Maximum 63 characters for names.
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
| `envToLabel` | array[string] | `[]` | List of context fields to convert to labels |
| `kebabCaseLabelsAndTags` | boolean | `true` | Convert labels/tags to kebab-case |
| `labels` | object | - | Label configuration |
| `labels.labelsAsTags` | boolean | `false` | Copy labels to tags |
| `labels.prefix` | string | **required** | Prefix for generated labels |
| `labels.separator` | string | `/` | Separator between label prefix and key |
| `nameTemplateFields` | array[string] | `[]` | Ordered list of fields for name template |
| `tags` | object | `{}` | Static tags to add to all resources |
| `tagsField` | string | `""` | Context field containing tags to inject |
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
| `external-name` | boolean | Write mutated name to `crossplane.io/external-name` |
| `for-provider-name` | boolean | Write mutated name to `spec.forProvider.name` |
| `for-provider-name-field` | string | Custom path for provider name field (dot notation) |
| `for-provider-nameoverride` | boolean | Overwrite existing `forProvider.name` value |
| `labels-as-tags` | boolean | Copy labels to `spec.forProvider.tags` |
| `labels-to-field` | string | Copy labels to custom field (dot notation) |
| `name-fields-separator` | string | Override name template separator |
| `name-template` | string | Override name template (comma-separated fields) |
| `skip-name-modify` | boolean | Skip name modification for this resource |
| `tag-name` | boolean | Set `Name` tag to mutated name |
| `tags-field` | string | Context field to load tags from |
| `<custom-field>` | string | Override any template field value |

All annotations accept `"true"`, `"yes"`, `"on"`, `"y"` for boolean true values (case-insensitive).

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| Maximum name length | 63 | RFC 1123 limit |
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

1. Verify resource supports `spec.forProvider.tags`.
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
