#! /bin/bash
# pycares-5.0.1 fails to build due to c-ares on macOS 27.x.
# pyobjc-core fails due to -Werror,-Wdefault-const-init-var-unsafe
brew install -q c-ares
export CFLAGS="-I$(brew --prefix c-ares)/include -Wno-error=default-const-init-var-unsafe"
export LDFLAGS="-L$(brew --prefix c-ares)/lib"
export PYCARES_USE_SYSTEM_LIB=1

uv python pin  $(cat .python-version)
uv cache clean
uv sync
