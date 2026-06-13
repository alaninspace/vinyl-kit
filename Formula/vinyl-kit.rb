class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.14.0"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.14.0/vinylkit-macos-arm64.zip"
      sha256 "PLACEHOLDER_MAC_ARM64"
    else
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.14.0/vinylkit-macos-x86_64.zip"
      sha256 "PLACEHOLDER_MAC_X86_64"
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.14.0/vinylkit-linux-amd64.tar.gz"
    sha256 "PLACEHOLDER_LINUX_AMD64"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
