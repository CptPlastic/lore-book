class Lore < Formula
  desc "The spellbook for your codebase — chronicle decisions, lore, and context your AI companions can actually read"
  homepage "https://github.com/cptplastic/lore-book"
  url "https://files.pythonhosted.org/packages/source/l/lore-book/lore-book-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "FSL-1.1-MIT"

  depends_on "python@3.10"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"lore", "--version"
  end
end
