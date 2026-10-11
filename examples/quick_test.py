#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本 - ArcGIS Token Gateway

使用方法:
    python quick_test.py
"""

import sys
import os
import requests

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service.token_service import generate_token

# 配置
GATEWAY_URL = "http://localhost:8000"
TEST_SERVICE = "ArcGIS/rest/services/TestMap/MapServer"


def test_1_health_check():
    """测试 1: 健康检查"""
    print("\n[测试 1] 健康检查")
    print("-" * 40)
    
    try:
        response = requests.get(f"{GATEWAY_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_2_generate_token():
    """测试 2: 生成 Token"""
    print("\n[测试 2] 生成 Token")
    print("-" * 40)
    
    try:
        token, token_id = generate_token(
            partner="TestPartner",
            services=[TEST_SERVICE],
            expire_minutes=120
        )
        print(f"✓ Token 生成成功")
        print(f"  Token ID: {token_id}")
        print(f"  Token: {token[:30]}...")
        return token
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return None


def test_3_access_without_token():
    """测试 3: 无 Token 访问"""
    print("\n[测试 3] 无 Token 访问")
    print("-" * 40)
    
    try:
        response = requests.get(f"{GATEWAY_URL}/{TEST_SERVICE}")
        print(f"状态码: {response.status_code}")
        if response.status_code == 401:
            print("✓ 正确拒绝无 Token 访问")
            return True
        else:
            print(f"✗ 预期 401，实际 {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_4_access_with_invalid_token():
    """测试 4: 无效 Token 访问"""
    print("\n[测试 4] 无效 Token 访问")
    print("-" * 40)
    
    try:
        headers = {"Authorization": "Bearer invalid-token"}
        response = requests.get(f"{GATEWAY_URL}/{TEST_SERVICE}", headers=headers)
        print(f"状态码: {response.status_code}")
        if response.status_code == 401:
            print("✓ 正确拒绝无效 Token")
            return True
        else:
            print(f"✗ 预期 401，实际 {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_5_access_with_valid_token(token):
    """测试 5: 有效 Token 访问"""
    print("\n[测试 5] 有效 Token 访问")
    print("-" * 40)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{GATEWAY_URL}/{TEST_SERVICE}", headers=headers)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功访问地图服务")
            print(f"  服务名称: {data.get('serviceName', 'N/A')}")
            return True
        else:
            print(f"✗ 访问失败: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_6_access_with_query_param(token):
    """测试 6: Query 参数传递 Token"""
    print("\n[测试 6] Query 参数传递 Token")
    print("-" * 40)
    
    try:
        url = f"{GATEWAY_URL}/{TEST_SERVICE}?token={token}&f=json"
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Query 参数方式成功")
            print(f"  服务名称: {data.get('serviceName', 'N/A')}")
            return True
        else:
            print(f"✗ 访问失败: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_7_access_unauthorized_service(token):
    """测试 7: 访问未授权服务"""
    print("\n[测试 7] 访问未授权服务")
    print("-" * 40)
    
    unauthorized_service = "ArcGIS/rest/services/OtherMap/MapServer"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{GATEWAY_URL}/{unauthorized_service}", headers=headers)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 403:
            print("✓ 正确拒绝未授权服务访问")
            return True
        else:
            print(f"✗ 预期 403，实际 {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def main():
    print("=" * 60)
    print("ArcGIS Token Gateway - 快速测试")
    print("=" * 60)
    print(f"网关地址: {GATEWAY_URL}")
    print(f"测试服务: {TEST_SERVICE}")
    
    results = []
    
    # 运行测试
    results.append(("健康检查", test_1_health_check()))
    token = test_2_generate_token()
    results.append(("生成 Token", token is not None))
    results.append(("无 Token 访问", test_3_access_without_token()))
    results.append(("无效 Token 访问", test_4_access_with_invalid_token()))
    
    if token:
        results.append(("有效 Token 访问", test_5_access_with_valid_token(token)))
        results.append(("Query 参数 Token", test_6_access_with_query_param(token)))
        results.append(("未授权服务访问", test_7_access_unauthorized_service(token)))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)