class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.14.3"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.14.3/vinylkit-macos-arm64.zip"
      sha256 "12fc28a7e3dd4572e39a6c33a560c9af0327a26f069fa9ade11b177950a6fa43"
    else
      odie "Intel Macs are no longer supported via standalone binary. Please install using `uv tool install vinylkit` instead."
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.14.3/vinylkit-linux-amd64.tar.gz"
    sha256 "d5cf991b08d7217a60d49c69d1fe5433a648b54876e734a301c90eb9840914cc"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
