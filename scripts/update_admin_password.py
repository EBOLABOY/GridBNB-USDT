"""
临时脚本：更新admin用户密码为bcrypt哈希
"""

import os
import sys
from passlib.context import CryptContext

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.connection import db_manager
from src.database.models import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def update_admin_password():
    """更新admin用户密码为bcrypt哈希"""
    try:
        with db_manager.get_session() as session:
            # 查找admin用户
            admin = session.query(User).filter_by(username='admin').first()

            if not admin:
                print("Admin user not found")
                return False

            # 更新密码为bcrypt哈希
            new_password_hash = pwd_context.hash("admin123")
            admin.password_hash = new_password_hash

            session.commit()

            print("Admin password updated to bcrypt hash")
            print("Username: admin")
            print("Password: admin123")
            return True

    except Exception as e:
        print(f"Update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_admin_password()
    sys.exit(0 if success else 1)
