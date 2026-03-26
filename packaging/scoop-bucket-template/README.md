# scoop-lore-book

Scoop bucket for lore-book.

## Add the bucket

```powershell
scoop bucket add cptplastic https://github.com/CptPlastic/scoop-lore-book
```

## Install lore-book

```powershell
scoop install lore-book
```

## Update the manifest

The primary manifest lives at `bucket/lore-book.json`.

This repository's source project generates an updated manifest during each release under `packaging/scoop/lore-book.json`.
Copy that file into this bucket repository and open a PR.
