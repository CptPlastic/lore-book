# Setting Up a Homebrew Tap for lore-book

## Quick Start

A Homebrew tap is a custom repository containing Homebrew formulas. To make lore-book installable via Homebrew, follow these steps:

### Step 1: Create a separate tap repository

Create a new GitHub repository named `homebrew-lore` with this structure:

```
homebrew-lore/
├── Formula/
│   └── lore.rb
├── README.md
└── .github/workflows/
    └── tests.yml
```

### Step 2: Add the formula file

Copy the `Formula/lore.rb` from this repository to your new tap repository.

### Step 3: Before publishing, update the SHA256

The formula contains a placeholder SHA256. Once your package is published to PyPI, get the correct SHA256:

```bash
# After publishing lore-book to PyPI
python3 -c "import urllib.request, hashlib; data = urllib.request.urlopen('https://files.pythonhosted.org/packages/source/l/lore-book/lore-book-0.1.0.tar.gz').read(); print(hashlib.sha256(data).hexdigest())"
```

Update the `sha256` value in `Formula/lore.rb`.

### Step 4: Add a README

Create a `README.md` in the tap repository:

```markdown
# homebrew-lore

Homebrew tap for lore-book.

## Installation

```bash
brew tap cptplastic/lore
brew install lore
```

## Usage

```bash
lore --help
```
```

### Step 5: Publish to PyPI

Make sure lore-book is published to PyPI first:

```bash
# From lore-book directory
pip install build
python -m build
twine upload dist/*
```

## Users can then install with:

```bash
brew tap cptplastic/lore https://github.com/cptplastic/homebrew-lore
brew install lore
```

Or more simply (if tap is public):

```bash
brew install cptplastic/lore/lore
```

## Optional: Automate with GitHub Actions

Create `.github/workflows/tests.yml` in your tap repo:

```yaml
name: Homebrew Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test formula
        run: |
          brew install --verbose --build-from-source --HEAD ./Formula/lore.rb
          brew test lore
          brew audit --formula lore.rb
```

## References

- [Homebrew Tap Documentation](https://docs.brew.sh/Taps)
- [Creating a Homebrew Formula](https://docs.brew.sh/Formula-Cookbook)
