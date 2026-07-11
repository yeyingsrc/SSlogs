import geoip2.database
from geoip2.errors import AddressNotFoundError, GeoIP2Error
from typing import Tuple, Optional, Dict, List
import ipaddress

class IPGeoLocator:
    """IP地理位置查询器，使用MaxMind GeoLite2数据库"""

    def __init__(self, db_path: str) -> None:
        """初始化IP地理位置查询器

        Args:
            db_path: GeoLite2数据库文件路径

        Raises:
            ValueError: 数据库文件不存在
            RuntimeError: 数据库初始化失败
        """
        self.db_path = db_path
        self.reader: Optional[geoip2.database.Reader] = None
        self._initialize_reader()

    def _initialize_reader(self) -> None:
        """初始化GeoIP数据库读取器

        Raises:
            ValueError: 数据库文件不存在
            RuntimeError: 数据库初始化失败
        """
        try:
            self.reader = geoip2.database.Reader(self.db_path)
        except FileNotFoundError:
            raise ValueError(f"GeoIP数据库文件未找到: {self.db_path}\n请下载GeoLite2-Country数据库并配置正确路径")
        except Exception as e:
            raise RuntimeError(f"初始化GeoIP数据库失败: {str(e)}")

    def get_location(self, ip_address: str) -> Tuple[Optional[str], Optional[str]]:
        """获取IP地址的国家和地区信息

        Args:
            ip_address: IP地址字符串

        Returns:
            Tuple[Optional[str], Optional[str]]: (国家ISO代码, 国家名称)，查询失败返回 (None, None)
        """
        if not self.reader:
            self._initialize_reader()

        try:
            response = self.reader.country(ip_address)
            country_iso = response.country.iso_code
            country_name = response.country.name
            return country_iso, country_name
        except (AddressNotFoundError, GeoIP2Error):
            return None, None
        except Exception as e:
            print(f"获取IP位置失败: {str(e)}")
            return None, None

    def is_private_ip(self, ip_address: str) -> bool:
        """检查IP地址是否为私有（LAN）地址

        Args:
            ip_address: IP地址字符串

        Returns:
            bool: 如果是私有IP返回True，否则返回False
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private
        except ValueError:
            return False

    def close(self) -> None:
        """关闭数据库连接，释放资源"""
        if hasattr(self, 'reader') and self.reader:
            self.reader.close()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False


def analyze_ip_access(ip_list: List[str], db_path: str) -> Tuple[Dict[str, int], Dict[str, int]]:
    """分析IP访问情况，返回内网和外网IP的访问次数统计

    Args:
        ip_list: IP地址列表
        db_path: GeoLite2数据库文件路径

    Returns:
        Tuple[Dict[str, int], Dict[str, int]]: (内网IP统计, 外网IP统计)
    """
    internal_ips: Dict[str, int] = {}
    external_ips: Dict[str, int] = {}
    locator: Optional[IPGeoLocator] = None

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