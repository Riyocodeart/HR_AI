"""
features
========
Feature planning + dictionary for the ranking engine. Currently contains:

* ``feature_dictionary`` — single source of truth for every feature used by
  the scorer (name, source field, type, normalisation, direction).

Future modules in this package:
* ``feature_extractor`` — pulls values out of CandidateObject + JD
* ``feature_normalizer`` — applies the per-feature normalisation method
"""