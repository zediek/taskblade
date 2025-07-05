from concurrent.futures import ThreadPoolExecutor
import ipaddress
import re
import socket
import subprocess
import sys


class PortScan:
    def is_local_ip(self, ip):
        try:
            return ipaddress.ip_address(ip).is_private
        except ValueError:
            return False

    def get_hostname(self, ip):
        if not self.is_local_ip(ip):
            return None
        try:
            res = socket.gethostbyaddr(ip)
            return res[0]
        except socket.herror:
            return None

    def get_mac(self, ip):
        if not self.is_local_ip(ip):
            return None
        try:
            subprocess.run(['ping', '-n', '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=2)
            for line in result.stdout.splitlines():
                if ip in line:
                    parts = line.split()
                    for p in parts:
                        if '-' in p or ':' in p:
                            return p
        except Exception as e:
            print(f"MAC error for {ip}: {e}")
        return None

    def scan_host(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=0.5):
                return port
        except:
            return None

    def generate_dns_range(self, start, end):
        match1 = re.match(r'([a-zA-Z\-]+?)(\d+)\.(.+)', start)
        match2 = re.match(r'([a-zA-Z\-]+?)(\d+)\.(.+)', end)
        if not match1 or not match2:
            raise ValueError("Invalid DNS hostname range format.")
        prefix1, num1, domain1 = match1.groups()
        prefix2, num2, domain2 = match2.groups()
        if prefix1 != prefix2 or domain1 != domain2:
            raise ValueError("Start and end hostnames must share prefix and domain.")
        num1, num2 = int(num1), int(num2)
        return [f"{prefix1}{i}.{domain1}" for i in range(num1, num2 + 1)]

    def resolve_to_ip(self, hostname):
        try:
            return socket.gethostbyname(hostname)
        except socket.error:
            return None

    def expand_targets(self, host_input):
        host_input = host_input.strip()
        targets = []
        if '/' in host_input:
            net = ipaddress.ip_network(host_input, strict=False)
            targets = [str(ip) for ip in net.hosts()]
        elif '-' in host_input:
            parts = host_input.split('-')
            try:
                start = ipaddress.IPv4Address(parts[0].strip())
                end = ipaddress.IPv4Address(parts[1].strip())
                for ip_block in ipaddress.summarize_address_range(start, end):
                    targets.extend(str(ip) for ip in ip_block)
            except:
                targets = self.generate_dns_range(parts[0].strip(), parts[1].strip())
        else:
            targets = [host_input]
        return targets

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def parse_ports_from_args(self):
        args = sys.argv[1:]
        if not args:
            print("❌ Error: No ports provided.")
            print("✅ Usage: python port_scanner.py [80] [22-25] [443] [5000 8000] ...")
            sys.exit(1)

        ports = set()
        for arg in args:
            if '-' in arg:
                try:
                    start, end = map(int, arg.split('-'))
                    ports.update(range(start, end + 1))
                except:
                    print(f"⚠️ Invalid range format: {arg}")
                    sys.exit(1)
            else:
                try:
                    split_ports = arg.split(" ")
                    for sp in split_ports:
                        ports.add(int(sp))
                except:
                    print(f"⚠️ Invalid port: {arg}")
                    sys.exit(1)
        return sorted(ports)

    def run(self):
        results = {}
        local_ip = self.get_local_ip()
        subnet = re.sub(r"\.\d+$", ".0/24", local_ip)
        ports = self.parse_ports_from_args()

        try:
            hostnames = self.expand_targets(subnet)
            resolved_targets = [(h, self.resolve_to_ip(h)) for h in hostnames]
            resolved_targets = [(h, ip) for h, ip in resolved_targets if ip]

            with ThreadPoolExecutor(max_workers=100) as executor:
                futures = {}
                for host, ip in resolved_targets:
                    for port in ports:
                        future = executor.submit(self.scan_host, ip, port)
                        futures[(host, port, ip)] = future

                for (host, port, ip), future in futures.items():
                    if future.result():
                        key = f"{host} ({ip})"
                        results.setdefault(key, {"hostname": None, "mac": None, "ports": []})
                        results[key]["ports"].append(port)

                for key in results:
                    ip = key.split('(')[-1].rstrip(')')
                    if self.is_local_ip(ip):
                        hostname = self.get_hostname(ip) or ip
                        results[key]["hostname"] = hostname
                        results[key]["mac"] = self.get_mac(ip)

                if not results:
                    results = {"No responsive hosts found.": {"ports": [], "hostname": None, "mac": None}}
        except Exception as e:
            results = {f"Error: {str(e)}": {"ports": [], "hostname": None, "mac": None}}

        print(results)


if __name__ == '__main__':
    PortScan().run()
