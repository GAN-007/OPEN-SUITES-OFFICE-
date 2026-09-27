# Separately Licensed Components

Nexus vendors every audited source tree that its upstream license permits this public repository to redistribute.

## GenOffice `ee/`

The pinned GenOffice repository contains `ee/` under the **GenOffice Enterprise License** rather than Apache-2.0. The license states that development/testing copying and modification are permitted, while production use, hosted/managed offering, or redistribution requires a valid enterprise agreement with Mainfunc, Inc.

Therefore:

- `engines/genoffice/ee/` is excluded from the public vendored snapshot.
- the path is git-ignored;
- Nexus does not relabel it as Apache-2.0;
- users who have read and can comply with the separate terms may create a local overlay with:

```bash
git submodule update --init upstream/genoffice
python scripts/install_restricted.py --engine genoffice --acknowledge-license
```

The overlay is local and is not committed by Nexus.

## Open WebUI

Open WebUI source is permitted to be redistributed subject to its own license. The vendored copy retains the upstream license and branding. Nexus does not remove, obscure or replace Open WebUI branding in the vendored module.
