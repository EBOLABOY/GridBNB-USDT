"""
API 密钥安全管理模块

提供 API 密钥的加密存储和安全访问功能。
使用 Fernet 对称加密来保护存储的 API 密钥。

安全特性:
1. 使用密钥派生函数 (PBKDF2) 从密码生成加密密钥
2. API 密钥加密后存储,不以明文形式保存
3. 支持密钥验证和权限检查
4. 提供密钥轮换功能

使用方法:
from src.security.api_key_manager import APIKeyManager

    # 初始化管理器
    manager = APIKeyManager(master_password="your_secure_password")

    # 存储API密钥
    manager.store_api_keys("your_api_key", "your_api_secret")

    # 获取API密钥
    api_key, api_secret = manager.get_api_keys()
"""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning(
        "cryptography 库未安装,API密钥加密功能不可用。" "请运行: pip install cryptography"
    )


class APIKeyManager:
    """
    API 密钥安全管理器

    负责 API 密钥的加密存储、解密访问和安全管理。
    """

    def __init__(
        self,
        master_password: Optional[str] = None,
        storage_path: Optional[str] = None,
        salt: Optional[bytes] = None,
    ):
        """
        初始化 API 密钥管理器

        Args:
            master_password: 主密码,用于生成加密密钥
            storage_path: 加密数据存储路径
            salt: 密钥派生盐值(可选,不提供则自动生成)

        Raises:
            ImportError: 如果 cryptography 库未安装
            ValueError: 如果未提供主密码
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography 库未安装,无法使用API密钥加密功能。" "请运行: pip install cryptography"
            )

        if not master_password:
            raise ValueError("必须提供主密码以初始化 APIKeyManager")

        self.logger = logging.getLogger(self.__class__.__name__)

        # 设置存储路径
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / ".gridbnb" / "api_keys.enc"

        # 确保存储目录存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化或加载盐值
        if salt:
            self.salt = salt
        else:
            self.salt = self._load_or_generate_salt()

        # 从主密码派生加密密钥
        self.cipher = self._derive_cipher(master_password)

        self.logger.info("APIKeyManager 初始化完成")

    def _load_or_generate_salt(self) -> bytes:
        """加载或生成新的盐值"""
        salt_path = self.storage_path.parent / "salt.bin"

        if salt_path.exists():
            with open(salt_path, "rb") as f:
                salt = f.read()
                self.logger.debug("已加载现有盐值")
                return salt
        else:
            # 生成新的随机盐值
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
            self.logger.info("已生成新的盐值")
            return salt

    def _derive_cipher(self, password: str) -> Fernet:
        """
        从密码派生加密密钥

        使用 PBKDF2 密钥派生函数从密码生成强加密密钥。

        Args:
            password: 主密码

        Returns:
            Fernet 加密器实例
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,  # 迭代次数,越高越安全但越慢
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def store_api_keys(
        self, api_key: str, api_secret: str, metadata: Optional[dict] = None
    ) -> bool:
        """
        加密并存储 API 密钥

        Args:
            api_key: API Key
            api_secret: API Secret
            metadata: 可选的元数据(如创建时间、描述等)

        Returns:
            bool: 存储是否成功
        """
        try:
            # 构建数据结构
            data = {"api_key": api_key, "api_secret": api_secret, "metadata": metadata or {}}

            # 序列化为 JSON
            json_data = json.dumps(data)

            # 加密
            encrypted_data = self.cipher.encrypt(json_data.encode())

            # 保存到文件
            with open(self.storage_path, "wb") as f:
                f.write(encrypted_data)

            # 设置文件权限为仅所有者可读写
            if os.name != "nt":  # Unix/Linux
                os.chmod(self.storage_path, 0o600)

            self.logger.info("API 密钥已安全存储")
            return True

        except Exception as e:
            self.logger.error(f"存储 API 密钥失败: {e}")
            return False

    def get_api_keys(self) -> Tuple[Optional[str], Optional[str]]:
        """
        解密并获取 API 密钥

        Returns:
            Tuple[api_key, api_secret]: API 密钥对,失败返回 (None, None)
        """
        try:
            if not self.storage_path.exists():
                self.logger.warning("API 密钥文件不存在")
                return None, None

            # 读取加密数据
            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()

            # 解密
            decrypted_data = self.cipher.decrypt(encrypted_data)

            # 解析 JSON
            data = json.loads(decrypted_data.decode())

            return data["api_key"], data["api_secret"]

        except Exception as e:
            self.logger.error(f"获取 API 密钥失败: {e}")
            return None, None

    def verify_password(self, password: str) -> bool:
        """
        验证主密码是否正确

        Args:
            password: 待验证的密码

        Returns:
            bool: 密码是否正确
        """
        try:
            test_cipher = self._derive_cipher(password)

            if not self.storage_path.exists():
                # 如果没有存储的数据,无法验证
                return True

            # 读取加密数据
            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()

            # 尝试解密
            test_cipher.decrypt(encrypted_data)
            return True

        except Exception:
            return False

    def rotate_encryption_key(self, new_password: str) -> bool:
        """
        轮换加密密钥

        使用新密码重新加密所有数据。这是一个安全的操作,
        原密钥解密后立即用新密钥重新加密。

        Args:
            new_password: 新的主密码

        Returns:
            bool: 轮换是否成功
        """
        try:
            # 使用旧密钥获取数据
            api_key, api_secret = self.get_api_keys()

            if not api_key or not api_secret:
                self.logger.error("无法获取现有密钥,轮换失败")
                return False

            # 生成新的盐值
            self.salt = os.urandom(16)
            salt_path = self.storage_path.parent / "salt.bin"
            with open(salt_path, "wb") as f:
                f.write(self.salt)

            # 生成新的加密器
            self.cipher = self._derive_cipher(new_password)

            # 使用新密钥重新存储
            return self.store_api_keys(api_key, api_secret)

        except Exception as e:
            self.logger.error(f"轮换加密密钥失败: {e}")
            return False

    def delete_stored_keys(self) -> bool:
        """
        删除存储的加密密钥

        Returns:
            bool: 删除是否成功
        """
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
                self.logger.info("已删除存储的 API 密钥")

            salt_path = self.storage_path.parent / "salt.bin"
            if salt_path.exists():
                salt_path.unlink()
                self.logger.info("已删除盐值文件")

            return True

        except Exception as e:
            self.logger.error(f"删除密钥文件失败: {e}")
            return False

    def get_metadata(self) -> Optional[dict]:
        """
        获取存储的元数据

        Returns:
            dict: 元数据,失败返回 None
        """
        try:
            if not self.storage_path.exists():
                return None

            # 读取加密数据
            with open(self.storage_path, "rb") as f:
                encrypted_data = f.read()

            # 解密
            decrypted_data = self.cipher.decrypt(encrypted_data)

            # 解析 JSON
            data = json.loads(decrypted_data.decode())

            return data.get("metadata", {})

        except Exception as e:
            self.logger.error(f"获取元数据失败: {e}")
            return None


