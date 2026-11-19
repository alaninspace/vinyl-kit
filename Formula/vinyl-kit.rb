class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.18.0"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.18.0/vinylkit-macos-arm64.zip"
      sha256 "f52b5da16d1d5a3d60f11556faf900280615f317f18edc7def363617c6eca0b6"
    else
      odie "Intel Macs are no longer supported via standalone binary. Please install using `uv tool install vinylkit` instead."
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.18.0/vinylkit-linux-amd64.tar.gz"
    sha256 "bffb8a1666e05bf611a56bf21bd3922d05cfe228f866f2f2c9a04593b7e4d92a"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
