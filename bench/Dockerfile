# DEVELOPED BY CARROTSTUDIO software house
# The bench's Campanile: Debian 13, the base of Raspberry Pi OS Trixie, with the same Python
# 3.13 and nginx a Raspberry Pi gets, plus the tools that shape and measure the links.
FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 nginx iproute2 ethtool iputils-ping curl procps ca-certificates \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default
