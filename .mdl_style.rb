# markdownlint config
# see https://github.com/markdownlint/markdownlint/tree/main
all

exclude_rule 'MD014'
# headers and footers may add top level headers
exclude_rule 'MD025'
# regexes breaking the rule in tables
exclude_rule 'MD056'

# unordered list indentation 2 spaces
rule 'MD007', :indent => 2
# increase line length
rule 'MD013', :line_length => 120, :ignore_code_blocks => true, :tables => false
# allow ordered lists
rule 'MD029', :style => 'ordered'
# allow duplicate headers titles only in different nestings
rule 'MD024', :allow_different_nesting => true
# required for ad-hoc links in markdown sections since github markdown does not support
# [heading ids](https://www.markdownguide.org/extended-syntax/#heading-ids)
rule 'MD033', :allowed_elements => 'a,br'
