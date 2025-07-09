import yaml
from core.ip_utils import IPGeoLocator

def test_ip_geolocation(ip_address: str):
    # 加载配置文件
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 获取GeoIP数据库路径
    geoip_db_path = config.get('geoip_db_path')
    if not geoip_db_path:
        print("错误: 配置文件中未找到geoip_db_path")
        return
    
    # 初始化IP定位器
    try:
        locator = IPGeoLocator(geoip_db_path)
        country_iso, country_name = locator.get_location(ip_address)
        
        if country_name:
            print(f"IP地址 {ip_address} 的地理位置: {country_name} ({country_iso})")
        else:
            print(f"无法识别IP地址 {ip_address} 的地理位置")
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        if 'locator' in locals():
            locator.close()

if __name__ == "__main__":
    test_ip_geolocation("104.152.52.86")