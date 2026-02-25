"""
Personal Cloud Mode for Regia.
Provides secure remote access via Tailscale or WireGuard,
enabling private cloud functionality where mobile/remote clients
connect to the Regia server over an encrypted mesh network.
"""

import logging
import shutil
import subprocess
import socket
import json
from typing import Optional, Dict, Any

logger = logging.getLogger("regia.cloud_mode")


class PersonalCloudManager:
    """Manages personal cloud mode settings and Tailscale/WireGuard integration."""

    def __init__(self):
        self._tailscale_ip: Optional[str] = None
        self._status: Optional[Dict] = None

    # === Tailscale Integration ===

    def is_tailscale_installed(self) -> bool:
        """Check if Tailscale CLI is available."""
        return shutil.which("tailscale") is not None

    def get_tailscale_status(self) -> Dict[str, Any]:
        """Get current Tailscale status."""
        if not self.is_tailscale_installed():
            return {"installed": False, "running": False, "ip": None}

        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return {"installed": True, "running": False, "ip": None, "error": result.stderr.strip()}

            data = json.loads(result.stdout)
            self_node = data.get("Self", {})
            ts_ips = self_node.get("TailscaleIPs", [])
            ip = ts_ips[0] if ts_ips else None

            peers = []
            for key, peer in data.get("Peer", {}).items():
                peers.append({
                    "hostname": peer.get("HostName", ""),
                    "ip": peer.get("TailscaleIPs", [None])[0],
                    "online": peer.get("Online", False),
                    "os": peer.get("OS", ""),
                })

            self._tailscale_ip = ip
            return {
                "installed": True,
                "running": True,
                "ip": ip,
                "hostname": self_node.get("HostName", ""),
                "dns_name": self_node.get("DNSName", ""),
                "tailnet": data.get("MagicDNSSuffix", ""),
                "peers": peers,
                "peer_count": len(peers),
            }
        except subprocess.TimeoutExpired:
            return {"installed": True, "running": False, "ip": None, "error": "Tailscale timed out"}
        except Exception as e:
            logger.error(f"Tailscale status check failed: {e}")
            return {"installed": True, "running": False, "ip": None, "error": str(e)}

    def get_tailscale_ip(self) -> Optional[str]:
        """Get the Tailscale IP address for this machine."""
        if self._tailscale_ip:
            return self._tailscale_ip

        try:
            result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                ip = result.stdout.strip()
                self._tailscale_ip = ip
                return ip
        except Exception:
            pass
        return None

    # === WireGuard Integration ===

    def is_wireguard_installed(self) -> bool:
        """Check if WireGuard CLI (wg) is available."""
        return shutil.which("wg") is not None

    def get_wireguard_status(self) -> Dict[str, Any]:
        """Get current WireGuard status."""
        if not self.is_wireguard_installed():
            return {"installed": False, "running": False, "interfaces": []}

        try:
            result = subprocess.run(
                ["wg", "show", "all", "dump"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return {"installed": True, "running": False, "interfaces": [],
                        "error": "WireGuard not active or requires elevated permissions"}

            interfaces = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 4:
                    interfaces.append({
                        "interface": parts[0],
                        "public_key": parts[1][:16] + "...",
                    })

            return {
                "installed": True,
                "running": len(interfaces) > 0,
                "interfaces": interfaces,
            }
        except Exception as e:
            logger.error(f"WireGuard status check failed: {e}")
            return {"installed": True, "running": False, "interfaces": [], "error": str(e)}

    # === General Network Info ===

    def get_lan_ip(self) -> str:
        """Get the machine's LAN IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_cloud_info(self, port: int = 8420) -> Dict[str, Any]:
        """Get comprehensive cloud access info."""
        lan_ip = self.get_lan_ip()
        ts_status = self.get_tailscale_status() if self.is_tailscale_installed() else None
        wg_status = self.get_wireguard_status() if self.is_wireguard_installed() else None

        info = {
            "lan": {
                "ip": lan_ip,
                "url": f"http://{lan_ip}:{port}",
                "accessible": True,
            },
            "tailscale": None,
            "wireguard": None,
            "recommended_url": f"http://{lan_ip}:{port}",
        }

        if ts_status and ts_status.get("running") and ts_status.get("ip"):
            ts_ip = ts_status["ip"]
            info["tailscale"] = {
                "ip": ts_ip,
                "url": f"http://{ts_ip}:{port}",
                "hostname": ts_status.get("hostname", ""),
                "dns_name": ts_status.get("dns_name", ""),
                "tailnet": ts_status.get("tailnet", ""),
                "peers": ts_status.get("peers", []),
            }
            # Prefer Tailscale URL for remote access
            info["recommended_url"] = f"http://{ts_ip}:{port}"
            dns = ts_status.get("dns_name", "")
            if dns:
                info["recommended_url"] = f"http://{dns.rstrip('.')}:{port}"

        if wg_status and wg_status.get("running"):
            info["wireguard"] = {
                "active": True,
                "interfaces": wg_status.get("interfaces", []),
            }

        return info
