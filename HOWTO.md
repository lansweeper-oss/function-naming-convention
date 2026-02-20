# HOWTO

## Global (all resources affected)

- Specify format for the naming convention:

  ```yaml
  - step: enforce-naming-convention
    functionRef:
      name: function-naming-convention
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        nameTemplateFields:
        - namePrefix
        - domain
        - fixed
        values:
          fixed: foo
  ```

- Copy keys from context to labels and optionally (when part of a resource spec) tags, while adding
  an optional prefix `ac/` to them:

  ```yaml
  - step: enforce-naming-convention
    functionRef:
      name: function-naming-convention
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        context: custom-context/foo  # defaults to apiextensions.crossplane.io/environment
        envToLabel:
        - account
        - accountCode
        - region
        - regionCode
        - tenant
        labels:
          prefix: ac
        labels-as-tags: true
  ```

- Use a different prefix for the annotations (those read by the function to override per-resource,
  then drop when finished). For example to use annotations starting by `fn.naming-`, do:

  ```yaml
  - step: enforce-naming-convention
    functionRef:
      name: function-naming-convention
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        annotations:
          prefix: fn.naming
          separator: "-"
  ```

- Use a different prefix for the labels/tags (bear in mind they must be RFC1123 compliant).
  For example to use annotations starting by `fn-naming/`, do:

  ```yaml
  - step: enforce-naming-convention
    functionRef:
      name: function-naming-convention
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        annotations:
          prefix: fn-naming
          # separator: "/"  # default, no need to specify
  ```

- Transform input values from a map, e.g. to take a shortened version of a resource's `kind`:

  ```yaml
  - step: enforce-naming-convention
    functionRef:
      name: function-naming-convention
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        nameTemplateFields:
        - namePrefix  # from context
        - kindCode    # from resource mapping
        valuesFromMap:
        - from: kind
          to: kindCode
          map:
            Bucket: s3
            Certificate: cert
            Cluster: clus
            EBSVolume: ebs
            InternetGateway: igw
            NATGateway: nat
            OpenIdConnectProvider: oidc
            Policy: plcy
            Record: rec
            RouteTable: rtb
            SecurityGroup: sg
            SecurityGroupRule: sgr
            TransitGateway: tgw
            VPCEndpoint: vpce
  ```

## Overrides (per resource)

- Omit name modification for a given resource:

  ```yaml
  metadata:
    annotations:
      function-naming-convention/skip-name-modify: "true"
  ```

- Copy mutated `metadata.name` to `crossplane.io/external-name` annotation:

  ```yaml
  metadata:
    annotations:
      function-naming-convention/external-name: "true"
  ```

- Copy mutated `metadata.name` to `spec.forProvider.name` field:

  ```yaml
  metadata:
    annotations:
      function-naming-convention/for-provider-name: "true"
  ```

- Copy mutated `metadata.name` to an arbitrary field under `spec.forProvider`
  (e.g. `spec.forProvider.clusterName`):

  ```yaml
  metadata:
    annotations:
      function-naming-convention/for-provider-name-field: clusterName
  ```

- Enable/disable copying the labels as tags:
  - When globally enable, to disable for a given resource:

    ```yaml
    [...]
    input:
      apiVersion: naming-convention.fn.crossplane.com/v1alpha1
      kind: Input
      spec:
        labels-as-tags: true
    [...]
    ```

  - When not globally enabled, to have tags for a given resource do:

    ```yaml
    metadata:
      annotations:
        function-naming-convention/labels-as-tags: false
    ```

- Set `tag.Name` from mutated `metadata.name`:

  ```yaml
  metadata:
    annotations:
      function-naming-convention/tag-name: true
  ```

- To override the current value for `forProvider.name` with the mutated `metadata.name` do:

  ```yaml
  metadata:
    annotations:
      function-naming-convention/for-provider-nameoverride: true
  ```

- To override how the context/parameters fields form the mutated name, set the per-resource template
  with (f-string format):

  ```yaml
  metadata:
    annotations:
      function-naming-convention/name-template: "prefix-{domain}-{component}"
      function-naming-convention/name-fields-separator: "--"
  ```

  > This will take the context (or EnvironmentConfig) values for `domain` (e.g. `foo`) and `component`
  (e.g. `bar`) and produce `prefix-foo-bar--baz` for a resource with `metadata.name`: `baz`.

- Replicate labels to an arbitrary field:

  ```yaml
   metadata:
    annotations:
      function-naming-convention/labels-to-field: spec.customTags
  ```

- Override a given template field:

  - Given this input:

    ```yaml
    - step: enforce-naming-convention
      functionRef:
        name: function-naming-convention
      input:
        apiVersion: naming-convention.fn.crossplane.com/v1alpha1
        kind: Input
        spec:
          nameTemplateFields:
          - namePrefix
          - domain
          - override-me
          values:
            override-me: foo
    ```

  - And this context (`EnvironmentConfig`):

    ```yaml
    data:
      namePrefix: this
      domain: is
      override-me: bar
    ```

  - The result of mutating a resource whose initial name is "baz" would be `this-is-foo-baz`.
  - If we add the following annotation to the resource:

    ```yaml
    metadata:
      annotations:
        function-naming-convention/override-me: qux
    ```

  - Then the result of mutating that resource would be `this-is-foo-qux` instead, while any other
  resources would be prefixed by `this-is-foo`.