def generate_secure_password() -> str:
    """
    生成一个安全的随机密码

    Returns:
        str: 32字符的安全随机密码
    """
    return base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")


def hash_password(password: str) -> str:
    """
    生成密码的哈希值(用于验证)

    Args:
        password: 明文密码

    Returns:
        str: 密码的 SHA-256 哈希值(十六进制)
    """
    return hashlib.sha256(password.encode()).hexdigest()


if __name__ == "__main__":
    # 示例用法
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=== API 密钥管理器示例 ===\n")

    # 1. 生成安全密码
    master_password = generate_secure_password()
    print(f"生成的主密码: {master_password}\n")

    # 2. 初始化管理器
    manager = APIKeyManager(master_password=master_password)

    # 3. 存储 API 密钥
    test_api_key = "test_api_key_" + os.urandom(8).hex()
    test_api_secret = "test_api_secret_" + os.urandom(16).hex()

    print("存储 API 密钥...")
    if manager.store_api_keys(
        test_api_key,
        test_api_secret,
        metadata={"created_at": "2025-01-01", "description": "Test keys"},
    ):
        print("✓ API 密钥已安全存储\n")

    # 4. 读取 API 密钥
    print("读取 API 密钥...")
    retrieved_key, retrieved_secret = manager.get_api_keys()

    if retrieved_key == test_api_key and retrieved_secret == test_api_secret:
        print("✓ API 密钥读取成功并验证一致\n")
    else:
        print("✗ API 密钥验证失败\n")
        sys.exit(1)

    # 5. 验证密码
    print("验证密码...")
    if manager.verify_password(master_password):
        print("✓ 密码验证成功\n")

    # 6. 清理测试数据
    print("清理测试数据...")
    if manager.delete_stored_keys():
        print("✓ 测试数据已清理\n")

    print("=== 示例完成 ===")
