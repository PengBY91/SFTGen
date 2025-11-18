"""
用户认证服务
负责用户管理、登录认证、JWT Token 生成等
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import JWTError, jwt

from backend.schemas import User, UserRole, UserCreate, UserLogin, UserUpdate


# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.users_file = "cache/users.json"
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        self._init_default_users()
    
    def _init_default_users(self):
        """初始化默认用户"""
        if not os.path.exists(self.users_file):
            # 创建默认管理员和审核员
            default_users = {
                "admin": {
                    "user_id": str(uuid.uuid4()),
                    "username": "admin",
                    "password_hash": self._hash_password("admin123"),
                    "email": "admin@graphgen.com",
                    "role": UserRole.ADMIN,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                },
                "reviewer": {
                    "user_id": str(uuid.uuid4()),
                    "username": "reviewer",
                    "password_hash": self._hash_password("reviewer123"),
                    "email": "reviewer@graphgen.com",
                    "role": UserRole.REVIEWER,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
            }
            self._save_users(default_users)
    
    def _load_users(self) -> Dict[str, Any]:
        """加载用户数据"""
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载用户数据失败: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        """保存用户数据"""
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存用户数据失败: {e}")
    
    def _hash_password(self, password: str) -> str:
        """哈希密码 - 使用 SHA256"""
        salt = SECRET_KEY
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self._hash_password(plain_password) == hashed_password
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建 JWT Token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT Token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return payload
        except JWTError:
            return None
    
    def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """创建用户"""
        try:
            users = self._load_users()
            
            # 检查用户名是否已存在
            if user_data.username in users:
                return {
                    "success": False,
                    "error": "用户名已存在"
                }
            
            # 创建新用户
            user_id = str(uuid.uuid4())
            user = {
                "user_id": user_id,
                "username": user_data.username,
                "password_hash": self._hash_password(user_data.password),
                "email": user_data.email,
                "role": user_data.role,
                "is_active": True,
                "created_at": datetime.now().isoformat()
            }
            
            users[user_data.username] = user
            self._save_users(users)
            
            # 返回用户信息（不包含密码）
            user_info = User(
                user_id=user["user_id"],
                username=user["username"],
                email=user["email"],
                role=user["role"],
                is_active=user["is_active"],
                created_at=user["created_at"]
            )
            
            return {
                "success": True,
                "message": "用户创建成功",
                "data": user_info.dict()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"创建用户失败: {str(e)}"
            }
    
    def login(self, login_data: UserLogin) -> Dict[str, Any]:
        """用户登录"""
        try:
            users = self._load_users()
            
            # 检查用户是否存在
            if login_data.username not in users:
                return {
                    "success": False,
                    "error": "用户名或密码错误"
                }
            
            user = users[login_data.username]
            
            # 检查用户是否激活
            if not user.get("is_active", True):
                return {
                    "success": False,
                    "error": "用户已被禁用"
                }
            
            # 验证密码
            if not self._verify_password(login_data.password, user["password_hash"]):
                return {
                    "success": False,
                    "error": "用户名或密码错误"
                }
            
            # 更新最后登录时间
            user["last_login"] = datetime.now().isoformat()
            users[login_data.username] = user
            self._save_users(users)
            
            # 生成 Token
            access_token = self._create_access_token(
                data={"sub": user["username"], "role": user["role"]}
            )
            
            # 返回用户信息和 Token
            user_info = User(
                user_id=user["user_id"],
                username=user["username"],
                email=user.get("email"),
                role=user["role"],
                is_active=user["is_active"],
                created_at=user.get("created_at"),
                last_login=user["last_login"]
            )
            
            return {
                "success": True,
                "message": "登录成功",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user_info.dict()
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"登录失败: {str(e)}"
            }
    
    def get_current_user(self, token: str) -> Optional[User]:
        """获取当前用户"""
        try:
            payload = self.verify_token(token)
            if not payload:
                return None
            
            username = payload.get("sub")
            if not username:
                return None
            
            users = self._load_users()
            if username not in users:
                return None
            
            user = users[username]
            return User(
                user_id=user["user_id"],
                username=user["username"],
                email=user.get("email"),
                role=user["role"],
                is_active=user["is_active"],
                created_at=user.get("created_at"),
                last_login=user.get("last_login")
            )
        
        except Exception as e:
            print(f"获取当前用户失败: {e}")
            return None
    
    def get_all_users(self) -> Dict[str, Any]:
        """获取所有用户"""
        try:
            users = self._load_users()
            user_list = []
            
            for username, user in users.items():
                user_info = User(
                    user_id=user["user_id"],
                    username=user["username"],
                    email=user.get("email"),
                    role=user["role"],
                    is_active=user["is_active"],
                    created_at=user.get("created_at"),
                    last_login=user.get("last_login")
                )
                user_list.append(user_info.dict())
            
            return {
                "success": True,
                "data": user_list
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"获取用户列表失败: {str(e)}"
            }
    
    def update_user(self, username: str, update_data: UserUpdate) -> Dict[str, Any]:
        """更新用户"""
        try:
            users = self._load_users()
            
            if username not in users:
                return {
                    "success": False,
                    "error": "用户不存在"
                }
            
            user = users[username]
            
            # 更新字段
            if update_data.email is not None:
                user["email"] = update_data.email
            if update_data.password is not None:
                user["password_hash"] = self._hash_password(update_data.password)
            if update_data.role is not None:
                user["role"] = update_data.role
            if update_data.is_active is not None:
                user["is_active"] = update_data.is_active
            
            users[username] = user
            self._save_users(users)
            
            user_info = User(
                user_id=user["user_id"],
                username=user["username"],
                email=user.get("email"),
                role=user["role"],
                is_active=user["is_active"],
                created_at=user.get("created_at"),
                last_login=user.get("last_login")
            )
            
            return {
                "success": True,
                "message": "用户更新成功",
                "data": user_info.dict()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"更新用户失败: {str(e)}"
            }
    
    def delete_user(self, username: str) -> Dict[str, Any]:
        """删除用户"""
        try:
            users = self._load_users()
            
            if username not in users:
                return {
                    "success": False,
                    "error": "用户不存在"
                }
            
            # 不允许删除最后一个管理员
            admin_count = sum(1 for u in users.values() if u["role"] == UserRole.ADMIN)
            if users[username]["role"] == UserRole.ADMIN and admin_count <= 1:
                return {
                    "success": False,
                    "error": "不能删除最后一个管理员"
                }
            
            del users[username]
            self._save_users(users)
            
            return {
                "success": True,
                "message": "用户删除成功"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"删除用户失败: {str(e)}"
            }
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        try:
            users = self._load_users()
            
            if username not in users:
                return {
                    "success": False,
                    "error": "用户不存在"
                }
            
            user = users[username]
            
            # 验证旧密码
            if not self._verify_password(old_password, user["password_hash"]):
                return {
                    "success": False,
                    "error": "旧密码错误"
                }
            
            # 更新密码
            user["password_hash"] = self._hash_password(new_password)
            users[username] = user
            self._save_users(users)
            
            return {
                "success": True,
                "message": "密码修改成功"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"修改密码失败: {str(e)}"
            }


# 全局服务实例
auth_service = AuthService()

