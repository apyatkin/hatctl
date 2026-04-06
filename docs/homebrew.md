# Installing hat via Homebrew

Currently, hat is installed via uv/pip:

```bash
uv tool install hatctl
```

A Homebrew formula is planned. For now, you can create a local tap:

```bash
# Create local tap
mkdir -p $(brew --repository)/Library/Taps/hatctl/homebrew-tap/Formula

# Create formula
cat > $(brew --repository)/Library/Taps/hatctl/homebrew-tap/Formula/hatctl.rb << 'EOF'
class Hatctl < Formula
  desc "Put on your company hat"
  homepage "https://github.com/apyatkin/personal-tools"
  url "https://github.com/apyatkin/personal-tools/archive/refs/tags/v2.1.0.tar.gz"
  license "MIT"

  depends_on "python@3.11"
  depends_on "uv"

  def install
    system "uv", "tool", "install", ".", "--python", Formula["python@3.11"].bin/"python3.11"
    bin.install_symlink Dir["#{HOMEBREW_PREFIX}/bin/hat"]
  end

  test do
    assert_match "version", shell_output("#{bin}/hat --version")
  end
end
EOF

# Install
brew install hatctl/tap/hatctl
```

This is a workaround until the package is submitted to Homebrew Core.
