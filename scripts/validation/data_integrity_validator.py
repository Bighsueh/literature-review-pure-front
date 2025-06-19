#!/usr/bin/env python3
"""
資料完整性驗證框架
Data Integrity Validation Framework for DB Migration

此腳本用於驗證資料庫遷移前後的資料完整性，確保：
1. 資料筆數一致性
2. 外鍵關聯正確性  
3. 業務邏輯一致性
4. 工作區歸檔正確性
"""

import psycopg2
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """驗證結果資料結構"""
    check_name: str
    passed: bool
    expected: Any
    actual: Any
    message: str
    details: Optional[Dict] = None


class DataIntegrityValidator:
    """資料完整性驗證器"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None
        self.results: List[ValidationResult] = []
        
    def connect(self):
        """建立資料庫連接"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.connection.autocommit = True
            print("✅ 資料庫連接成功")
        except Exception as e:
            print(f"❌ 資料庫連接失敗: {e}")
            sys.exit(1)
    
    def disconnect(self):
        """關閉資料庫連接"""
        if self.connection:
            self.connection.close()
            print("✅ 資料庫連接已關閉")
    
    def execute_query(self, query: str) -> List[tuple]:
        """執行查詢並返回結果"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor.fetchall()
    
    def get_table_count(self, table_name: str) -> int:
        """獲取表格資料筆數"""
        result = self.execute_query(f"SELECT COUNT(*) FROM {table_name}")
        return result[0][0]
    
    def validate_table_counts(self, pre_migration_snapshot: Dict[str, int]):
        """驗證表格資料筆數一致性"""
        print("\n🔍 驗證表格資料筆數一致性...")
        
        tables = [
            'users', 'workspaces', 'papers', 'paper_sections', 
            'sentences', 'paper_selections', 'processing_queue', 
            'chat_histories'
        ]
        
        for table in tables:
            try:
                current_count = self.get_table_count(table)
                expected_count = pre_migration_snapshot.get(table, 0)
                
                # 對於 users 和 workspaces，遷移後會增加 1 筆（legacy user/workspace）
                if table in ['users', 'workspaces']:
                    expected_count += 1
                
                passed = current_count == expected_count
                
                result = ValidationResult(
                    check_name=f"table_count_{table}",
                    passed=passed,
                    expected=expected_count,
                    actual=current_count,
                    message=f"表格 {table} 資料筆數{'正確' if passed else '不一致'}"
                )
                
                self.results.append(result)
                status = "✅" if passed else "❌"
                print(f"  {status} {table}: 期望 {expected_count}, 實際 {current_count}")
                
            except Exception as e:
                result = ValidationResult(
                    check_name=f"table_count_{table}",
                    passed=False,
                    expected="無錯誤",
                    actual=f"錯誤: {e}",
                    message=f"檢查表格 {table} 時發生錯誤"
                )
                self.results.append(result)
                print(f"  ❌ {table}: 檢查失敗 - {e}")
    
    def validate_workspace_assignments(self):
        """驗證工作區分配正確性"""
        print("\n🔍 驗證工作區分配正確性...")
        
        # 檢查所有關鍵表格是否都有 workspace_id
        critical_tables = ['papers', 'paper_sections', 'sentences', 'paper_selections', 'processing_queue']
        
        for table in critical_tables:
            try:
                # 檢查是否有 NULL workspace_id
                null_count_result = self.execute_query(
                    f"SELECT COUNT(*) FROM {table} WHERE workspace_id IS NULL"
                )
                null_count = null_count_result[0][0]
                
                passed = null_count == 0
                
                result = ValidationResult(
                    check_name=f"workspace_assignment_{table}",
                    passed=passed,
                    expected=0,
                    actual=null_count,
                    message=f"表格 {table} 所有記錄都{'已' if passed else '未'}分配到工作區"
                )
                
                self.results.append(result)
                status = "✅" if passed else "❌"
                print(f"  {status} {table}: {null_count} 筆未分配記錄")
                
            except Exception as e:
                result = ValidationResult(
                    check_name=f"workspace_assignment_{table}",
                    passed=False,
                    expected="無錯誤",
                    actual=f"錯誤: {e}",
                    message=f"檢查表格 {table} 工作區分配時發生錯誤"
                )
                self.results.append(result)
                print(f"  ❌ {table}: 檢查失敗 - {e}")
    
    def validate_legacy_workspace(self):
        """驗證遺留工作區設置"""
        print("\n🔍 驗證遺留工作區設置...")
        
        try:
            # 檢查遺留用戶是否存在
            legacy_user_result = self.execute_query(
                "SELECT id, name FROM users WHERE google_id = 'system_legacy_user'"
            )
            
            if legacy_user_result:
                user_id = legacy_user_result[0][0]
                user_name = legacy_user_result[0][1]
                
                result = ValidationResult(
                    check_name="legacy_user_exists",
                    passed=True,
                    expected="系統遺留用戶存在",
                    actual=f"用戶: {user_name}",
                    message="遺留系統用戶已正確創建"
                )
                print(f"  ✅ 遺留用戶: {user_name} (ID: {user_id})")
                
                # 檢查遺留工作區是否存在
                legacy_workspace_result = self.execute_query(
                    f"SELECT id, name FROM workspaces WHERE user_id = '{user_id}'"
                )
                
                if legacy_workspace_result:
                    workspace_id = legacy_workspace_result[0][0]
                    workspace_name = legacy_workspace_result[0][1]
                    
                    result = ValidationResult(
                        check_name="legacy_workspace_exists",
                        passed=True,
                        expected="遺留工作區存在",
                        actual=f"工作區: {workspace_name}",
                        message="遺留工作區已正確創建"
                    )
                    print(f"  ✅ 遺留工作區: {workspace_name} (ID: {workspace_id})")
                    
                    # 檢查有多少數據被分配到遺留工作區
                    for table in ['papers', 'paper_sections', 'sentences', 'paper_selections']:
                        try:
                            count_result = self.execute_query(
                                f"SELECT COUNT(*) FROM {table} WHERE workspace_id = '{workspace_id}'"
                            )
                            count = count_result[0][0]
                            print(f"    📊 {table}: {count} 筆記錄分配到遺留工作區")
                        except Exception as e:
                            print(f"    ❌ {table}: 無法統計 - {e}")
                    
                else:
                    result = ValidationResult(
                        check_name="legacy_workspace_exists",
                        passed=False,
                        expected="遺留工作區存在",
                        actual="未找到遺留工作區",
                        message="遺留工作區創建失敗"
                    )
                    print("  ❌ 未找到遺留工作區")
                    
            else:
                result = ValidationResult(
                    check_name="legacy_user_exists",
                    passed=False,
                    expected="遺留用戶存在",
                    actual="未找到遺留用戶",
                    message="遺留用戶創建失敗"
                )
                print("  ❌ 未找到遺留用戶")
                
            self.results.append(result)
            
        except Exception as e:
            result = ValidationResult(
                check_name="legacy_workspace_validation",
                passed=False,
                expected="無錯誤",
                actual=f"錯誤: {e}",
                message="驗證遺留工作區時發生錯誤"
            )
            self.results.append(result)
            print(f"  ❌ 檢查失敗 - {e}")
    
    def validate_foreign_key_constraints(self):
        """驗證外鍵約束正確性"""
        print("\n🔍 驗證外鍵約束正確性...")
        
        # 檢查重要的外鍵約束
        constraints_to_check = [
            ("papers", "workspace_id", "workspaces", "id"),
            ("paper_sections", "workspace_id", "workspaces", "id"),
            ("sentences", "workspace_id", "workspaces", "id"),
            ("paper_selections", "workspace_id", "workspaces", "id"),
            ("processing_queue", "workspace_id", "workspaces", "id"),
            ("chat_histories", "workspace_id", "workspaces", "id"),
        ]
        
        for child_table, child_column, parent_table, parent_column in constraints_to_check:
            try:
                # 檢查是否有孤立記錄（子表中有但父表中沒有的記錄）
                orphan_query = f"""
                    SELECT COUNT(*) 
                    FROM {child_table} c
                    LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
                    WHERE c.{child_column} IS NOT NULL 
                    AND p.{parent_column} IS NULL
                """
                
                orphan_result = self.execute_query(orphan_query)
                orphan_count = orphan_result[0][0]
                
                passed = orphan_count == 0
                
                result = ValidationResult(
                    check_name=f"fk_constraint_{child_table}_{child_column}",
                    passed=passed,
                    expected=0,
                    actual=orphan_count,
                    message=f"表格 {child_table}.{child_column} 外鍵約束{'正確' if passed else '有問題'}"
                )
                
                self.results.append(result)
                status = "✅" if passed else "❌"
                print(f"  {status} {child_table}.{child_column} -> {parent_table}.{parent_column}: {orphan_count} 筆孤立記錄")
                
            except Exception as e:
                result = ValidationResult(
                    check_name=f"fk_constraint_{child_table}_{child_column}",
                    passed=False,
                    expected="無錯誤",
                    actual=f"錯誤: {e}",
                    message=f"檢查外鍵約束時發生錯誤"
                )
                self.results.append(result)
                print(f"  ❌ {child_table}.{child_column}: 檢查失敗 - {e}")
    
    def validate_business_logic_consistency(self):
        """驗證業務邏輯一致性"""
        print("\n🔍 驗證業務邏輯一致性...")
        
        try:
            # 檢查 paper_selections 與 papers 的一致性
            inconsistent_selections = self.execute_query("""
                SELECT COUNT(*)
                FROM paper_selections ps
                JOIN papers p ON ps.paper_id = p.id
                WHERE ps.workspace_id != p.workspace_id
            """)
            
            inconsistent_count = inconsistent_selections[0][0]
            passed = inconsistent_count == 0
            
            result = ValidationResult(
                check_name="paper_selections_workspace_consistency",
                passed=passed,
                expected=0,
                actual=inconsistent_count,
                message=f"paper_selections 與 papers 的工作區{'一致' if passed else '不一致'}"
            )
            
            self.results.append(result)
            status = "✅" if passed else "❌"
            print(f"  {status} paper_selections 工作區一致性: {inconsistent_count} 筆不一致記錄")
            
            # 檢查 sentences 與 paper_sections 的一致性
            inconsistent_sentences = self.execute_query("""
                SELECT COUNT(*)
                FROM sentences s
                JOIN paper_sections ps ON s.section_id = ps.id
                WHERE s.workspace_id != ps.workspace_id
            """)
            
            inconsistent_count = inconsistent_sentences[0][0]
            passed = inconsistent_count == 0
            
            result = ValidationResult(
                check_name="sentences_sections_workspace_consistency",
                passed=passed,
                expected=0,
                actual=inconsistent_count,
                message=f"sentences 與 paper_sections 的工作區{'一致' if passed else '不一致'}"
            )
            
            self.results.append(result)
            status = "✅" if passed else "❌"
            print(f"  {status} sentences-sections 工作區一致性: {inconsistent_count} 筆不一致記錄")
            
        except Exception as e:
            result = ValidationResult(
                check_name="business_logic_consistency",
                passed=False,
                expected="無錯誤",
                actual=f"錯誤: {e}",
                message="驗證業務邏輯一致性時發生錯誤"
            )
            self.results.append(result)
            print(f"  ❌ 業務邏輯檢查失敗 - {e}")
    
    def generate_report(self) -> Dict:
        """生成驗證報告"""
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "success_rate": f"{(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "0%"
            },
            "results": [
                {
                    "check_name": r.check_name,
                    "passed": r.passed,
                    "expected": str(r.expected),
                    "actual": str(r.actual),
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        return report
    
    def print_summary(self):
        """印出驗證摘要"""
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks
        
        print("\n" + "="*60)
        print("📊 驗證摘要報告")
        print("="*60)
        print(f"總檢查項目: {total_checks}")
        print(f"通過項目: {passed_checks} ✅")
        print(f"失敗項目: {failed_checks} ❌")
        print(f"成功率: {(passed_checks/total_checks*100):.1f}%" if total_checks > 0 else "0%")
        
        if failed_checks > 0:
            print("\n❌ 失敗的檢查項目:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.check_name}: {result.message}")
        
        print("="*60)
        
        return failed_checks == 0


def main():
    """主函數"""
    # 資料庫配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'paper_analysis'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    print("🚀 開始資料完整性驗證...")
    print(f"連接資料庫: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    validator = DataIntegrityValidator(db_config)
    
    try:
        validator.connect()
        
        # 如果有遷移前快照，讀取它
        pre_migration_snapshot = {}
        snapshot_file = "pre_migration_snapshot.json"
        
        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                pre_migration_snapshot = json.load(f)
            print(f"✅ 讀取遷移前快照: {snapshot_file}")
        else:
            print("⚠️  未找到遷移前快照檔案，將跳過表格筆數比較")
        
        # 執行各項驗證
        if pre_migration_snapshot:
            validator.validate_table_counts(pre_migration_snapshot.get('table_counts', {}))
        
        validator.validate_workspace_assignments()
        validator.validate_legacy_workspace()
        validator.validate_foreign_key_constraints()
        validator.validate_business_logic_consistency()
        
        # 生成報告
        report = validator.generate_report()
        
        # 儲存報告
        report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 詳細報告已儲存至: {report_file}")
        
        # 印出摘要
        success = validator.print_summary()
        
        # 根據驗證結果設定退出碼
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ 驗證過程發生錯誤: {e}")
        sys.exit(1)
        
    finally:
        validator.disconnect()


if __name__ == "__main__":
    main() 