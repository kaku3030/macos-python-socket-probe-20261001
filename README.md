# Generic macOS Python socket probe

This repository is a standalone diagnostic for local Python socket and HTTPServer behavior on a macOS GitHub-hosted runner.

It uses only the Python standard library, performs no external network access, reads no environment secrets, and does not reference any application or provider. Each probe step runs in its own child process with a 15-second watchdog.

Steps: raw IPv4 bind, `TCPServer.server_bind`, `socket.getfqdn`, `HTTPServer.server_bind`, plus local `getaddrinfo` and `gethostbyaddr` helpers.
