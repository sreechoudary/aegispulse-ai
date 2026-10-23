AegisPulse AI
Copyright 2026 M Sreenivasarao

This product is licensed under the Apache License, Version 2.0 (see the LICENSE file).

This NOTICE file provides attribution for third-party software and models used by
AegisPulse AI. License identifiers were verified on 2026-10-18 from (a) the installed
Python package metadata, (b) the frontend package-lock.json / node_modules metadata, and
(c) the upstream project README for the Strands Decider model. No third-party source code,
model weights, fonts, icons, or binary assets are vendored into this repository; all
dependencies are fetched from their package registries, and the Strands Decider model
weights are downloaded at runtime into the local Hugging Face cache (outside this repo).

================================================================================
Models
================================================================================

Strands Decider 2B
  Model id: StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 (Hugging Face; also mirrored
  under the "amazon/" organization). Base torso: Qwen3.5-2B-Base.
  License: Apache License 2.0 (per the strands-labs/strands-decider repository, which states
  it is licensed under the Apache License 2.0, and per the installed strands-decider package
  metadata: License-Expression Apache-2.0).
  Usage: downloaded and run locally for inference; weights are NOT redistributed by this
  project. Retain this attribution when redistributing.

Amazon Bedrock (amazon.nova-lite-v1:0)
  Accessed as a hosted AWS service via the AWS SDK (boto3). Used under the applicable AWS
  Service Terms. No model weights are included or redistributed by this project.

================================================================================
Python dependencies (versions as installed and tested)
================================================================================

The following are direct dependencies. License identifiers are taken from each package's
installed metadata (importlib.metadata).

  strands-decider  0.1.0      Apache-2.0
  strands-agents   1.61.1     Apache-2.0
  boto3            1.43.114   Apache-2.0
  fastapi          0.143.3    MIT
  pydantic         2.14.1     MIT
  sqlmodel         0.0.48     MIT
  transformers     5.20.1     Apache-2.0
  torch            2.14.1     BSD-3-Clause (PyTorch is distributed under a BSD-3-Clause
                              license; its metadata also lists bundled components under
                              Apache-2.0, Apache-2.0-with-LLVM-exception, BSD-2-Clause,
                              BSL-1.0, and MIT. See the PyTorch LICENSE for the authoritative
                              terms before redistributing.)
  hypothesis       6.170.1    MPL-2.0  (used ONLY as a development/test dependency; it is not
                              imported by, linked into, or redistributed with the shipped
                              application. MPL-2.0 is a file-level (weak) copyleft: if you
                              modify and distribute Hypothesis's own source files, those
                              files must remain under MPL-2.0. Using it as an unmodified test
                              tool imposes no copyleft obligation on AegisPulse AI's code.)

Retain the upstream copyright and license notices for each package when redistributing it.
This file does not reproduce each package's full license text; obtain those from the
respective packages (e.g. node_modules/<pkg>/LICENSE and site-packages/<pkg>/*).

================================================================================
Frontend dependencies (from package-lock.json / installed node_modules)
================================================================================

Direct dev/runtime dependencies: react, react-dom (MIT); vite, @vitejs/plugin-react (MIT);
typescript (Apache-2.0); tailwindcss, autoprefixer, postcss (MIT); vitest,
@testing-library/react, jsdom (MIT).

Transitive license tally across 237 installed packages (from node_modules metadata):
  MIT 210, ISC 14, Apache-2.0 7, BSD-2-Clause 2, BSD-3-Clause 2, MIT-0 1, CC-BY-4.0 1.
No GPL/LGPL/AGPL/MPL packages are present in the frontend tree.

  caniuse-lite (CC-BY-4.0): browser-compatibility DATA pulled in transitively by
  autoprefixer/browserslist. CC-BY-4.0 requires attribution. It is build-time data and is
  not emitted into the production bundle, but it is attributed here. Source and license:
  https://github.com/browserslist/caniuse-lite (data derived from caniuse.com, CC-BY-4.0).

Note: a license scan also surfaces a handful of internal TEST FIXTURE packages (e.g. "baz",
"browser_field", "false_main", "invalid_main", and unnamed entries) nested inside some
dependencies' test directories. These are intentionally malformed test data with no license
field; they are not real dependencies and are not distributed by this project.

================================================================================
Disclaimer
================================================================================

This is an attribution summary compiled from automated metadata, not legal advice. A final
human license review is recommended before public release, in particular: the full PyTorch
license terms, confirmation that Hypothesis remains a test-only dependency, and the
caniuse-lite CC-BY-4.0 attribution above.
