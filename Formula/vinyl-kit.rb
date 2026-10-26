class VinylKit < Formula
  desc "Manage digitized vinyl record audio files using Discogs metadata"
  homepage "https://vinylkit.app"
  version "0.16.5"

  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.16.5/vinylkit-macos-arm64.zip"
      sha256 "4a03a5e7b3d5637882af2dbb47355fd92fe04b50993d9005d11ff68d00529b87"
    else
      odie "Intel Macs are no longer supported via standalone binary. Please install using `uv tool install vinylkit` instead."
    end
  elsif OS.linux?
    url "https://github.com/alaninspace/vinyl-kit/releases/download/v0.16.5/vinylkit-linux-amd64.tar.gz"
    sha256 "30810b076b8cb5c242e1c6b45227da6b4b227c9e402396f2ca4ee41993ddf9f6"
  end

  def install
    bin.install "vinylkit"
  end

  test do
    system "#{bin}/vinylkit", "--version"
  end
end
