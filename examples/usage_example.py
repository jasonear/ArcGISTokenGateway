"""
ArcGIS Token Gateway 使用示例脚本

这个脚本演示了如何：
1. 生成 JWT Token
2. 使用 Token 访问 ArcGIS 地图服务
3. 常见的地图服务操作（查询、导出等）
"""

import sys
import os
import requests
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.token_service import generate_token

# ==================== 配置 ====================
GATEWAY_URL = "http://localhost:8000"
ARCGIS_SERVICE = "ArcGIS/rest/services/TestMap/MapServer"

# ==================== 1. 生成 Token ====================
def demo_generate_token():
    """演示生成 Token"""
    print("=" * 60)
    print("1. 生成 JWT Token")
    print("=" * 60)
    
    partner = "DemoPartner"
    services = [ARCGIS_SERVICE]
    expire_hours = 2
    
    # 生成 Token
    token, token_id = generate_token(partner, services, expire_minutes=int(expire_hours * 60))
    
    print(f"合作伙伴: {partner}")
    print(f"Token ID: {token_id}")
    print(f"授权服务: {', '.join(services)}")
    print(f"Token: {token[:50]}...")
    print()
    
    return token


# ==================== 2. 查询图层信息 ====================
def demo_get_layer_info(token):
    """演示获取图层信息"""
    print("=" * 60)
    print("2. 获取图层信息")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"服务名称: {data.get('serviceName', 'N/A')}")
            print(f"图层数量: {data.get('layers', [])}")
            print(f"子图层数量: {data.get('singleFusedMapCache', 'N/A')}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 3. 查询要素 ====================
def demo_query_features(token):
    """演示查询地图要素"""
    print("=" * 60)
    print("3. 查询地图要素")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}/0/query"
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "returnGeometry": "true",
        "maxRecordCount": 10,
    }
    
    try:
        response = requests.post(url, headers=headers, data=params)
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            print(f"查询到 {len(features)} 个要素")
            if features:
                print(f"第一个要素属性: {features[0].get('attributes', {})}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 4. 空间查询 ====================
def demo_spatial_query(token):
    """演示空间查询"""
    print("=" * 60)
    print("4. 空间查询（矩形范围）")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}/0/query"
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "geometry": '{"xmin":100000,"ymin":4000000,"xmax":110000,"ymax":4010000,"spatialReference":{"wkid":4490}}',
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "f": "json",
        "returnGeometry": "true",
    }
    
    try:
        response = requests.post(url, headers=headers, data=params)
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            print(f"空间查询到 {len(features)} 个要素")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 5. 统计查询 ====================
def demo_statistics_query(token):
    """演示统计查询"""
    print("=" * 60)
    print("5. 统计查询")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}/0/query"
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "where": "1=1",
        "outStatistics": "[{'statisticType':'count','onStatisticField':'OBJECTID','outStatisticFieldName':'count'}]",
        "f": "json",
    }
    
    try:
        response = requests.post(url, headers=headers, data=params)
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            if features:
                print(f"统计结果: {features[0].get('attributes', {})}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 6. 使用 Query 参数传递 Token ====================
def demo_query_param_token(token):
    """演示使用 Query 参数传递 Token"""
    print("=" * 60)
    print("6. 使用 Query 参数传递 Token")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}?token={token}&f=json"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功获取服务信息")
            print(f"服务名称: {data.get('serviceName', 'N/A')}")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 7. 错误处理示例 ====================
def demo_error_handling():
    """演示错误处理"""
    print("=" * 60)
    print("7. 错误处理示例")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}"
    
    # 测试 1: 无 Token
    print("测试 1: 无 Token 访问")
    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"错误: {e}")
    print()
    
    # 测试 2: 无效 Token
    print("测试 2: 使用无效 Token")
    headers = {"Authorization": "Bearer invalid-token-12345"}
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"错误: {e}")
    print()


# ==================== 8. 获取字段信息 ====================
def demo_get_fields(token):
    """演示获取字段信息"""
    print("=" * 60)
    print("8. 获取字段信息")
    print("=" * 60)
    
    url = f"{GATEWAY_URL}/{ARCGIS_SERVICE}/0"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            fields = data.get("fields", [])
            print(f"图层字段数量: {len(fields)}")
            for field in fields[:5]:  # 只显示前 5 个字段
                print(f"  - {field.get('name')}: {field.get('type')}")
            if len(fields) > 5:
                print(f"  ... 还有 {len(fields) - 5} 个字段")
        else:
            print(f"错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    print()


# ==================== 主函数 ====================
def main():
    print("\n" + "=" * 60)
    print("ArcGIS Token Gateway 使用示例")
    print("=" * 60)
    print(f"网关地址: {GATEWAY_URL}")
    print(f"地图服务: {ARCGIS_SERVICE}")
    print()
    
    # 生成 Token
    token = demo_generate_token()
    
    # 执行各个示例
    demo_get_layer_info(token)
    demo_query_features(token)
    demo_spatial_query(token)
    demo_statistics_query(token)
    demo_query_param_token(token)
    demo_get_fields(token)
    demo_error_handling()
    
    print("=" * 60)
    print("示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()