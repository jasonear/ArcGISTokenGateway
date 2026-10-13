import argparse
import sys
import os

# Add current directory to path for importing config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone, timedelta
from config import JWT_EXPIRE_MINUTES
from service.token_service import generate_token as generate_token_from_service
from service.token_store import save_token_record, list_tokens, delete_token, get_token, add_service_to_token


def print_list(only_active: bool = False):
    """打印 Token 列表；only_active 为 True 时仅显示有效（未撤销且未过期）的 Token"""
    tokens = list_tokens()
    if only_active:
        now = datetime.now(timezone.utc)
        filtered = []
        for token in tokens:
            if token.get("status") != "active":
                continue
            try:
                # 有效期未知按无效处理（fail-closed）
                if datetime.fromisoformat(token.get("expire_at", "")) <= now:
                    continue
            except (ValueError, TypeError):
                continue
            filtered.append(token)
        tokens = filtered

    if not tokens:
        print("没有符合条件的 Token 记录。" if only_active else "当前没有已生成的 Token 记录。")
        return

    print("=" * 80)
    print("有效 Token 列表:" if only_active else "Token 列表:")
    print("=" * 80)

    for token in tokens:
        created_at = token.get("created_at", "N/A")
        expire_at = token.get("expire_at", "N/A")

        try:
            created_dt = datetime.fromisoformat(created_at)
            created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            created_str = created_at

        try:
            expire_dt = datetime.fromisoformat(expire_at)
            expire_str = expire_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            expire_str = expire_at

        services_str = ", ".join(token.get("services", []))
        status = token.get("status", "unknown")

        print(f"Token ID: {token.get('token_id', 'N/A')}")
        print(f"合作伙伴: {token.get('partner', 'N/A')}")
        print(f"授权服务: {services_str}")
        print(f"创建时间: {created_str}")
        print(f"过期时间: {expire_str}")
        print(f"状态: {status}")
        print()

    print("=" * 80)
    print(f"总计: {len(tokens)} 个 Token")


def print_delete(token_id: str):
    result = delete_token(token_id)
    if result:
        print(f"Token {token_id} 已删除（标记为 revoked）。")
    else:
        print(f"未找到 Token ID: {token_id}")


def main():
    parser = argparse.ArgumentParser(
        description="ArcGIS Token 管理工具 - 生成、查看、删除 Token",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成 Token
  python generate_token.py --partner "PartnerA" --services "ArcGIS/rest/services/TestMap/MapServer"

  # 查看有效 Token 列表
  python generate_token.py --list

  # 查看全部 Token 记录（含已撤销、已过期）
  python generate_token.py --listall

  # 删除 Token
  python generate_token.py --delete "550e8400-e29b-41d4-a716-446655440000"

  # 为 Token 增加可访问的服务
  python generate_token.py --add-service "550e8400-e29b-41d4-a716-446655440000" "ArcGIS/rest/services/NewMap/MapServer"
        """,
    )

    parser.add_argument("--partner", type=str, help="合作伙伴名称")
    parser.add_argument("--services", type=str, nargs="+", help="授权服务列表")
    parser.add_argument("--hours", type=float, default=JWT_EXPIRE_MINUTES / 60, help="Token 有效期（小时，默认取 .env 中 JWT_EXPIRE_HOURS）")
    parser.add_argument("--list", action="store_true", help="查看有效 Token 列表（未撤销且未过期）")
    parser.add_argument("--listall", action="store_true", help="查看全部 Token 记录（含已撤销、已过期）")
    parser.add_argument("--delete", type=str, metavar="TOKEN_ID", help="删除指定 Token（传入 Token ID）")
    parser.add_argument("--add-service", nargs=2, metavar=("TOKEN_ID", "SERVICE"), help="为指定 Token 增加可访问的服务")

    args = parser.parse_args()

    if args.list:
        print_list(only_active=True)
        return

    if args.listall:
        print_list()
        return

    if args.delete:
        print_delete(args.delete)
        return

    if args.add_service:
        token_id, service = args.add_service
        result = add_service_to_token(token_id, service)
        if result:
            print(f"成功为 Token {token_id} 增加服务: {service}")
            print(f"当前授权服务: {', '.join(result.get('services', []))}")
        else:
            print(f"未找到 Token ID: {token_id}")
        return

    if not args.partner or not args.services:
        parser.print_help()
        print("\n错误: 生成 Token 需要提供 --partner 和 --services 参数。")
        sys.exit(1)

    expire_minutes = int(args.hours * 60)

    token, token_id = generate_token_from_service(args.partner, args.services, expire_minutes)

    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(minutes=expire_minutes)
    expire_at_str = expire_at.isoformat()

    save_token_record(token_id, args.partner, args.services, expire_at_str)

    try:
        expire_display = expire_at.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        expire_display = expire_at_str

    print("=" * 60)
    print("Token 生成成功!")
    print("=" * 60)
    print(f"Token ID: {token_id}")
    print(f"合作伙伴: {args.partner}")
    print(f"授权服务:")
    for service in args.services:
        print(f"  - {service}")
    print(f"过期时间: {expire_display} UTC")
    print("=" * 60)
    print("Token:")
    print(token)
    print("=" * 60)
    print("\n请妥善保管此 Token，不要泄露给未授权方。")


if __name__ == "__main__":
    main()