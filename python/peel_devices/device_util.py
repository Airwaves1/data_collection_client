import ipaddress

def check_ip_address(ip_addr):
    try:
        ip = ipaddress.ip_address(ip_addr)
        return True
    except ValueError:
        return False
    
def check_ip_port(ip_port):
    port = int(ip_port)
    if port >=0 and port <= 65535:
        return True
    else:
        return False
    