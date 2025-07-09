import geoip2.database
from geoip2.errors import AddressNotFoundError
from typing import Tuple, Optional, Dict

class IPGeoLocator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.reader = None
        self._initialize_reader()

    def _initialize_reader(self):
        """初始化GeoIP数据库读取器"""
        try:
            self.reader = geoip2.database.Reader(self.db_path)
        except FileNotFoundError:
            raise ValueError(f"GeoIP数据库文件未找到: {self.db_path}\n请下载GeoLite2-Country数据库并配置正确路径")
        except Exception as e:
            raise RuntimeError(f"初始化GeoIP数据库失败: {str(e)}")

    def get_location(self, ip_address: str) -> Tuple[Optional[str], Optional[str]]:
        """获取IP地址的国家和地区信息"""
        if not self.reader:
            self._initialize_reader()
        try:
            response = self.reader.country(ip_address)
            country_iso = response.country.iso_code
            country_name = response.country.name
            return country_iso, country_name
        except AddressNotFoundError:
            return None, None
        except Exception as e:
            print(f"获取IP位置失败: {str(e)}")
            return None, None

    def is_private_ip(self, ip_address: str) -> bool:
        """Check if the IP address is in a private (LAN) range"""
        import ipaddress
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private
        except ValueError:
            return False

    def close(self):
        if hasattr(self, 'reader') and self.reader:
            self.reader.close()


def analyze_ip_access(ip_list: list, db_path: str) -> Tuple[Dict[str, int], Dict[str, int]]:
    """分析IP访问情况，返回国内和国外IP的访问次数统计"""
    internal_ips = {}
    external_ips = {}
    locator = None

    try:
        # 使用传入的数据库路径初始化定位器
        locator = IPGeoLocator(db_path)

        for ip in ip_list:
            if locator.is_private_ip(ip):
                internal_ips[ip] = internal_ips.get(ip, 0) + 1
            else:
                external_ips[ip] = external_ips.get(ip, 0) + 1
    finally:
        if locator:
            locator.close()

    # 按访问次数排序
    internal_ips = dict(sorted(internal_ips.items(), key=lambda x: x[1], reverse=True))
    external_ips = dict(sorted(external_ips.items(), key=lambda x: x[1], reverse=True))

    return internal_ips, external_ips