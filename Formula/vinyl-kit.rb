class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.17.1"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.17.1/vinylkit-macos-arm64.zip"
      sha256 "d0466a279ed1567c977e0060101f038d4c472a18fa43afa3e58451a601ca6faa"
    else
      odie "Intel Macs are no longer supported via standalone binary. Please install using `uv tool install vinylkit` instead."
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.17.1/vinylkit-linux-amd64.tar.gz"
    sha256 "124ccc869505431a0c9aabaf18fa10fc6b65a840fd2d1689054a1aa5650c5369"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
