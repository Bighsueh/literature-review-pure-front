#!/usr/bin/env python3
"""
部署前 Schema 驗證工具
確保資料庫 Schema 與程式碼模型一致
"""

import asyncio
import sys
import json
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

# 添加 backend 路徑
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from database.connection import db_manager
from database.models import *  # 導入所有模型
from core.config import get_settings

@dataclass
class ColumnInfo:
    """資料庫欄位資訊"""
    name: str
    type: str
    nullable: bool
    default: Any = None
    primary_key: bool = False

@dataclass
class TableInfo:
    """資料庫表格資訊"""
    name: str
    columns: Dict[str, ColumnInfo]
    indexes: List[str]
    foreign_keys: List[str]

class SchemaValidator:
    """Schema 驗證器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        
    async def initialize(self):
        """初始化資料庫連接"""
        if not self.engine:
            self.engine = create_async_engine(
                self.settings.database_url,
                echo=False
            )
    
    async def get_database_tables(self) -> Dict[str, TableInfo]:
        """取得資料庫中所有表格的資訊"""
        await self.initialize()
        
        async with self.engine.connect() as conn:
            # 取得表格列表
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            table_names = [row[0] for row in result.fetchall()]
            tables = {}
            
            for table_name in table_names:
                # 取得欄位資訊
                columns_result = await conn.execute(text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """), {"table_name": table_name})
                
                columns = {}
                for col_row in columns_result.fetchall():
                    col_name, col_type, nullable, default = col_row
                    columns[col_name] = ColumnInfo(
                        name=col_name,
                        type=col_type,
                        nullable=(nullable == 'YES'),
                        default=default
                    )
                
                # 取得索引資訊
                indexes_result = await conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = :table_name 
                    AND schemaname = 'public'
                """), {"table_name": table_name})
                
                indexes = [row[0] for row in indexes_result.fetchall()]
                
                # 取得外鍵資訊
                fk_result = await conn.execute(text("""
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = :table_name 
                    AND constraint_type = 'FOREIGN KEY'
                """), {"table_name": table_name})
                
                foreign_keys = [row[0] for row in fk_result.fetchall()]
                
                tables[table_name] = TableInfo(
                    name=table_name,
                    columns=columns,
                    indexes=indexes,
                    foreign_keys=foreign_keys
                )
            
            return tables
    
    def get_model_tables(self) -> Dict[str, TableInfo]:
        """從 SQLAlchemy 模型中取得表格資訊"""
        from sqlalchemy.ext.declarative import declarative_base
        from database.models import Base
        
        tables = {}
        
        for model_class in Base.registry.mappers:
            model = model_class.class_
            table = model.__table__
            
            columns = {}
            for col in table.columns:
                columns[col.name] = ColumnInfo(
                    name=col.name,
                    type=str(col.type),
                    nullable=col.nullable,
                    default=col.default,
                    primary_key=col.primary_key
                )
            
            # 取得索引名稱
            indexes = [idx.name for idx in table.indexes if idx.name]
            
            # 取得外鍵名稱
            foreign_keys = [fk.name for fk in table.foreign_keys if fk.name]
            
            tables[table.name] = TableInfo(
                name=table.name,
                columns=columns,
                indexes=indexes,
                foreign_keys=foreign_keys
            )
        
        return tables
    
    async def validate_schema(self) -> Dict[str, Any]:
        """執行完整的 Schema 驗證"""
        print("🔍 開始 Schema 驗證...")
        
        # 取得資料庫和模型的表格資訊
        db_tables = await self.get_database_tables()
        model_tables = self.get_model_tables()
        
        validation_result = {
            "status": "success",
            "issues": [],
            "summary": {
                "db_tables": len(db_tables),
                "model_tables": len(model_tables),
                "matched_tables": 0,
                "missing_tables": [],
                "extra_tables": [],
                "column_mismatches": []
            }
        }
        
        # 檢查缺少的表格
        db_table_names = set(db_tables.keys())
        model_table_names = set(model_tables.keys())
        
        missing_tables = model_table_names - db_table_names
        extra_tables = db_table_names - model_table_names
        
        validation_result["summary"]["missing_tables"] = list(missing_tables)
        validation_result["summary"]["extra_tables"] = list(extra_tables)
        
        if missing_tables:
            validation_result["status"] = "error"
            for table in missing_tables:
                validation_result["issues"].append({
                    "type": "missing_table",
                    "table": table,
                    "message": f"模型中定義的表格 '{table}' 在資料庫中不存在"
                })
        
        # 檢查共同表格的欄位
        common_tables = db_table_names & model_table_names
        validation_result["summary"]["matched_tables"] = len(common_tables)
        
        for table_name in common_tables:
            db_table = db_tables[table_name]
            model_table = model_tables[table_name]
            
            # 檢查欄位
            db_columns = set(db_table.columns.keys())
            model_columns = set(model_table.columns.keys())
            
            missing_columns = model_columns - db_columns
            extra_columns = db_columns - model_columns
            
            if missing_columns:
                validation_result["status"] = "error"
                for col in missing_columns:
                    issue = {
                        "type": "missing_column",
                        "table": table_name,
                        "column": col,
                        "message": f"表格 '{table_name}' 缺少欄位 '{col}'"
                    }
                    validation_result["issues"].append(issue)
                    validation_result["summary"]["column_mismatches"].append(issue)
            
            # 檢查欄位類型差異（簡化版）
            for col_name in db_columns & model_columns:
                db_col = db_table.columns[col_name]
                model_col = model_table.columns[col_name]
                
                # 簡單的類型檢查
                if db_col.nullable != model_col.nullable:
                    issue = {
                        "type": "column_type_mismatch",
                        "table": table_name,
                        "column": col_name,
                        "message": f"欄位 '{col_name}' nullable 不一致: DB={db_col.nullable}, Model={model_col.nullable}"
                    }
                    validation_result["issues"].append(issue)
                    validation_result["summary"]["column_mismatches"].append(issue)
        
        return validation_result
    
    async def generate_fix_suggestions(self, validation_result: Dict[str, Any]) -> List[str]:
        """根據驗證結果生成修復建議"""
        suggestions = []
        
        for issue in validation_result["issues"]:
            if issue["type"] == "missing_table":
                suggestions.append(f"CREATE TABLE {issue['table']} (...);")
            elif issue["type"] == "missing_column":
                suggestions.append(f"ALTER TABLE {issue['table']} ADD COLUMN {issue['column']} ...;")
            elif issue["type"] == "column_type_mismatch":
                suggestions.append(f"ALTER TABLE {issue['table']} ALTER COLUMN {issue['column']} ...;")
        
        return suggestions
    
    async def close(self):
        """關閉資料庫連接"""
        if self.engine:
            await self.engine.dispose()

async def main():
    """主要執行函數"""
    validator = SchemaValidator()
    
    try:
        # 執行驗證
        result = await validator.validate_schema()
        
        # 輸出結果
        print("=" * 60)
        print("📊 Schema 驗證結果")
        print("=" * 60)
        
        print(f"狀態: {'✅ 通過' if result['status'] == 'success' else '❌ 失敗'}")
        print(f"資料庫表格數: {result['summary']['db_tables']}")
        print(f"模型表格數: {result['summary']['model_tables']}")
        print(f"匹配表格數: {result['summary']['matched_tables']}")
        
        if result["summary"]["missing_tables"]:
            print(f"🔴 缺少表格: {', '.join(result['summary']['missing_tables'])}")
        
        if result["summary"]["extra_tables"]:
            print(f"🟡 額外表格: {', '.join(result['summary']['extra_tables'])}")
        
        if result["issues"]:
            print("\n🔍 發現的問題:")
            for i, issue in enumerate(result["issues"], 1):
                print(f"  {i}. {issue['message']}")
        
        if result["status"] != "success":
            print("\n🛠️ 修復建議:")
            suggestions = await validator.generate_fix_suggestions(result)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        # 保存結果到文件
        output_file = Path("schema_validation_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 詳細結果已保存到: {output_file}")
        
        # 返回適當的退出碼
        return 0 if result["status"] == "success" else 1
        
    except Exception as e:
        print(f"❌ Schema 驗證過程中發生錯誤: {e}")
        return 1
    finally:
        await validator.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 