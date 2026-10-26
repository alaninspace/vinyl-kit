class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.16.5"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.16.5/vinylkit-macos-arm64.zip"
      sha256 "519fd36c00a75b60f1e713b802b49d8d816b6122465a8faadc8ac4c98452c0ea"
    else
      odie "Intel Macs are no longer supported via standalone binary. Please install using `uv tool install vinylkit` instead."
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.16.5/vinylkit-linux-amd64.tar.gz"
    sha256 "bcbee0e5432523527aa0da80b5d74d7e1d8a4bc6090f83df84f7c1e39e20b728"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
