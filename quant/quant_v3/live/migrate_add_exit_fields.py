"""添加退出相关字段到backtest_trades表"""
from backtest.database import engine
from sqlalchemy import text

def migrate():
    """运行数据库迁移，添加自适应策略字段"""
    print("开始数据库迁移...")
    print("目标: 添加exit_reason, volatility_level, is_partial, sell_ratio字段")

    with engine.connect() as conn:
        try:
            # 添加exit_reason列（退出原因）
            print("  添加 exit_reason 列...")
            conn.execute(text("""
                ALTER TABLE backtest_trades
                ADD COLUMN IF NOT EXISTS exit_reason TEXT
            """))

            # 添加volatility_level列（波动率类型）
            print("  添加 volatility_level 列...")
            conn.execute(text("""
                ALTER TABLE backtest_trades
                ADD COLUMN IF NOT EXISTS volatility_level TEXT
            """))

            # 添加is_partial列（是否部分卖出）
            print("  添加 is_partial 列...")
            conn.execute(text("""
                ALTER TABLE backtest_trades
                ADD COLUMN IF NOT EXISTS is_partial BOOLEAN DEFAULT FALSE
            """))

            # 添加sell_ratio列（卖出比例）
            print("  添加 sell_ratio 列...")
            conn.execute(text("""
                ALTER TABLE backtest_trades
                ADD COLUMN IF NOT EXISTS sell_ratio REAL DEFAULT 1.0
            """))

            conn.commit()
            print("\n✅ 数据库迁移成功完成！")
            print("新增字段:")
            print("  - exit_reason (TEXT): 退出原因")
            print("  - volatility_level (TEXT): 波动率类型")
            print("  - is_partial (BOOLEAN): 是否部分卖出")
            print("  - sell_ratio (REAL): 卖出比例")

        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
